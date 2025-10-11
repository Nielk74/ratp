"""Tests for the ratp.fr traffic scraper."""

from __future__ import annotations

from typing import Dict, Iterable, List, Tuple
from unittest.mock import Mock

import pytest

from backend.services.scrapers.ratp_traffic import RatpTrafficScraper


class _DummyResponse:
    def __init__(self, payload: Dict):
        self._payload = payload
        self.status_code = 200

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


class _DummySession:
    def __init__(self, payloads: Iterable[Dict]):
        self._payloads = list(payloads)
        self.headers: Dict[str, str] = {}
        self.requests: List[Tuple[str, float]] = []

    def get(self, url: str, timeout: float = 15.0):
        self.requests.append((url, timeout))
        if self._payloads:
            payload = self._payloads.pop(0)
        else:
            payload = {}
        return _DummyResponse(payload)


class _FakeHttpScraper:
    def __init__(self, session: _DummySession):
        self._session = session

    def get_session(self, *, context=None, force: bool = False):  # pylint: disable=unused-argument
        return self._session


def _build_scraper_with_payloads(payloads: Iterable[Dict]) -> RatpTrafficScraper:
    session = _DummySession(payloads)
    http_scraper = _FakeHttpScraper(session)
    return RatpTrafficScraper(http_scraper=http_scraper)


def test_fetch_status_groups_entries_across_networks():
    payloads = [
        {"result": [{"line": "1", "slug": "normal", "message": "<b>OK</b>"}]},
        {"result": []},
        {"result": []},
        {"result": []},
    ]

    scraper = _build_scraper_with_payloads(payloads)
    result, errors = scraper.fetch_status()

    assert errors == []
    assert "metros" in result
    assert result["metros"][0]["message"] == "OK"
    assert result["metros"][0]["line"] == "1"


def test_fetch_status_filters_line_code():
    payloads = [
        {
            "result": [
                {"line": "1", "slug": "normal", "message": "OK"},
                {"line": "14", "slug": "alerte", "message": "Incident"},
            ]
        },
        {"result": []},
        {"result": []},
        {"result": []},
    ]

    scraper = _build_scraper_with_payloads(payloads)
    result, errors = scraper.fetch_status(line_code="14")

    assert errors == []
    assert "metros" in result
    lines = result["metros"]
    assert len(lines) == 1
    assert lines[0]["line"] == "14"
    assert lines[0]["slug"] == "alerte"


def test_fetch_status_collects_errors(monkeypatch):
    scraper = _build_scraper_with_payloads([{}, {}, {}, {}])

    fetch_mock = Mock(side_effect=[RuntimeError("blocked"), [], [], []])
    monkeypatch.setattr(scraper, "_fetch_network", fetch_mock)

    result, errors = scraper.fetch_status()

    assert result == {}
    assert errors == ["metros: blocked"]
    assert fetch_mock.call_count == 4
