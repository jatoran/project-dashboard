import os
import re
import uuid
import unittest
import httpx


class HomepageScrapeTest(unittest.TestCase):
    """
    Integration smoke test: ensure the Search Gateway's headless_playwright
    extractor can render the Homepage dashboard and return recognizable text.
    Requires:
      - Gateway running with HEADLESS_ENABLE_PLAYWRIGHT=true
      - Homepage reachable on HOMEPAGE_URL
      - X-Client-Id (and optional X-Api-Key) configured for the gateway
    """

    def setUp(self):
        self.gateway_url = os.getenv("GATEWAY_URL", "http://127.0.0.1:7083")
        self.homepage_url = os.getenv("HOMEPAGE_URL", "http://192.168.50.193:3000")
        self.client_id = os.getenv("GATEWAY_CLIENT_ID", "test_homepage_scrape")
        self.api_key = os.getenv("GATEWAY_API_KEY")
        # Cache-bust so we never re-use a stale gateway extract response.
        self.request_url = f"{self.homepage_url}?cb={uuid.uuid4()}"
        # Optional: pass cookies/headers if Homepage requires auth/session.
        self.cookie_header = os.getenv("HOMEPAGE_COOKIE_HEADER")  # e.g., "session=abc; other=xyz"
        self.extra_headers = os.getenv("HOMEPAGE_EXTRA_HEADERS")  # JSON string not supported here; use simple Cookie header.
        # Expected service names and the metric labels we expect to harvest.
        self.expected_services = {
            "Sonarr": ["Wanted", "Queued", "Series"],
            "Radarr": ["Wanted", "Missing", "Queued", "Movies"],
            "Bazarr": ["Missing Episodes", "Missing Movies"],
            "Prowlarr": ["Grabs", "Queries"],
            "Proxmox": ["VMs", "LXC", "CPU", "MEM"],
            "OMV NAS": ["CPU", "RAM", "OS", "Downloads"],
        }

    def _fetch_homepage_via_gateway(self):
        """
        Try multiple provider/option combinations to get rendered content.
        Returns the first items list that contains any textual/html content.
        """
        attempts = []
        provider = "headless_playwright"
        renders = ["always", "auto"]
        formats = ["text", "markdown"]

        for render in renders:
            for fmt in formats:
                payload = {
                    "provider": provider,
                    "urls": [self.request_url],
                    "options": {
                        "timeout_ms": 40000,
                        "render": render,
                        "format": fmt,
                        "extract_depth": "advanced",
                        "wait_until": "networkidle",
                        "wait_for_text": "Sonarr",
                        "wait_for_timeout_ms": 12000,
                        "include_html": True,
                        "ignore_https_errors": True,
                        "include_console_logs": True,
                        "include_network_errors": True,
                    },
                }
                if self.cookie_header:
                    payload["options"].setdefault("headers", {})["Cookie"] = self.cookie_header
                if self.extra_headers:
                    payload["options"].setdefault("headers", {})["X-Extra-Headers"] = self.extra_headers
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

                attempt_info = {
                    "provider": provider,
                    "render": render,
                    "format": fmt,
                    "status": resp.status_code,
                    "text": resp.text[:500],
                }
                if resp.status_code != 200:
                    attempts.append(attempt_info)
                    continue

                data = resp.json()
                items = data.get("items") or data.get("results") or []
                if not items:
                    attempts.append(attempt_info | {"reason": "no_items"})
                    continue

                # Return early if any item has textual content.
                for item in items:
                    if any(
                        isinstance(item.get(k), str) and item.get(k).strip()
                        for k in ("html", "content", "text", "raw_html", "raw_content", "body")
                    ):
                        return items
                    meta = item.get("provider_meta") or {}
                    if isinstance(meta, dict):
                        raw_html = meta.get("html")
                        if isinstance(raw_html, str) and raw_html.strip():
                            return items

                attempts.append(attempt_info | {"reason": "items_without_content", "sample_item": items[0]})

        self.fail(f"No extraction with content succeeded. Attempts: {attempts}")

    @staticmethod
    def _aggregate_html(items):
        """Aggregate html/text blobs from extraction results."""
        blobs = []
        for item in items:
            for key in ("html", "content", "text", "raw_html", "raw_content", "body"):
                val = item.get(key)
                if isinstance(val, str):
                    blobs.append(val)
            # Include provider_meta.html if present (when include_html is true).
            meta = item.get("provider_meta") or {}
            if isinstance(meta, dict):
                raw_html = meta.get("html")
                if isinstance(raw_html, str):
                    blobs.append(raw_html)
        return " ".join(blobs)

    def test_can_extract_service_metrics_from_homepage(self):
        items = self._fetch_homepage_via_gateway()
        html_blob = self._aggregate_html(items)
        self.assertTrue(
            html_blob,
            f"Extractor returned no textual or HTML content. Sample item: {items[0]}",
        )
        self._print_diagnostics(items)

        # Normalized text for simpler matching if HTML was stripped by sanitizer.
        normalized = re.sub(r"\s+", " ", html_blob)
        norm_upper = re.sub(r"[^A-Z0-9 ]+", " ", normalized.upper())

        for service, expected_labels in self.expected_services.items():
            block = self._find_service_block(html_blob, service)
            self.assertIsNotNone(block, f"Did not find service block for {service}")

            self.assertIn(
                service.upper(),
                norm_upper,
                f"Did not find service name '{service}' in extracted content. "
                f"First 400 chars: {normalized[:400]}",
            )
            # Ensure each expected metric label appears somewhere in the content.
            missing_labels = [
                label for label in expected_labels if label.upper() not in norm_upper
            ]
            self.assertFalse(
                missing_labels,
                f"Missing expected metric labels for {service}: {missing_labels}. "
                f"First 400 chars: {normalized[:400]}",
            )

            links = self._extract_links(block)
            icons = self._extract_icons(block)
            self.assertTrue(links, f"No links found for {service}")
            self.assertTrue(icons, f"No icons found for {service}")

            # Emit snippets, parsed metrics, links, and icons.
            snippet = self._service_snippets(normalized, norm_upper, [service]).get(service, "")
            metrics = self._extract_metrics_from_snippet(snippet)
            print(f"[scrape] {service}: {snippet}")
            print(f"[metrics] {service}: {metrics}")
            print(f"[links] {service}: {links}")
            print(f"[icons] {service}: {icons}")

    @staticmethod
    def _print_diagnostics(items):
        # Print console logs and network errors if present.
        for idx, item in enumerate(items):
            meta = item.get("provider_meta") or {}
            logs = meta.get("console_logs") or []
            if logs:
                print(f"[console][item {idx}] count={len(logs)}")
                for log in logs:
                    print(f"[console][{log.get('type')}] {log.get('text')} @ {log.get('location')}")
            errors = meta.get("network_errors") or []
            if errors:
                print(f"[neterr][item {idx}] count={len(errors)}")
                for err in errors:
                    print(f"[neterr] {err.get('method')} {err.get('url')} -> {err.get('failure')}")

    @staticmethod
    def _service_snippets(normalized, norm_upper, services):
        """
        Return a short snippet of normalized text for each service, starting at the
        first occurrence of the service name up to the next service (or 180 chars).
        """
        positions = []
        for svc in services:
            pos = norm_upper.find(svc.upper())
            if pos != -1:
                positions.append((svc, pos))

        snippets = {}
        positions_sorted = sorted(positions, key=lambda x: x[1])
        for idx, (svc, pos) in enumerate(positions_sorted):
            next_pos = positions_sorted[idx + 1][1] if idx + 1 < len(positions_sorted) else len(norm_upper)
            # Map positions from uppercase to original normalized (same length after stripping non-alnum -> but we preserved spaces only)
            # Use pos indices on normalized as well, since we only uppercased and stripped punctuation separately.
            snippet = normalized[pos: min(next_pos, pos + 180)].strip()
            snippets[svc] = snippet
        return snippets

    @staticmethod
    def _extract_metrics_from_snippet(snippet):
        """
        Simple heuristic: capture uppercase tokens and preceding numbers if present.
        Returns dict[label] = value_or_placeholder.
        """
        metrics = {}
        pairs = re.findall(r"([0-9A-Za-z\-\\+\\.]+)\\s+([A-Z][A-Z0-9 ]+)", snippet)
        for value, label in pairs:
            cleaned_label = label.strip()
            cleaned_value = value.strip()
            metrics[cleaned_label] = cleaned_value
        return metrics

    @staticmethod
    def _find_service_block(html, service_name):
        pattern = (
            r"<li[^>]*class=\"[^\"]*service[^\"]*\"[^>]*>.*?"
            + re.escape(service_name)
            + r".*?</li>"
        )
        match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
        return match.group(0) if match else None

    @staticmethod
    def _extract_links(block_html):
        return re.findall(r'href=["\\\']([^"\\\']+)["\\\']', block_html, flags=re.IGNORECASE)

    @staticmethod
    def _extract_icons(block_html):
        return re.findall(r'src=["\\\']([^"\\\']+)["\\\']', block_html, flags=re.IGNORECASE)


if __name__ == "__main__":
    unittest.main()
