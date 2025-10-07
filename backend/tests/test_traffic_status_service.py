"""Tests for traffic status normalisation."""

from backend.services.traffic_status import TrafficStatusService


def test_normalise_prefers_prim_data():
    service = TrafficStatusService()
    payload = {
        "status": "ok",
        "source": "prim_api",
        "timestamp": "2025-10-07T00:00:00",
        "data": {
            "line_reports": [
                {
                    "line": {"code": "1"},
                    "status": {
                        "severity": "information",
                        "message": "Minor delays",
                        "effect": "DELAYED",
                    },
                    "disruption": {"description": "Maintenance work"},
                }
            ]
        },
        "result": {
            "metros": [
                {
                    "line": "1",
                    "slug": "normal",
                    "title": "Trafic normal",
                }
            ]
        },
    }

    normalised = service.normalise(payload)
    assert normalised["status"] == "ok"
    assert normalised["source"] == "prim_api"
    assert normalised["default"]["level"] == "normal"
    assert len(normalised["lines"]) == 1
    line = normalised["lines"][0]
    assert line["line_code"] == "1"
    assert line["level"] == "warning"
    assert line["source"] == "prim"
    assert "Maintenance work" in line["message"]


def test_normalise_uses_community_when_no_prim():
    service = TrafficStatusService()
    payload = {
        "status": "unavailable",
        "source": "community_api",
        "result": {
            "metros": [
                {
                    "line": "2",
                    "slug": "alerte",
                    "message": "Incident en cours",
                }
            ]
        },
    }

    normalised = service.normalise(payload)
    assert normalised["default"]["level"] == "unknown"
    assert len(normalised["lines"]) == 1
    line = normalised["lines"][0]
    assert line["line_code"] == "2"
    assert line["level"] == "disrupted"
    assert line["source"] == "community"
