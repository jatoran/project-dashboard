"""
DuckDB-based history service for persistent hardware metrics storage.
Columnar storage optimized for time-series analytics.
"""

import duckdb
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Database file path
DATA_DIR = Path(__file__).parent.parent / "data"
DB_FILE = DATA_DIR / "history.duckdb"

# Global connection (lazy initialized)
_conn: Optional[duckdb.DuckDBPyConnection] = None


def _get_connection() -> duckdb.DuckDBPyConnection:
    """Get or create the DuckDB connection."""
    global _conn
    if _conn is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _conn = duckdb.connect(str(DB_FILE))
        _init_schema(_conn)
    return _conn


def _init_schema(conn: duckdb.DuckDBPyConnection):
    """Initialize the database schema."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hardware_metrics (
            timestamp TIMESTAMP NOT NULL,
            cpu_load DOUBLE,
            cpu_temp DOUBLE,
            cpu_clock DOUBLE,
            gpu_load DOUBLE,
            gpu_temp DOUBLE,
            gpu_clock DOUBLE,
            ram_load DOUBLE,
            ram_used_gb DOUBLE,
            network_upload_mbps DOUBLE,
            network_download_mbps DOUBLE
        )
    """)
    # Create index on timestamp for efficient time-range queries
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_hw_timestamp 
        ON hardware_metrics(timestamp)
    """)


def get_db_info() -> Dict[str, Any]:
    """Get database debug info - record count, time range, etc."""
    try:
        conn = _get_connection()
        result = conn.execute("""
            SELECT 
                COUNT(*) as total_records,
                MIN(timestamp) as oldest,
                MAX(timestamp) as newest
            FROM hardware_metrics
        """).fetchone()
        
        if result:
            return {
                "total_records": result[0],
                "oldest": result[1].isoformat() if result[1] else None,
                "newest": result[2].isoformat() if result[2] else None,
            }
        return {"total_records": 0, "oldest": None, "newest": None}
    except Exception as e:
        return {"error": str(e)}


def backfill_from_history(history_data: list) -> int:
    """
    Backfill the database from existing agent history.
    Takes the history array from host-hardware response.
    Returns number of records inserted.
    """
    if not history_data:
        return 0
    
    try:
        conn = _get_connection()
        inserted = 0
        
        for snapshot in history_data:
            # Parse timestamp from the snapshot
            ts_str = snapshot.get("timestamp")
            if not ts_str:
                continue
            
            try:
                # Parse ISO timestamp
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except:
                continue
            
            # Get metrics directly from snapshot
            cpu = snapshot.get("cpu", {})
            gpu = snapshot.get("gpu", {})
            ram = snapshot.get("ram", {})
            network = snapshot.get("network", {})
            
            # Aggregate network
            net_upload = 0.0
            net_download = 0.0
            for adapter_data in network.values():
                if isinstance(adapter_data, dict):
                    net_upload += adapter_data.get("upload_rate_mbps", 0) or 0
                    net_download += adapter_data.get("download_rate_mbps", 0) or 0
            
            # Insert the record
            conn.execute("""
                INSERT INTO hardware_metrics (
                    timestamp, cpu_load, cpu_temp, cpu_clock,
                    gpu_load, gpu_temp, gpu_clock,
                    ram_load, ram_used_gb,
                    network_upload_mbps, network_download_mbps
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                ts,
                cpu.get("load_pct"), cpu.get("temp_c"), cpu.get("clock_mhz"),
                gpu.get("load_pct"), gpu.get("temp_c"), gpu.get("clock_mhz"),
                ram.get("load_pct"), ram.get("used_gb"),
                net_upload if net_upload > 0 else None,
                net_download if net_download > 0 else None,
            ])
            inserted += 1
        
        return inserted
    except Exception as e:
        print(f"[history] Error backfilling: {e}")
        return 0


