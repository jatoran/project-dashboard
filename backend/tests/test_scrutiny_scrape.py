import os
import unittest
import httpx
import re


class ScrutinyScrapeTest(unittest.TestCase):
    """
    Smoke test: ensure we can render the Scrutiny dashboard via headless_playwright
    and receive non-empty HTML/text content.
    """

    def setUp(self):
        self.gateway_url = os.getenv("GATEWAY_URL", "http://127.0.0.1:7083")
        self.scrutiny_url = os.getenv("SCRUTINY_URL", "http://192.168.50.193:8081/web/dashboard")
        self.client_id = os.getenv("GATEWAY_CLIENT_ID", "test_homepage_scrape")
        self.api_key = os.getenv("GATEWAY_API_KEY")

    def test_scrutiny_dashboard_renders(self):
        payload = {
            "provider": "headless_playwright",
            "urls": [self.scrutiny_url],
            "options": {
                "timeout_ms": 40000,
                "render": "always",
                "format": "text",
                "extract_depth": "advanced",
                "wait_until": "networkidle",
                "wait_for_timeout_ms": 8000,
                "include_html": True,
                "ignore_https_errors": True,
                "include_console_logs": True,
                "include_network_errors": True,
            },
        }
        headers = {
            "Content-Type": "application/json",
            "X-Client-Id": self.client_id,
        }
        if self.api_key:
            headers["X-Api-Key"] = self.api_key

        resp = httpx.post(
            f"{self.gateway_url}/v1/extract",
            json=payload,
            headers=headers,
            timeout=60.0,
        )
        self.assertEqual(resp.status_code, 200, f"Gateway returned {resp.status_code}: {resp.text}")

        data = resp.json()
        items = data.get("items") or data.get("results") or []
        self.assertTrue(items, "No items returned from gateway")

        blobs = []
        for item in items:
            for key in ("html", "content", "text", "raw_html", "raw_content", "body"):
                val = item.get(key)
                if isinstance(val, str):
                    blobs.append(val)
            meta = item.get("provider_meta") or {}
            if isinstance(meta, dict):
                raw_html = meta.get("html")
                if isinstance(raw_html, str):
                    blobs.append(raw_html)

            logs = meta.get("console_logs") or []
            if logs:
                print(f"[console] item logs: {logs}")
            net_errs = meta.get("network_errors") or []
            if net_errs:
                print(f"[neterr] item errors: {net_errs}")

        aggregated = " ".join(blobs)
        self.assertTrue(aggregated.strip(), "Extractor returned no textual or HTML content")

        drives = self._parse_drives(aggregated)
        self.assertTrue(drives, "No drives parsed from Scrutiny dashboard")
        for d in drives:
            print(f"[drive] {d['device']} | {d['bus_model']} | Status={d['status']} | Temp={d['temp']} | Capacity={d['capacity']} | Powered On={d['powered_on']} | Last Updated={d['last_updated']}")

    @staticmethod
    def _parse_drives(text: str):
        """
        Parse drive blocks like:
        /dev/sda - sat - Samsung ...
        Last Updated on ... - 18:54
        Status
        Passed
        Temperature
        25°C
        Capacity
        232.9 GiB
        Powered On
        6 years
        """
        drives = []
        # Normalize whitespace
        t = re.sub(r"[ \t]+", " ", text)
        t = t.replace("\r", "")
        # Split on /dev occurrences
        pattern = re.compile(
            r"(/dev/[^\s]+)\s+-\s+([^-]+?)\s+-\s+([^\n]+?)\s+Last Updated on\s+([^\n]+?)\s+Status\s+([^\n]+?)\s+Temperature\s+([^\n]+?)\s+Capacity\s+([^\n]+?)\s+Powered On\s+([^\n]+?)(?:\s+/dev|$)",
            flags=re.IGNORECASE | re.DOTALL,
        )
        for m in pattern.finditer(t + " /dev"):  # sentinel to match last block
            device = m.group(1).strip()
            bus = m.group(2).strip()
            model = m.group(3).strip()
            last_updated = m.group(4).strip()
            status = m.group(5).strip()
            temp = m.group(6).strip()
            capacity = m.group(7).strip()
            powered_on = m.group(8).strip()
            drives.append(
                {
                    "device": device,
                    "bus_model": f"{bus} - {model}",
                    "last_updated": last_updated,
                    "status": status,
                    "temp": temp,
                    "capacity": capacity,
                    "powered_on": powered_on,
                }
            )
        return drives


if __name__ == "__main__":
    unittest.main()
