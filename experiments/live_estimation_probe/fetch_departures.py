"""CLI helper to fetch live departure estimates for a single RATP station."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Tuple

from bs4 import BeautifulSoup
import cloudscraper
from requests.cookies import RequestsCookieJar

BASE_HORAIRES_URL = "https://www.ratp.fr/horaires"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch live departure estimates from ratp.fr for a given station/direction.",
    )
    parser.add_argument("--network", default="metro", help="Network slug as used by ratp.fr (metro, rer, tram, ...).")
    parser.add_argument("--line", required=True, help="Line code (e.g. 1, A, T3a).")
    parser.add_argument("--station", required=True, help="Station name exactly as displayed on ratp.fr.")
    parser.add_argument("--direction", default="A", choices=("A", "B", "R"), help="Direction code (A/B/R).")
    parser.add_argument("--json", action="store_true", help="Print the raw JSON payload instead of a human summary.")
    parser.add_argument("--debug", action="store_true", help="Dump scraper metadata for troubleshooting.")
    parser.add_argument("--with-vmtr", action="store_true", help="Augment the output with VMTR websocket vehicle positions.")
    return parser


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value or "")
    stripped = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    stripped = stripped.lower()
    stripped = stripped.replace("œ", "oe").replace("æ", "ae")
    stripped = stripped.replace("’", "'").replace("–", "-").replace("—", "-")
    stripped = re.sub(r"[^a-z0-9]+", "-", stripped)
    return stripped.strip("-")


def _station_slug(name: str) -> str:
    return _normalize(name)


def _station_match(lhs: str, rhs: str) -> bool:
    return _normalize(lhs) == _normalize(rhs)


def _build_session():
    session = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "linux", "desktop": True},
        delay=10,
    )
    session.headers.update(
        {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://www.ratp.fr",
            "X-Requested-With": "XMLHttpRequest",
        }
    )
    return session


def _request_json(session, url: str, *, referer: str, params: Dict[str, Any] | None = None):
    response = session.get(url, params=params, headers={"Referer": referer}, timeout=15)
    if response.status_code == 403:
        raise RuntimeError("Forbidden while calling %s" % url)
    response.raise_for_status()
    try:
        return response.json()
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to decode JSON from {url}: {exc}") from exc


def _get_line_id(session: requests.Session, network: str, line: str, *, referer: str) -> str:
    payload = _request_json(
        session,
        f"https://www.ratp.fr/horaires/api/getLineId/{network}/{line}",
        referer=referer,
    )
    if isinstance(payload, str):
        return payload.strip()
    raise RuntimeError(f"Unexpected line id payload: {payload!r}")


def _get_stop_points(session: requests.Session, network: str, line: str, *, referer: str) -> List[Dict[str, Any]]:
    payload = _request_json(
        session,
        f"https://www.ratp.fr/horaires/api/getStopPoints/{network}/{line}",
        referer=referer,
    )
    if not isinstance(payload, list):
        raise RuntimeError(f"Unexpected stop points payload: {payload!r}")
    return payload


def _select_stop_point(stop_points: Iterable[Dict[str, Any]], station: str) -> Dict[str, Any]:
    for entry in stop_points:
        if _station_match(entry.get("name", ""), station):
            return entry
    raise RuntimeError(f"Station {station!r} not found in stop points")


def _fetch_board_html(
    session,
    network: str,
    line_id: str,
    stop_place_id: str,
    *,
    station: str,
    direction: str,
    referer: str,
) -> str:
    url = f"https://www.ratp.fr/horaires/blocs-horaires-next-passages/{network}/{line_id}/{stop_place_id}"
    response = session.get(
        url,
        params={"stopPlaceName": station, "type": "now", "sens": direction},
        headers={"Referer": referer},
        timeout=20,
    )
    if response.status_code == 403:
        raise RuntimeError("Forbidden while calling %s" % url)
    response.raise_for_status()
    return json.loads(response.text)


def _parse_departures(html_fragment: str, direction: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html_fragment, "html.parser")
    blocks = soup.select(".ixxi-horaire-result-timetable")
    block_index = 0 if direction.upper() == "A" else 1
    if block_index >= len(blocks):
        block_index = 0
    block = blocks[block_index] if blocks else None

    departures: List[Dict[str, Any]] = []
    if not block:
        return departures

    table = block.select_one("table.timetable")
    if not table:
        return departures

    for row in table.select("tr.body-metro"):
        destination = row.select_one(".terminus-wrap")
        waiting_time = row.select_one(".heure-wrap")
        status = row.select_one(".type-horaire-td span")
        if not destination or not waiting_time:
            continue
        departures.append(
            {
                "destination": destination.get_text(strip=True),
                "waiting_time": waiting_time.get_text(strip=True),
                "status": status.get_text(strip=True) if status else None,
            }
        )
    return departures


def _format_departures(departures: List[Dict[str, Any]]) -> str:
    if not departures:
        return "  no departures returned"

    lines = []
    for entry in departures:
        wait = entry.get("waiting_time") or "?"
        destination = entry.get("destination") or "?"
        status = entry.get("status")
        line = f"  - {wait:<10} → {destination}"
        if status:
            line = f"{line} ({status})"
        lines.append(line)
    return "\n".join(lines)


def _print_summary(result_dict: Dict[str, Any]) -> None:
    metadata = result_dict.get("metadata") or {}
    departures = result_dict.get("departures") or []
    vehicles = result_dict.get("vmtr") or []

    timestamp = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
    heading = f"[{timestamp}] Live departures for {metadata.get('network', '?')} {metadata.get('line', '?')} @ {metadata.get('station', '?')} direction {metadata.get('direction', '?')}"
    print(heading)
    print("-" * len(heading))
    print(_format_departures(departures))
    if metadata:
        print()
        print(
            "  line_id={line_id} | stop_place_id={stop_place_id} | source={source}".format(
                line_id=metadata.get("line_id"),
                stop_place_id=metadata.get("stop_place_id"),
                source=metadata.get("source"),
            )
        )
    if vehicles:
        sample = vehicles[0]
        print(
            "  vmtr vehicles: {count} (sample: {vehicle_id} prev={prev} next={next} progress={progress:.0%})".format(
                count=len(vehicles),
                vehicle_id=sample.get("vehicle_id"),
                prev=sample.get("previous_stop_ref"),
                next=sample.get("next_stop_ref"),
                progress=sample.get("progress") or 0.0,
            )
        )


def main(argv: List[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    network = args.network.lower()
    line = args.line.upper()
    station = args.station
    direction = args.direction.upper()

    try:
        session = _build_session()
        referer = f"{BASE_HORAIRES_URL}/{network}/{line}"
        if station:
            station_slug = _station_slug(station)
            if station_slug:
                referer = f"{referer}/{station_slug}"

        line_id = _get_line_id(session, network, line, referer=referer)
        stop_points = _get_stop_points(session, network, line, referer=referer)
        stop_point = _select_stop_point(stop_points, station)
        stop_place_id = stop_point.get("stop_place_id")

        html_fragment = _fetch_board_html(
            session,
            network,
            line_id,
            stop_place_id,
            station=station,
            direction=direction,
            referer=referer,
        )
        departures = _parse_departures(html_fragment, direction)
    except Exception as exc:  # pylint: disable=broad-except
        parser.error(f"scrape failed: {exc}")
        return 1

    result_dict: Dict[str, Any] = {
        "metadata": {
            "network": network,
            "line": line,
            "station": station,
            "direction": direction,
            "line_id": line_id,
            "stop_place_id": stop_place_id,
            "source": "ratp.fr/horaires",
        },
        "departures": departures,
    }

    if args.with_vmtr:
        try:
            from .vmtr_client import VmtrClient

            vmtr_client = VmtrClient()
            vehicles = vmtr_client.fetch_direction(line_id, direction)
            result_dict["vmtr"] = [vehicle.to_dict() for vehicle in vehicles]
        except Exception as exc:  # pylint: disable=broad-except
            result_dict.setdefault("errors", []).append({"vmtr": str(exc)})

    if args.json:
        json.dump(result_dict, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        _print_summary(result_dict)

    if args.debug:
        sys.stdout.write("\n--- metadata ---\n")
        json.dump(result_dict.get("metadata"), sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
