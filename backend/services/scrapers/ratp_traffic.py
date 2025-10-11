"""Traffic status scraper that emulates the public ratp.fr web client."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from bs4 import BeautifulSoup

from .ratp_http import RatpHttpScraper


_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
)


def _strip_html(value: Optional[str]) -> str:
    if not value:
        return ""
    if "<" not in value:
        return value.strip()
    soup = BeautifulSoup(value, "html.parser")
    return soup.get_text(" ", strip=True)


@dataclass
class TrafficEntry:
    """Normalised traffic message emitted by the public site."""

    line: str
    slug: str
    title: str
    message: str
    updated_at: Optional[str]
    raw: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "line": self.line,
            "slug": self.slug,
            "title": self.title,
            "message": self.message,
        }
        if self.updated_at:
            payload["updated_at"] = self.updated_at
        payload["_raw"] = self.raw
        return payload


class RatpTrafficScraper:
    """Fetch line traffic messages by mimicking the ratp.fr Ajax calls."""

    _NETWORK_ENDPOINTS = {
        "metros": "metros",
        "rers": "rers",
        "tramways": "tramways",
        "trains": "trains",
    }

    def __init__(
        self,
        *,
        base_url: str = "https://www.ratp.fr/api/traffic",
        http_scraper: Optional[RatpHttpScraper] = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._http_scraper = http_scraper or RatpHttpScraper()
        self._session_lock = threading.Lock()
        self._session = None

    # Public API -----------------------------------------------------------------

    def fetch_status(
        self,
        *,
        line_code: Optional[str] = None,
    ) -> Tuple[Dict[str, List[Dict[str, Any]]], List[str]]:
        """Return community-style traffic payload grouped by network."""

        aggregated: Dict[str, List[Dict[str, Any]]] = {}
        errors: List[str] = []

        normalized_code = line_code.strip().upper() if line_code else None

        for result_key, endpoint in self._NETWORK_ENDPOINTS.items():
            try:
                entries = self._fetch_network(endpoint, result_key)
            except Exception as exc:  # pylint: disable=broad-except
                errors.append(f"{result_key}: {exc}")
                continue

            if not entries:
                continue

            if normalized_code:
                entries = [
                    entry for entry in entries if entry.line.upper() == normalized_code
                ]
                if not entries:
                    continue

            aggregated[result_key] = [entry.to_dict() for entry in entries]

        return aggregated, errors

    # Internal helpers -----------------------------------------------------------

    def _fetch_network(self, endpoint: str, result_key: str) -> List[TrafficEntry]:
        url = f"{self._base_url}/{endpoint}"
        response = self._request(url, context={"network": endpoint})
        payload: Dict[str, Any]
        try:
            payload = response.json()
        except json.JSONDecodeError:
            payload = {}

        entries = self._extract_entries(payload, result_key)
        normalised = [self._normalise_entry(entry) for entry in entries]
        return [entry for entry in normalised if entry is not None]

    def _request(self, url: str, *, context: Optional[Dict[str, str]] = None):
        session = self._ensure_session(context=context)
        response = session.get(url, timeout=15)
        if response.status_code in {403, 429, 503}:
            session = self._ensure_session(force=True, context=context)
            response = session.get(url, timeout=15)
        response.raise_for_status()
        return response

    def _ensure_session(
        self,
        *,
        force: bool = False,
        context: Optional[Dict[str, str]] = None,
    ):
        with self._session_lock:
            if force or self._session is None:
                self._session = self._create_session(context=context, force=force)
            return self._session

    def _create_session(
        self,
        *,
        context: Optional[Dict[str, str]] = None,
        force: bool = False,
    ):
        # RatpHttpScraper already encapsulates the Playwright-based cookie dance.
        session = self._http_scraper.get_session(context=context, force=force)
        session.headers.setdefault("User-Agent", _USER_AGENT)
        session.headers.setdefault("Referer", "https://www.ratp.fr/infos-trafic")
        return session

    @staticmethod
    def _extract_entries(payload: Dict[str, Any], result_key: str) -> List[Dict[str, Any]]:
        if not payload:
            return []

        result = payload.get("result")
        if isinstance(result, list):
            return [entry for entry in result if isinstance(entry, dict)]

        if isinstance(result, dict):
            candidates: Iterable[str] = (
                result_key,
                result_key.rstrip("s"),
                f"{result_key}_lines",
                "lines",
            )
            for key in candidates:
                value = result.get(key)
                if isinstance(value, list):
                    return [entry for entry in value if isinstance(entry, dict)]
                if isinstance(value, dict):
                    nested = value.get("results") or value.get("records") or value.get("items")
                    if isinstance(nested, list):
                        return [entry for entry in nested if isinstance(entry, dict)]

        return []

    @staticmethod
    def _normalise_entry(entry: Dict[str, Any]) -> Optional[TrafficEntry]:
        if not entry:
            return None

        line_code = (
            entry.get("line")
            or entry.get("code")
            or entry.get("id")
            or entry.get("identifier")
            or ""
        )
        line_code = str(line_code).strip()
        if not line_code:
            return None

        slug = (
            entry.get("slug")
            or entry.get("state")
            or entry.get("status")
            or entry.get("severity")
            or "unknown"
        )
        slug = str(slug).strip().lower() or "unknown"

        title = _strip_html(
            entry.get("title")
            or entry.get("headline")
            or entry.get("summary")
            or entry.get("message")
        )

        message = _strip_html(
            entry.get("message")
            or entry.get("text")
            or entry.get("description")
            or entry.get("detail")
            or title
        )

        updated_at = (
            entry.get("updated_at")
            or entry.get("updatedAt")
            or entry.get("last_update")
            or entry.get("lastUpdate")
            or entry.get("date")
        )
        if isinstance(updated_at, dict):
            updated_at = updated_at.get("value") or updated_at.get("iso")
        if isinstance(updated_at, (int, float)):
            updated_at = str(updated_at)

        if not title:
            title = f"Ligne {line_code} - état {slug}"

        return TrafficEntry(
            line=line_code.upper(),
            slug=slug,
            title=title,
            message=message,
            updated_at=str(updated_at).strip() if updated_at else None,
            raw=entry,
        )
