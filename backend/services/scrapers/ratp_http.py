"""Cloudscraper-based scraper for RATP schedule pages."""

from __future__ import annotations

import json
import re
import time
import unicodedata
from dataclasses import dataclass
import threading
from typing import Any, Dict, List, Optional

import cloudscraper
from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright
from requests.cookies import RequestsCookieJar

from ..station_data import STATION_FALLBACKS
from .ratp_playwright import ScrapedDeparture, ScraperResult

BASE_HORAIRES_URL = "https://www.ratp.fr/horaires"
_PLAYWRIGHT_LOCK = threading.Lock()


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn").lower()


@dataclass
class _StopPoint:
    name: str
    stop_place_id: str
    line_id: str


class RatpHttpScraper:
    """Grab schedule snippets using the public ajax endpoints protected by Cloudflare."""

    def __init__(self) -> None:
        self._line_id_cache: Dict[str, str] = {}
        self._stop_points_cache: Dict[str, List[_StopPoint]] = {}
        self._session_state = threading.local()

    def fetch_station_board(
        self,
        *,
        network: str,
        line: str,
        station: str,
        direction: str,
    ) -> ScraperResult:
        network_segment = network.lower()
        line_code = line.upper()

        context = {"network": network_segment, "line": line_code, "station": station}

        line_id = self._get_line_id(network_segment, line_code, context=context)
        stop_point = self._find_stop_point(network_segment, line_code, station, context=context)
        if not stop_point:
            raise ValueError(f"Unknown stop {station} on {network}:{line}")

        params = {
            "stopPlaceName": station,
            "type": "now",
            "sens": direction.upper(),
        }
        url = f"https://www.ratp.fr/horaires/blocs-horaires-next-passages/{network_segment}/{stop_point.line_id}/{stop_point.stop_place_id}"
        response = self._request(url, params=params, context=context)
        response.raise_for_status()

        html = json.loads(response.text)
        soup = BeautifulSoup(html, "html.parser")

        blocks = soup.select(".ixxi-horaire-result-timetable")
        block_index = 0 if direction.upper() == "A" else 1
        if block_index >= len(blocks):
            block_index = 0

        selected_block = blocks[block_index] if blocks else None
        departures = self._parse_departures(selected_block)

        metadata = {
            "line": line,
            "station": station,
            "direction": direction,
            "network": network,
            "line_id": stop_point.line_id,
            "stop_place_id": stop_point.stop_place_id,
            "timestamp": time.time(),
            "source": "cloudscraper",
            "final_url": url,
            "cloudflare_blocked": False,
            "form_flow": False,
        }

        return ScraperResult(
            url=url,
            departures=departures,
            raw_state={"html": html},
            metadata=metadata,
        )

    def _get_line_id(self, network: str, line: str, *, context: Optional[Dict[str, str]] = None) -> str:
        cache_key = f"{network}:{line}"
        if cache_key in self._line_id_cache:
            return self._line_id_cache[cache_key]

        url = f"https://www.ratp.fr/horaires/api/getLineId/{network}/{line}"
        response = self._request(url, context=context)
        response.raise_for_status()
        line_id = response.json() if response.headers.get("Content-Type", "").startswith("application/json") else response.text
        line_id = line_id.strip().strip('"')
        self._line_id_cache[cache_key] = line_id
        return line_id

    def _fetch_stop_points(self, network: str, line: str, *, context: Optional[Dict[str, str]] = None) -> List[_StopPoint]:
        cache_key = f"{network}:{line}"
        if cache_key in self._stop_points_cache:
            return self._stop_points_cache[cache_key]

        url = f"https://www.ratp.fr/horaires/api/getStopPoints/{network}/{line}"
        response = self._request(url, context=context)
        response.raise_for_status()
        payload = response.json()
        entries = [
            _StopPoint(name=item.get("name", ""), stop_place_id=item.get("stop_place_id", ""), line_id=item.get("line_id", ""))
            for item in payload
            if item.get("stop_place_id") and item.get("line_id")
        ]
        self._stop_points_cache[cache_key] = entries
        return entries

    def _find_stop_point(
        self,
        network: str,
        line: str,
        station: str,
        *,
        context: Optional[Dict[str, str]] = None,
    ) -> _StopPoint | None:
        normalized_station = _normalize(station)
        candidates = self._fetch_stop_points(network, line, context=context)
        for candidate in candidates:
            if _normalize(candidate.name) == normalized_station:
                return candidate
        return None

    def _parse_departures(self, block) -> List[ScrapedDeparture]:
        departures: List[ScrapedDeparture] = []
        if not block:
            return departures

        table = block.select_one("table.timetable")
        if not table:
            return departures

        for row in table.select("tr.body-metro"):
            dest = row.select_one(".terminus-wrap")
            wait = row.select_one(".heure-wrap")
            status = row.select_one(".type-horaire-td span")

            if not dest or not wait:
                continue

            departure = ScrapedDeparture(
                raw_text=f"{wait.get_text(strip=True)} → {dest.get_text(strip=True)}",
                destination=dest.get_text(strip=True),
                waiting_time=wait.get_text(strip=True),
                status=status.get_text(strip=True) if status else None,
            )
            departures.append(departure)

        return departures

    # Internal helpers -------------------------------------------------

    def _request(
        self,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, str]] = None,
    ):
        session = self._ensure_session(context=context)
        headers = {}
        referer = self._build_referer(context)
        if referer:
            headers["Referer"] = referer
        response = session.get(url, params=params, timeout=12, headers=headers or None)
        if response.status_code == 403 or "Just a moment" in response.text:
            session = self._ensure_session(force=True, context=context)
            referer = self._build_referer(context)
            if referer:
                headers["Referer"] = referer
            response = session.get(url, params=params, timeout=12, headers=headers or None)
        return response

    def _ensure_session(self, *, force: bool = False, context: Optional[Dict[str, str]] = None):
        now = time.time()
        state = getattr(self._session_state, "value", None)
        should_create = force
        if state is None:
            should_create = True
        else:
            session_age = now - state.get("created", 0.0)
            if session_age > 600:
                should_create = True

        if should_create:
            session = self._create_session(context=context)
            self._session_state.value = {"session": session, "created": now}
            return session

        return state["session"]

    def _create_session(self, context: Optional[Dict[str, str]] = None):
        session = cloudscraper.create_scraper()
        self._refresh_cookies(session, request_context=context)
        session.headers.setdefault("Accept", "application/json, text/plain, */*")
        session.headers.setdefault("Accept-Language", "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7")
        session.headers.setdefault("Origin", "https://www.ratp.fr")
        return session

    def _refresh_cookies(self, session, request_context: Optional[Dict[str, str]] = None):
        request_context = request_context or {}
        targets = self._build_navigation_targets(request_context)
        cookies: List[Dict[str, Any]] = []
        user_agent = None
        with _PLAYWRIGHT_LOCK:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                browser_context = browser.new_context()
                page = browser_context.new_page()
                try:
                    for target in targets:
                        try:
                            page.goto(target, wait_until="domcontentloaded", timeout=60000)
                            page.wait_for_timeout(2000)
                        except PlaywrightTimeoutError:
                            continue
                except PlaywrightTimeoutError:
                    pass
                page.wait_for_timeout(2000)
                cookies = browser_context.cookies()
                try:
                    user_agent = page.evaluate("() => navigator.userAgent")
                except Exception:  # pylint: disable=broad-except
                    user_agent = None
                browser_context.close()
                browser.close()

        jar = RequestsCookieJar()
        for cookie in cookies:
            jar.set(cookie.get("name"), cookie.get("value"), domain=cookie.get("domain"), path=cookie.get("path"))
        session.cookies.update(jar)
        if user_agent:
            session.headers["User-Agent"] = user_agent

    def _build_navigation_targets(self, request_context: Dict[str, str]) -> List[str]:
        network = request_context.get("network")
        line = request_context.get("line")
        station = request_context.get("station")
        targets: List[str] = [BASE_HORAIRES_URL]

        if network and line:
            targets.append(f"{BASE_HORAIRES_URL}/{network}/{line}")
            station_candidates = self._collect_station_candidates(network, line, station)
            for candidate in station_candidates:
                slug = self._station_slug(candidate)
                if not slug:
                    continue
                targets.append(f"https://www.ratp.fr/horaires/{network}/{line}/{slug}")

        seen: set[str] = set()
        unique_targets: List[str] = []
        for target in targets:
            if target in seen:
                continue
            seen.add(target)
            unique_targets.append(target)
        return unique_targets

    def _collect_station_candidates(self, network: str, line: str, station: Optional[str]) -> List[str]:
        candidates: List[str] = []
        if station:
            candidates.append(station)

        fallbacks = STATION_FALLBACKS.get(network, {}).get(line)
        if fallbacks:
            for entry in fallbacks:
                name = entry.get("slug") or entry.get("name")
                if name:
                    candidates.append(name)

        seen: set[str] = set()
        ordered: List[str] = []
        for candidate in candidates:
            key = candidate.lower()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(candidate)
        return ordered

    @staticmethod
    def _station_slug(value: str) -> str:
        normalized = unicodedata.normalize("NFD", value)
        stripped = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
        stripped = stripped.lower()
        stripped = stripped.replace("œ", "oe").replace("æ", "ae")
        stripped = stripped.replace("’", " ").replace("'", " ")
        stripped = stripped.replace("–", "-").replace("—", "-")
        stripped = re.sub(r"[^a-z0-9]+", "-", stripped)
        return stripped.strip("-")

    def _build_referer(self, context: Optional[Dict[str, str]]) -> Optional[str]:
        if not context:
            return BASE_HORAIRES_URL
        network = context.get("network")
        line = context.get("line")
        station = context.get("station")
        if network and line and station:
            slug = self._station_slug(station)
            if slug:
                return f"{BASE_HORAIRES_URL}/{network}/{line}/{slug}"
        if network and line:
            return f"{BASE_HORAIRES_URL}/{network}/{line}"
        return BASE_HORAIRES_URL
