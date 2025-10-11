"""Utilities to normalise traffic data coming from external APIs."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

LineStatus = Dict[str, Any]


class TrafficStatusService:
    """Normalises traffic payloads into line-centric status summaries."""

    LEVEL_PRIORITY = {
        "normal": 0,
        "warning": 1,
        "disrupted": 2,
        "closed": 3,
        "unknown": 0,
    }

    COMMUNITY_SLUG_LEVEL = {
        "normal": "normal",
        "ok": "normal",
        "info": "warning",
        "travaux": "warning",
        "slowdown": "warning",
        "ralentissement": "warning",
        "perturbation": "warning",
        "alerte": "disrupted",
        "alerte_fermeture": "closed",
        "alertefermeture": "closed",
        "alertefermee": "closed",
        "alerte_fermee": "closed",
        "critical": "closed",
        "unknow": "unknown",
    }

    PRIM_SEVERITY_LEVEL = {
        "information": "warning",
        "warning": "warning",
        "caution": "warning",
        "attention": "warning",
        "disruption": "disrupted",
        "disturbed": "disrupted",
        "disturbance": "disrupted",
        "significant": "disrupted",
        "major": "disrupted",
        "critical": "closed",
        "blocking": "closed",
        "very_important": "closed",
        "no_service": "closed",
    }

    PRIM_EFFECT_LEVEL = {
        "SIGNIFICANT_DELAYS": "disrupted",
        "DELAYED": "warning",
        "REDUCED_SERVICE": "disrupted",
        "SHUTTLE_SERVICE": "disrupted",
        "NO_SERVICE": "closed",
        "OTHER_EFFECT": "warning",
    }

    def normalise(self, traffic_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Return a normalised representation of line statuses."""
        raw_line_reports = traffic_payload.get("data", {}).get("line_reports", [])
        community_groups = traffic_payload.get("result", {})

        status_by_line: Dict[str, LineStatus] = {}

        # PRIM data takes precedence
        for report in raw_line_reports or []:
            code = self._normalise_line_code(report.get("line", {}).get("code"))
            if not code:
                continue

            level, message = self._resolve_prim_severity(report)

            status_by_line[code] = {
                "line_code": code,
                "level": level,
                "message": message,
                "source": "prim",
                "details": {
                    "line": report.get("line"),
                    "status": report.get("status"),
                    "disruption": report.get("disruption"),
                },
            }

        # Community fallback data
        for group in community_groups.values():
            if not isinstance(group, list):
                continue

            for entry in group:
                code = self._normalise_line_code(entry.get("line"))
                if not code:
                    continue

                level, message = self._resolve_community(entry)

                existing = status_by_line.get(code)
                if existing and existing["source"] == "prim":
                    continue  # PRIM data wins

                should_replace = (
                    not existing
                    or self.LEVEL_PRIORITY[level] >= self.LEVEL_PRIORITY[existing["level"]]
                )

                if should_replace:
                    status_by_line[code] = {
                        "line_code": code,
                        "level": level,
                        "message": message,
                        "source": "community",
                        "details": entry,
                    }

        # Fill remaining lines as unknown
        source = (traffic_payload.get("source") or "").lower()
        default_level = (
            "normal"
            if traffic_payload.get("status") == "ok"
            and source in {"prim_api", "ratp_site", "community_api"}
            else "unknown"
        )
        default_message = (
            "No disruptions reported"
            if default_level == "normal"
            else "Live status unavailable"
        )

        normalised_lines: List[LineStatus] = []
        for code, info in sorted(status_by_line.items(), key=lambda item: item[0]):
            normalised_lines.append(info)

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": traffic_payload.get("source"),
            "status": traffic_payload.get("status"),
            "timestamp": traffic_payload.get("timestamp"),
            "lines": normalised_lines,
            "default": {
                "level": default_level,
                "message": default_message,
            },
        }

    def _normalise_line_code(self, code: Optional[str]) -> Optional[str]:
        if not code:
            return None
        return str(code).strip().upper()

    def _resolve_prim_severity(self, report: Dict[str, Any]) -> (str, Optional[str]):
        level = "normal"
        messages: List[str] = []

        status = report.get("status") or {}
        disruption = report.get("disruption") or {}

        for field in ("message", "short_message", "description"):
            value = status.get(field)
            if value:
                messages.append(value)

        if disruption.get("description"):
            messages.append(disruption["description"])

        impacts = report.get("impacts") or []
        for impact in impacts:
            if impact.get("description"):
                messages.append(impact["description"])
            severity = impact.get("severity")
            if severity:
                level = self._pick_higher_level(
                    level, self.PRIM_SEVERITY_LEVEL.get(severity.lower(), "disrupted")
                )

        severity = disruption.get("severity")
        if severity:
            level = self._pick_higher_level(
                level, self.PRIM_SEVERITY_LEVEL.get(severity.lower(), "disrupted")
            )

        severity = status.get("severity")
        if severity:
            level = self._pick_higher_level(
                level, self.PRIM_SEVERITY_LEVEL.get(severity.lower(), "warning")
            )

        effect = status.get("effect")
        if effect:
            level = self._pick_higher_level(
                level, self.PRIM_EFFECT_LEVEL.get(effect, "warning")
            )

        message = " ".join(messages).strip() or None
        return level, message

    def _resolve_community(self, entry: Dict[str, Any]) -> (str, Optional[str]):
        slug = (entry.get("slug") or "").lower()
        level = self.COMMUNITY_SLUG_LEVEL.get(slug)

        if not level:
            if "normal" in slug:
                level = "normal"
            elif "ferme" in slug:
                level = "closed"
            elif "ralent" in slug:
                level = "warning"
            elif "perturb" in slug:
                level = "disrupted"
            else:
                level = "unknown"

        message = entry.get("message") or entry.get("title")
        return level, message

    def _pick_higher_level(self, current: str, candidate: str) -> str:
        if self.LEVEL_PRIORITY.get(candidate, 0) > self.LEVEL_PRIORITY.get(current, 0):
            return candidate
        return current
