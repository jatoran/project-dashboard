"""
DuckDB-based history service for persistent hardware metrics storage.
Columnar storage optimized for time-series analytics.

Uses connection-per-operation pattern to avoid long-lived connections
that can cause issues in containerized environments.
"""

import duckdb
import threading
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Generator, List

# Database file path
DATA_DIR = Path(__file__).parent.parent / "data"
DB_FILE = DATA_DIR / "history.duckdb"

# Thread lock for schema initialization
_schema_init_lock = threading.Lock()
_schema_initialized = False

# Auto-cleanup tracking
_last_cleanup: datetime | None = None
_cleanup_lock = threading.Lock()


def _ensure_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Initialize the database schema if needed."""
    global _schema_initialized
    if _schema_initialized:
        return
    
    with _schema_init_lock:
        if _schema_initialized:
            return
        
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
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_hw_timestamp 
            ON hardware_metrics(timestamp)
        """)
        _schema_initialized = True


@contextmanager
def _get_connection() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """
    Context manager for DuckDB connections.
    Opens a fresh connection for each operation and closes it after.
    This prevents long-lived connections from causing file handle issues.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(DB_FILE))
    try:
        _ensure_schema(conn)
        _maybe_auto_cleanup(conn)
        yield conn
    finally:
        conn.close()


def _maybe_auto_cleanup(conn: duckdb.DuckDBPyConnection) -> None:
    """Auto-cleanup old data every 6 hours."""
    global _last_cleanup
    
    with _cleanup_lock:
        now = datetime.now(timezone.utc)
        if _last_cleanup is not None:
            hours_since = (now - _last_cleanup).total_seconds() / 3600
            if hours_since < 6:
                return
        
        try:
            cutoff = now - timedelta(days=7)
            conn.execute("DELETE FROM hardware_metrics WHERE timestamp < ?", [cutoff])
            _last_cleanup = now
            print(f"[history] Auto-cleanup completed, removed data older than 7 days")
        except Exception as e:
            print(f"[history] Auto-cleanup error: {e}")


def get_db_info() -> Dict[str, Any]:
    """Get database debug info - record count, time range, etc."""
    try:
        with _get_connection() as conn:
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
        with _get_connection() as conn:
            inserted = 0
            
            for snapshot in history_data:
                # Parse timestamp from the snapshot
                ts_str = snapshot.get("timestamp")
                if not ts_str:
                    continue
                
                try:
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
        # Prefer 'latest' field which contains the most recent real-time data
        # Fall back to history[0] if latest is unavailable or empty
        latest = data.get("latest", {})
        
        # The latest field may have metrics directly or under a 'metrics' key
        metrics_container = latest.get("metrics", latest)
        has_metrics = metrics_container.get("cpu") or metrics_container.get("gpu") or metrics_container.get("ram")
        
        if has_metrics:
            snapshot = metrics_container
            snapshot_ts = latest.get("timestamp")
        else:
            history = data.get("history", [])
            if not history:
                return False
            snapshot = history[0]
            snapshot_ts = snapshot.get("timestamp")
        
        # Extract metrics
        cpu = snapshot.get("cpu", {})
        cpu_load = cpu.get("load_pct")
        cpu_temp = cpu.get("temp_c")
        cpu_clock = cpu.get("clock_mhz")
        
        gpu = snapshot.get("gpu", {})
        gpu_load = gpu.get("load_pct")
        gpu_temp = gpu.get("temp_c")
        gpu_clock = gpu.get("clock_mhz")
        
        ram = snapshot.get("ram", {})
        ram_load = ram.get("load_pct")
        ram_used = ram.get("used_gb")
        
        network = snapshot.get("network", {})
        net_upload = 0.0
        net_download = 0.0
        for adapter_data in network.values():
            if isinstance(adapter_data, dict):
                net_upload += adapter_data.get("upload_rate_mbps", 0) or 0
                net_download += adapter_data.get("download_rate_mbps", 0) or 0
        
        # Only insert if we have at least some data
        if cpu_load is None and cpu_temp is None and ram_load is None:
            return False
        
        # Use timestamp extracted earlier, or use current time as fallback
        if snapshot_ts:
            try:
                ts = datetime.fromisoformat(snapshot_ts.replace("Z", "+00:00"))
            except:
                ts = datetime.now(timezone.utc)
        else:
            ts = datetime.now(timezone.utc)
        
        with _get_connection() as conn:
            # Deduplication check
            existing = conn.execute(
                "SELECT 1 FROM hardware_metrics WHERE timestamp = ? LIMIT 1",
                [ts]
            ).fetchone()
            
            if existing:
                return False
            
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
    """
    try:
        with _get_connection() as conn:
            since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
            
            # Determine bucket size for downsampling
            if minutes <= 60:
                bucket_minutes = 1
            elif minutes <= 360:
                bucket_minutes = 2
            elif minutes <= 1440:
                bucket_minutes = 10
            else:
                bucket_minutes = 60
            
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
    """Get aggregated statistics for the time range."""
    try:
        with _get_connection() as conn:
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
        with _get_connection() as conn:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Get count before delete
            count_result = conn.execute(
                "SELECT COUNT(*) FROM hardware_metrics WHERE timestamp < ?",
                [cutoff]
            ).fetchone()
            count = count_result[0] if count_result else 0
            
            conn.execute("DELETE FROM hardware_metrics WHERE timestamp < ?", [cutoff])
            
            return count
    except Exception as e:
        print(f"[history] Error cleaning up: {e}")
        return 0