def record_snapshot(data: Dict[str, Any]) -> bool:
    """
    Record a hardware snapshot to the database.
    Extracts metrics from the host-hardware response format.
    Returns True if recorded successfully.
    """
    try:
        conn = _get_connection()
        
        # Prefer 'latest' field which contains the most recent real-time data
        # Fall back to history[0] if latest is unavailable or empty
        latest = data.get("latest", {})
        
        # The latest field may have metrics directly or under a 'metrics' key
        # Check both possibilities
        metrics_container = latest.get("metrics", latest)
        has_metrics = metrics_container.get("cpu") or metrics_container.get("gpu") or metrics_container.get("ram")
        
        if has_metrics:
            # Use the metrics container (either latest.metrics or latest itself)
            snapshot = metrics_container
            # Get timestamp from the parent latest object
            snapshot_ts = latest.get("timestamp")
        else:
            # Fallback: try the first item from history
            history = data.get("history", [])
            if not history:
                print(f"[history] No latest metrics and no history, skipping")
                return False
            snapshot = history[0]
            snapshot_ts = snapshot.get("timestamp")
        
        # Metrics are directly on the snapshot (cpu, gpu, ram, etc.)
        cpu = snapshot.get("cpu", {})
        cpu_load = cpu.get("load_pct")
        cpu_temp = cpu.get("temp_c")
        cpu_clock = cpu.get("clock_mhz")
        
        # Get GPU metrics
        gpu = snapshot.get("gpu", {})
        gpu_load = gpu.get("load_pct")
        gpu_temp = gpu.get("temp_c")
        gpu_clock = gpu.get("clock_mhz")
        
        # Get RAM metrics
        ram = snapshot.get("ram", {})
        ram_load = ram.get("load_pct")
        ram_used = ram.get("used_gb")
        
        # Get Network metrics (aggregate all adapters)
        network = snapshot.get("network", {})
        net_upload = 0.0
        net_download = 0.0
        for adapter_data in network.values():
            if isinstance(adapter_data, dict):
                net_upload += adapter_data.get("upload_rate_mbps", 0) or 0
                net_download += adapter_data.get("download_rate_mbps", 0) or 0
        
        # Only insert if we have at least some data
        if cpu_load is None and cpu_temp is None and ram_load is None:
            print(f"[history] No metrics found in snapshot, skipping")
            return False
        
        # Use timestamp extracted earlier, or use current time as fallback
        if snapshot_ts:
            try:
                ts = datetime.fromisoformat(snapshot_ts.replace("Z", "+00:00"))
            except:
                ts = datetime.now(timezone.utc)
        else:
            ts = datetime.now(timezone.utc)
        
        # Deduplication: check if we have this exact timestamp already
        existing = conn.execute("""
            SELECT COUNT(*) FROM hardware_metrics WHERE timestamp = ?
        """, [ts]).fetchone()
        if existing and existing[0] > 0:
            # Already have this snapshot, skip
            return False
        
        # Insert the record
        conn.execute("""
            INSERT INTO hardware_metrics (
                timestamp, cpu_load, cpu_temp, cpu_clock,
                gpu_load, gpu_temp, gpu_clock,
                ram_load, ram_used_gb,
                network_upload_mbps, network_download_mbps
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            ts,
            cpu_load, cpu_temp, cpu_clock,
            gpu_load, gpu_temp, gpu_clock,
            ram_load, ram_used,
            net_upload if net_upload > 0 else None,
            net_download if net_download > 0 else None,
        ])
        
        return True
    except Exception as e:
        print(f"[history] Error recording snapshot: {e}")
        return False


def get_history(minutes: int = 60, max_points: int = 200) -> List[Dict[str, Any]]:
    """
    Get hardware metrics history for the specified time range.
    Automatically downsamples for longer time ranges to keep response fast.
    Returns list of metric snapshots ordered by timestamp.
    """
    try:
        conn = _get_connection()
        since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        
        # Determine bucket size based on time range for downsampling
        # Goal: return ~max_points data points for smooth charts
        if minutes <= 60:
            bucket_minutes = 1  # 1 min buckets for 1h
        elif minutes <= 360:
            bucket_minutes = 2  # 2 min buckets for 6h
        elif minutes <= 1440:
            bucket_minutes = 10  # 10 min buckets for 24h
        else:
            bucket_minutes = 60  # 1 hour buckets for 7d+
        
        # Use DuckDB time_bucket for efficient downsampling with averages
        result = conn.execute(f"""
            SELECT 
                time_bucket(INTERVAL '{bucket_minutes} minutes', timestamp) as bucket,
                AVG(cpu_load) as cpu_load,
                AVG(cpu_temp) as cpu_temp,
                AVG(cpu_clock) as cpu_clock,
                AVG(gpu_load) as gpu_load,
                AVG(gpu_temp) as gpu_temp,
                AVG(gpu_clock) as gpu_clock,
                AVG(ram_load) as ram_load,
                AVG(ram_used_gb) as ram_used_gb,
                AVG(network_upload_mbps) as network_upload_mbps,
                AVG(network_download_mbps) as network_download_mbps
            FROM hardware_metrics
            WHERE timestamp >= ?
            GROUP BY bucket
            ORDER BY bucket ASC
            LIMIT ?
        """, [since, max_points]).fetchall()
        
        columns = [
            "timestamp", "cpu_load", "cpu_temp", "cpu_clock",
            "gpu_load", "gpu_temp", "gpu_clock",
            "ram_load", "ram_used_gb",
            "network_upload_mbps", "network_download_mbps"
        ]
        
        return [
            {col: (row[i].isoformat() if isinstance(row[i], datetime) else row[i])
             for i, col in enumerate(columns)}
            for row in result
        ]
    except Exception as e:
        print(f"[history] Error getting history: {e}")
        return []


def get_stats(minutes: int = 60) -> Dict[str, Any]:
    """
    Get aggregated statistics for the time range.
    Returns min, max, avg for each metric.
    """
    try:
        conn = _get_connection()
        since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        
        result = conn.execute("""
            SELECT 
                COUNT(*) as sample_count,
                AVG(cpu_load) as cpu_load_avg,
                MAX(cpu_load) as cpu_load_max,
                AVG(cpu_temp) as cpu_temp_avg,
                MAX(cpu_temp) as cpu_temp_max,
                AVG(gpu_load) as gpu_load_avg,
                MAX(gpu_load) as gpu_load_max,
                AVG(gpu_temp) as gpu_temp_avg,
                MAX(gpu_temp) as gpu_temp_max,
                AVG(ram_load) as ram_load_avg,
                MAX(ram_load) as ram_load_max
            FROM hardware_metrics
            WHERE timestamp >= ?
        """, [since]).fetchone()
        
        if not result:
            return {}
        
        return {
            "sample_count": result[0],
            "cpu_load": {"avg": result[1], "max": result[2]},
            "cpu_temp": {"avg": result[3], "max": result[4]},
            "gpu_load": {"avg": result[5], "max": result[6]},
            "gpu_temp": {"avg": result[7], "max": result[8]},
            "ram_load": {"avg": result[9], "max": result[10]},
        }
    except Exception as e:
        print(f"[history] Error getting stats: {e}")
        return {}


def cleanup_old_data(days: int = 7) -> int:
    """Delete data older than the specified number of days. Returns rows deleted."""
    try:
        conn = _get_connection()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        result = conn.execute("""
            DELETE FROM hardware_metrics WHERE timestamp < ?
        """, [cutoff])
        
        return result.rowcount if hasattr(result, 'rowcount') else 0
    except Exception as e:
        print(f"[history] Error cleaning up: {e}")
        return 0
