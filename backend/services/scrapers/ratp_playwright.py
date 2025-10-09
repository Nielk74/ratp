"""Playwright-based scraper experiment for RATP schedule pages.

This remains a workaround while we wait for official SIRI / GTFS-RT feeds. It
drives a headless (or headed) Chromium instance, passes the Cloudflare
challenge, and extracts the next departures for a given line/station/direction
combination from https://www.ratp.fr.

⚠️ The target site does not expose a stable API for this purpose. Selectors and
payload shapes may change at any time, so treat this module as experimental.
"""

from __future__ import annotations

import json
import time
import os
import random
import subprocess
import contextlib
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import quote_plus

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright


@dataclass
class ScrapedDeparture:
    """Represents a single departure entry scraped from the page."""

    raw_text: str
    destination: Optional[str] = None
    waiting_time: Optional[str] = None
    status: Optional[str] = None
    platform: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScraperResult:
    """Structured response returned by the scraper."""

    url: str
    departures: List[ScrapedDeparture]
    raw_state: Dict[str, Any]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "departures": [item.to_dict() for item in self.departures],
            "raw_state": self.raw_state,
            "metadata": self.metadata,
        }


class RatpPlaywrightScraper:
    """Scraper abstraction delivering RATP schedule information via Playwright."""

    BASE_URL = "https://www.ratp.fr/horaires"

    def __init__(
        self,
        headless: bool = True,
        challenge_delay: float = 8.0,
        wait_timeout: float = 20.0,
        use_xvfb: bool = False,
    ) -> None:
        self.headless = headless
        self.challenge_delay = challenge_delay
        self.wait_timeout = wait_timeout
        self.use_xvfb = use_xvfb

    @contextlib.contextmanager
    def _virtual_display(self):
        if self.headless or os.getenv("DISPLAY"):
            yield
            return

        if not self.use_xvfb:
            yield
            return

        display_id = f":{random.randint(90, 110)}"
        cmd = [
            "Xvfb",
            display_id,
            "-screen",
            "0",
            "1280x1024x24",
            "-nolisten",
            "tcp",
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.5)
        if proc.poll() is not None:
            raise RuntimeError("Failed to start Xvfb display")
        original_display = os.getenv("DISPLAY")
        os.environ["DISPLAY"] = display_id
        try:
            yield
        finally:
            if original_display is not None:
                os.environ["DISPLAY"] = original_display
            else:
                os.environ.pop("DISPLAY", None)
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()

    def fetch_station_board(
        self,
        line: str,
        station: str,
        direction: str,
        *,
        network: str = "metro",
        language: str = "fr",
    ) -> ScraperResult:
        """Fetch live departure information for the requested station."""

        url = self._build_url(network=network, line=line, station=station, direction=direction)
        with self._virtual_display():
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    headless=self.headless,
                    args=[
                        "--disable-gpu",
                        "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--lang=%s" % language,
                ],
            )
            context = browser.new_context(
                locale=language,
                viewport={"width": 1280, "height": 1024},
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                ),
            )
            context.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(window, 'chrome', {get: () => ({runtime: {}})});
                Object.defineProperty(navigator, 'plugins', {
                  get: () => [1, 2, 3, 4, 5],
                });
                Object.defineProperty(navigator, 'languages', {get: () => ['fr-FR', 'fr']});
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = parameters =>
                  parameters.name === 'notifications'
                    ? Promise.resolve({ state: 'default' })
                    : originalQuery(parameters);
                """
            )
            page = context.new_page()
            api_payload: Optional[Dict[str, Any]] = None
            api_status: Optional[int] = None
            used_form_flow = False
            cloudflare_blocked = False

            def _capture_response(response):
                nonlocal api_payload
                nonlocal api_status
                if "/api/horaires" in response.url and api_payload is None:
                    api_status = response.status
                    if response.ok:
                        try:
                            api_payload = response.json()
                        except Exception:  # pylint: disable=broad-except
                            api_payload = None

            page.on("response", _capture_response)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=self.wait_timeout * 1000)
            except PlaywrightTimeoutError:
                # Let the rest of the routine try to recover.
                pass

            self._handle_consent(page)

            if self._is_challenge_page(page):
                if self._navigate_via_form(page, network=network, line=line, station=station):
                    used_form_flow = True
                else:
                    cloudflare_blocked = True

            if not used_form_flow and not self._has_departure_container(page):
                if self._navigate_via_form(page, network=network, line=line, station=station):
                    used_form_flow = True
                elif self._is_challenge_page(page):
                    cloudflare_blocked = True

            if self.challenge_delay > 0:
                time.sleep(self.challenge_delay)

            try:
                page.wait_for_selector(
                    '[data-component="next-departures"], .next-departures, .horaires-next',
                    timeout=self.wait_timeout * 1000,
                    state="attached",
                )
            except PlaywrightTimeoutError:
                # Some stations temporarily miss the container; we'll rely on JS state.
                pass

            raw_state = self._extract_state(page)
            departures = self._extract_departures(page, raw_state, direction=direction)

            if not api_payload:
                api_payload = self._fetch_api_payload(
                    page,
                    params={"espace": network, "ligne": line, "station": station, "sens": direction},
                )

            if api_payload:
                api_payload = self._ensure_json_serializable(api_payload)
                departures.extend(self._from_api(api_payload))

            metadata = {
                "line": line,
                "station": station,
                "direction": direction,
                "network": network,
                "timestamp": time.time(),
                "headless": self.headless,
                "browser": "chromium",
                "api_source": bool(api_payload),
                "final_url": page.url,
                "api_status": api_status,
                "form_flow": used_form_flow,
                "cloudflare_blocked": cloudflare_blocked,
            }
            context.close()
            browser.close()

        return ScraperResult(url=url, departures=departures, raw_state=raw_state, metadata=metadata)

    # Internal helpers ---------------------------------------------------------------

    def _build_url(self, *, network: str, line: str, station: str, direction: str) -> str:
        params = {
            "espace": network,
            "ligne": line,
            "station": station,
            "sens": direction,
        }
        query = "&".join(f"{key}={quote_plus(value)}" for key, value in params.items())
        return f"{self.BASE_URL}?{query}"

    def _extract_state(self, page) -> Dict[str, Any]:
        script_candidates = [
            "window.__NEXT_DATA__",
            "window.__NUXT__",
            "window.drupalSettings",
            "window.__INITIAL_STATE__",
        ]
        for script in script_candidates:
            try:
                state = page.evaluate(script)
            except PlaywrightTimeoutError:
                continue
            except Exception:  # pylint: disable=broad-except
                continue
            if state:
                return self._ensure_json_serializable(state)
        return {}

    def _handle_consent(self, page) -> None:
        """Dismiss cookie/privacy banners that block the schedule widgets."""

        selectors = [
            "#popin_tc_privacy_button_3",
            "#tc_privacy_button_3",
            'button[title="Accepter et fermer"]',
            'button[data-testid="uc-accept-all-button"]',
            'button:has-text("Tout accepter")',
        ]

        def _click_in_frame(frame) -> bool:
            for selector in selectors:
                try:
                    handle = frame.wait_for_selector(selector, state="attached", timeout=3000)
                except PlaywrightTimeoutError:
                    continue
                except Exception:  # pylint: disable=broad-except
                    continue
                if handle:
                    try:
                        handle.click()
                        frame.wait_for_timeout(500)
                        return True
                    except Exception:  # pylint: disable=broad-except
                        continue
            return False

        if _click_in_frame(page):
            return

        main_frame = page.main_frame
        for frame in page.frames:
            if frame == main_frame:
                continue
            if _click_in_frame(frame):
                return

    def _fetch_api_payload(self, page, params: Dict[str, str]) -> Optional[Dict[str, Any]]:
        query = "&".join(f"{key}={quote_plus(value)}" for key, value in params.items())
        url = f"https://www.ratp.fr/api/horaires?{query}"
        script = (
            "return fetch('"
            + url
            + "', {credentials: 'include'})"
            + ".then(res => res.ok ? res.json() : null)"
            + ".catch(() => null);"
        )
        try:
            result = page.evaluate(script)
        except Exception:  # pylint: disable=broad-except
            return None
        if isinstance(result, dict):
            return self._ensure_json_serializable(result)
        return None

    def _ensure_json_serializable(self, state: Any) -> Dict[str, Any]:
        try:
            return json.loads(json.dumps(state))
        except (TypeError, ValueError):
            if isinstance(state, dict):
                return {k: self._ensure_json_serializable(v) for k, v in state.items()}
            if isinstance(state, list):
                return [self._ensure_json_serializable(node) for node in state]
            return {"value": str(state)}

    def _extract_departures(self, page, raw_state: Dict[str, Any], direction: str) -> List[ScrapedDeparture]:
        departures: List[ScrapedDeparture] = []

        dom_departures = self._from_dom(page, requested_direction=direction)
        if dom_departures:
            departures.extend(dom_departures)

        state_departures = self._from_state(raw_state)
        if state_departures:
            departures.extend(state_departures)

        seen = set()
        unique: List[ScrapedDeparture] = []
        for entry in departures:
            key = (entry.destination, entry.waiting_time, entry.raw_text)
            if key in seen:
                continue
            seen.add(key)
            unique.append(entry)
        return unique

    def _from_api(self, payload: Dict[str, Any]) -> List[ScrapedDeparture]:
        departures: List[ScrapedDeparture] = []
        next_passages = payload.get("nextSchedules") or payload.get("result", {}).get("schedules")
        if isinstance(next_passages, list):
            for item in next_passages:
                if not isinstance(item, dict):
                    continue
                waiting_time = self._extract_best(item, ["message", "waittime", "waiting_time"])
                destination = self._extract_best(item, ["destination", "terminus", "direction"])
                departures.append(
                    ScrapedDeparture(
                        raw_text=json.dumps(item, ensure_ascii=False),
                        destination=destination,
                        waiting_time=waiting_time,
                        status=item.get("state"),
                        platform=item.get("platform"),
                        extra=item,
                    )
                )
        return departures

    def _from_dom(self, page, requested_direction: str) -> List[ScrapedDeparture]:
        departures: List[ScrapedDeparture] = []
        selectors = [
            '[data-component="next-departures"] li',
            ".next-departures li",
            ".prochains-departs li",
            ".line-schedules__next-passages li",
        ]
        for selector in selectors:
            elements = page.query_selector_all(selector)
            if not elements:
                continue
            for element in elements:
                text = (element.inner_text() or "").strip()
                if not text:
                    continue
                departures.append(
                    ScrapedDeparture(
                        raw_text=text,
                        destination=self._get_child_text(element, ".destination, .next-departure__destination"),
                        waiting_time=self._get_child_text(element, ".time, .next-departure__duration"),
                        status=self._get_child_text(element, ".status, .next-departure__status"),
                        platform=self._get_child_text(element, ".platform, .next-departure__quai"),
                    )
                )
            if departures:
                break

        if departures:
            return departures

        timetable_blocks = page.query_selector_all(".ixxi-horaire-result-timetable")
        matched_blocks = []
        for index, block in enumerate(timetable_blocks):
            try:
                label_el = block.query_selector(".destination_label")
            except Exception:  # pylint: disable=broad-except
                label_el = None
            direction_label = (label_el.inner_text().strip() if label_el else "") or ""
            if self._direction_matches(direction_label, requested_direction, index):
                matched_blocks.append((index, block, direction_label))

        if not matched_blocks and timetable_blocks:
            first_block = timetable_blocks[0]
            try:
                first_label = first_block.query_selector(".destination_label")
            except Exception:  # pylint: disable=broad-except
                first_label = None
            matched_blocks = [(0, first_block, (first_label.inner_text().strip() if first_label else "") or "")]

        for index, block, direction_label in matched_blocks:
            try:
                table = block.query_selector("table.timetable")
            except Exception:  # pylint: disable=broad-except
                table = None
            if not table:
                continue
            try:
                rows = table.query_selector_all("tr.body-metro")
            except Exception:  # pylint: disable=broad-except
                rows = []
            for row_index, row in enumerate(rows):
                try:
                    destination_el = row.query_selector(".terminus-wrap")
                    time_el = row.query_selector(".heure-wrap")
                except Exception:  # pylint: disable=broad-except
                    continue
                if not destination_el or not time_el:
                    continue
                try:
                    destination_text = destination_el.inner_text().strip()
                    time_text = time_el.inner_text().replace("\xa0", " ").strip()
                except Exception:  # pylint: disable=broad-except
                    continue
                raw_text = f"{time_text} → {destination_text}"
                departures.append(
                    ScrapedDeparture(
                        raw_text=raw_text,
                        destination=destination_text or None,
                        waiting_time=time_text or None,
                        extra={
                            "source": "timetable",
                            "direction_label": direction_label,
                            "table_index": index,
                            "row_index": row_index,
                        },
                    )
                )
        return departures

    def _get_child_text(self, element, selector: str) -> Optional[str]:
        try:
            child = element.query_selector(selector)
        except Exception:  # pylint: disable=broad-except
            return None
        if not child:
            return None
        text = (child.inner_text() or "").strip()
        return text or None

    def _from_state(self, raw_state: Dict[str, Any]) -> List[ScrapedDeparture]:
        departures: List[ScrapedDeparture] = []
        for candidate in self._iter_candidate_lists(raw_state):
            for payload in candidate:
                if not isinstance(payload, dict):
                    continue
                waiting_time = self._extract_best(payload, ["waittime", "waitingTime", "waiting_time", "message", "time"])
                destination = self._extract_best(payload, ["destination", "terminus", "direction"])
                status = self._extract_best(payload, ["state", "status"])
                platform = self._extract_best(payload, ["platform", "voie", "quai"])
                departures.append(
                    ScrapedDeparture(
                        raw_text=json.dumps(payload, ensure_ascii=False),
                        destination=destination,
                        waiting_time=waiting_time,
                        status=status,
                        platform=platform,
                        extra=payload,
                    )
                )
            if departures:
                break
        return departures

    def _iter_candidate_lists(self, data: Any) -> Iterable[List[Any]]:
        queue: List[Any] = [data]
        while queue:
            node = queue.pop(0)
            if isinstance(node, dict):
                for key, value in node.items():
                    if isinstance(value, list) and self._looks_like_departures(key, value):
                        yield value
                    queue.append(value)
            elif isinstance(node, list):
                queue.extend(node)

    def _looks_like_departures(self, key: str, value: List[Any]) -> bool:
        key_lower = key.lower()
        if any(token in key_lower for token in ("departure", "passage", "horaire", "schedule")):
            if value and isinstance(value[0], dict):
                sample_keys = {str(k).lower() for k in value[0].keys()}
                tokens = {"wait", "time", "destination", "direction", "terminus", "status"}
                return bool(sample_keys & tokens)
        return False

    def _extract_best(self, payload: Dict[str, Any], keys: Iterable[str]) -> Optional[str]:
        for key in keys:
            if key in payload and payload[key]:
                return str(payload[key])
        return None

    def _direction_matches(self, direction_label: str, requested_direction: str, block_index: int) -> bool:
        if not requested_direction:
            return True
        label_normalized = (direction_label or "").lower()
        requested = requested_direction.strip()
        if not requested:
            return True
        if len(requested) > 1:
            return requested.lower() in label_normalized
        if requested.isalpha():
            offset = ord(requested.upper()) - ord("A")
            return offset == block_index
        return requested.lower() in label_normalized

    def _is_challenge_page(self, page) -> bool:
        try:
            title = page.title()
        except Exception:  # pylint: disable=broad-except
            title = ""
        if title and "instant" in title.lower():
            return True
        try:
            challenge = page.query_selector("#challenge-error-text, #cf-chl-widget")
        except Exception:  # pylint: disable=broad-except
            challenge = None
        return challenge is not None

    def _has_departure_container(self, page) -> bool:
        try:
            container = page.query_selector(
                '[data-component="next-departures"], .ixxi-horaire-result-timetable, table.timetable'
            )
        except Exception:  # pylint: disable=broad-except
            container = None
        return container is not None

    def _navigate_via_form(self, page, *, network: str, line: str, station: str) -> bool:
        try:
            page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=self.wait_timeout * 1000)
        except PlaywrightTimeoutError:
            return False

        self._handle_consent(page)

        if self._is_challenge_page(page):
            return False

        network_key = network.lower()
        network_selector = f'label[for="edit-networks-{network_key}"]'
        try:
            locator = page.locator(network_selector)
            locator.wait_for(state="visible", timeout=self.wait_timeout * 1000)
            locator.click()
        except Exception:  # pylint: disable=broad-except
            return False

        line_id = line.lower()
        line_selector = f'label[for="edit-line-{network_key}-{line_id}"]'
        try:
            line_locator = page.locator(line_selector)
            line_locator.wait_for(state="visible", timeout=self.wait_timeout * 1000)
            line_locator.click()
        except Exception:  # pylint: disable=broad-except
            return False

        station_selector = f'input[data-drupal-selector="edit-stop-point-{network_key}"]'
        try:
            station_input = page.locator(station_selector)
            station_input.wait_for(state="visible", timeout=self.wait_timeout * 1000)
            station_input.fill("")
            station_input.type(station, delay=75)
        except Exception:  # pylint: disable=broad-except
            return False

        try:
            suggestion = page.locator("ul.autocomplete-horaire-list li").first
            suggestion.wait_for(state="visible", timeout=self.wait_timeout * 1000)
            suggestion.click()
        except Exception:  # pylint: disable=broad-except
            return False

        try:
            page.wait_for_selector(".ixxi-horaire-result-timetable table.timetable tr.body-metro", timeout=self.wait_timeout * 1000)
        except PlaywrightTimeoutError:
            return False

        return True


def _format_departure(departure: ScrapedDeparture) -> str:
    pieces = [
        departure.waiting_time or "?",
        "→",
        departure.destination or "Unknown",
    ]
    if departure.status:
        pieces.append(f"({departure.status})")
    if departure.platform:
        pieces.append(f"[platform {departure.platform}]")
    return " ".join(pieces)


def _print_result(result: ScraperResult) -> None:
    print(f"URL: {result.url}")
    print("Metadata:")
    for key, value in sorted(result.metadata.items()):
        print(f"  - {key}: {value}")
    print("\nDepartures:")
    if not result.departures:
        print("  (no departures found)")
    for item in result.departures:
        print(f"  - {_format_departure(item)}")
    print("\nHint: raw state is large; write result.to_dict() to json if needed.")


if __name__ == "__main__":
    import argparse
    import pprint

    parser = argparse.ArgumentParser(description="Probe RATP departures via Playwright workaround.")
    parser.add_argument("--line", required=True, help="Line code, ex: 1")
    parser.add_argument("--station", required=True, help="Station slug displayed on ratp.fr")
    parser.add_argument("--direction", required=True, help="Direction A/B or numeric depending on the line.")
    parser.add_argument("--network", default="metro", help="Transport network (metro, rer, tram, bus).")
    parser.add_argument("--language", default="fr", help="Browser language to request.")
    parser.add_argument("--headless", action="store_true", help="Run Chromium in headless mode.")
    parser.add_argument("--no-headless", action="store_true", help="Force disable headless mode.")
    parser.add_argument("--challenge-delay", type=float, default=8.0, help="Seconds to wait after initial load.")
    parser.add_argument("--wait-timeout", type=float, default=20.0, help="Explicit wait timeout in seconds.")
    parser.add_argument("--dump-state", action="store_true", help="Pretty-print the raw JS state.")

    cli_args = parser.parse_args()

    headless = True
    if cli_args.headless:
        headless = True
    elif cli_args.no_headless:
        headless = False

    scraper = RatpPlaywrightScraper(
        headless=headless,
        challenge_delay=cli_args.challenge_delay,
        wait_timeout=cli_args.wait_timeout,
    )

    result = scraper.fetch_station_board(
        line=cli_args.line,
        station=cli_args.station,
        direction=cli_args.direction,
        network=cli_args.network,
        language=cli_args.language,
    )
    _print_result(result)

    if cli_args.dump_state:
        pprint.pp(result.raw_state)


__all__ = ["RatpPlaywrightScraper", "ScrapedDeparture", "ScraperResult"]
