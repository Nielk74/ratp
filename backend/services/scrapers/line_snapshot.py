"""Line snapshot aggregation driven by VMTR websocket data only."""

from __future__ import annotations

import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Tuple

import requests

from ...config import settings
from .ratp_vmtr_socket import RatpVmtrSocketClient
from ..station_data import STATION_FALLBACKS


@dataclass
class StationJob:
    """Represents a station + direction to expose in the snapshot."""

    network: str
    line: str
    line_id: str
    name: str
    slug: str
    order: int
    direction: str
    stop_id: Optional[str]


@dataclass
class StationSnapshot:
    """Snapshot entry for a given station/direction."""

    job: StationJob
    departures: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    error: Optional[str] = None
    direction_index: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.job.name,
            "slug": self.job.slug,
            "order": self.job.order,
            "direction": self.job.direction,
            "direction_index": self.direction_index,
            "departures": self.departures,
            "metadata": self.metadata,
            "error": self.error,
        }


@dataclass
class TrainEstimate:
    """Derived train position along the line."""

    direction: str
    from_station: str
    to_station: str
    eta_from: Optional[int]
    eta_to: Optional[int]
    progress: float
    absolute_progress: float
    confidence: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LineSnapshot:
    """Aggregated snapshot for a transit line."""

    scraped_at: datetime
    network: str
    line: str
    stations: List[StationSnapshot]
    trains: Dict[str, List[TrainEstimate]]
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scraped_at": self.scraped_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "network": self.network,
            "line": self.line,
            "stations": [station.to_dict() for station in self.stations],
            "trains": {
                direction: [train.to_dict() for train in trains]
                for direction, trains in self.trains.items()
            },
            "errors": self.errors,
        }


@dataclass
class _CacheEntry:
    snapshot: LineSnapshot
    timestamp: datetime


def _normalize_key(network: str, line: str) -> Tuple[str, str]:
    return (network.lower(), line.upper())


def _normalize_name(value: str) -> str:
    return (
        value.replace("–", "-")
        .replace("—", "-")
        .replace("’", "'")
        .strip()
        .lower()
    )


def _slugify(value: str) -> str:
    normalized = _normalize_name(value)
    for token in (" ", "'", "(", ")", "/"):
        normalized = normalized.replace(token, "-")
    while "--" in normalized:
        normalized = normalized.replace("--", "-")
    return normalized.strip("-")


class IdfmReferenceClient:
    """Minimal helper around the IDFM open-data datasets."""

    BASE_URL = "https://data.iledefrance-mobilites.fr/api/explore/v2.1/catalog/datasets"

    _LINE_FILTERS = {
        "metro": {"transportmode": "metro", "operatorname": "RATP"},
        "rer": {"networkname": "RER"},
        "tram": {"transportmode": "tram", "operatorname": "RATP"},
        "transilien": {"networkname": "Transilien"},
    }

    def __init__(self) -> None:
        self._session = requests.Session()
        self._line_cache: Dict[tuple[str, str], Optional[str]] = {}
        self._stops_cache: Dict[str, Dict[str, Dict[str, str]]] = {}

    def get_line_id(self, network: str, line_code: str) -> Optional[str]:
        key = (network.lower(), line_code.upper())
        if key in self._line_cache:
            return self._line_cache[key]

        params = [f"shortname_line='{line_code.upper()}'"]
        filters = self._LINE_FILTERS.get(network.lower(), {})
        for field, value in filters.items():
            params.append(f"{field}='{value}'")

        where_clause = " AND ".join(params)
        response = self._session.get(
            f"{self.BASE_URL}/referentiel-des-lignes/records",
            params={"where": where_clause, "limit": 20},
            timeout=20,
        )
        response.raise_for_status()
        results = response.json().get("results", [])

        selected = self._select_line_candidate(network, results)
        if not selected:
            self._line_cache[key] = None
            return None

        line_id = selected.get("id_line")
        if not line_id:
            self._line_cache[key] = None
            return None

        value = line_id if line_id.startswith("IDFM:") else f"IDFM:{line_id}"
        self._line_cache[key] = value
        return value

    def get_stops_for_line(self, line_id: str) -> Dict[str, Dict[str, str]]:
        if line_id in self._stops_cache:
            return self._stops_cache[line_id]

        response = self._session.get(
            f"{self.BASE_URL}/arrets-lignes/records",
            params={"where": f'id="{line_id}"', "limit": 100},
            timeout=20,
        )
        response.raise_for_status()
        records = response.json().get("results", [])

        mapping: Dict[str, Dict[str, str]] = {}
        for record in records:
            stop_name = record.get("stop_name")
            if not stop_name:
                continue
            normalized = self._normalize(stop_name)
            mapping[normalized] = record
            slug = self._slugify(stop_name)
            mapping.setdefault(slug, record)

        self._stops_cache[line_id] = mapping
        return mapping

    def _select_line_candidate(self, network: str, results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not results:
            return None

        network_lower = network.lower()

        if network_lower in {"metro", "tram"}:
            filtered = [item for item in results if item.get("operatorname", "").lower() == "ratp"]
            if filtered:
                return filtered[0]
        elif network_lower in {"rer", "transilien"}:
            filtered = [item for item in results if item.get("networkname")]
            if filtered:
                return filtered[0]

        return results[0]

    @staticmethod
    def _normalize(value: str) -> str:
        decomposed = unicodedata.normalize("NFD", value)
        ascii_value = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
        return ascii_value.replace("–", "-").replace("—", "-").lower().strip()

    @staticmethod
    def _slugify(value: str) -> str:
        normalized = IdfmReferenceClient._normalize(value)
        for token in (" ", "'", "(", ")", ","):
            normalized = normalized.replace(token, "-")
        while "--" in normalized:
            normalized = normalized.replace("--", "-")
        return normalized.strip("-")


class LineSnapshotService:
    """Collects station information and VMTR vehicle positions for a line."""

    def __init__(self) -> None:
        self._cache: Dict[Tuple[str, str], _CacheEntry] = {}
        self._reference_client = IdfmReferenceClient()
        self._vmtr_client = (
            RatpVmtrSocketClient(
                base_url=settings.vmtr_socket_url,
                enabled=settings.vmtr_socket_enabled,
            )
            if settings.vmtr_socket_enabled
            else None
        )

    def get_snapshot(
        self,
        network: str,
        line: str,
        *,
        refresh: bool = False,
        station_limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        key = _normalize_key(network, line)
        now = datetime.now(UTC)

        use_cache = station_limit is None

        if use_cache and not refresh:
            entry = self._cache.get(key)
            if entry and (now - entry.timestamp).total_seconds() <= 60:
                return entry.snapshot.to_dict()

        snapshot = self._collect_snapshot(network, line, station_limit=station_limit)
        if use_cache:
            self._cache[key] = _CacheEntry(snapshot=snapshot, timestamp=now)
        return snapshot.to_dict()

    # Internal helpers -------------------------------------------------

    def _collect_snapshot(
        self,
        network: str,
        line: str,
        *,
        station_limit: Optional[int],
    ) -> LineSnapshot:
        normalized_network = network.lower()
        normalized_line = line.upper()

        line_id = self._reference_client.get_line_id(normalized_network, normalized_line)
        if not line_id:
            raise ValueError(f"Unable to resolve IDFM line id for {network} {line}")

        stop_lookup = self._reference_client.get_stops_for_line(line_id)
        jobs = self._build_jobs(normalized_network, normalized_line, line_id, stop_lookup, station_limit)
        if not jobs:
            raise ValueError(f"No station data available for {network} line {line}")

        station_snapshots = [self._build_station_snapshot(job) for job in jobs]
        sequences = self._assign_direction_indices(station_snapshots)

        vmtr_trains, vmtr_error = self._build_vmtr_trains(sequences, station_snapshots, line_id)
        errors: List[str] = []
        if vmtr_error:
            errors.append(vmtr_error)

        scraped_at = datetime.now(UTC)
        return LineSnapshot(
            scraped_at=scraped_at,
            network=normalized_network,
            line=normalized_line,
            stations=station_snapshots,
            trains=vmtr_trains,
            errors=errors,
        )

    def _build_jobs(
        self,
        network: str,
        line: str,
        line_id: str,
        stop_lookup: Dict[str, Dict[str, Any]],
        station_limit: Optional[int],
    ) -> List[StationJob]:
        fallbacks = STATION_FALLBACKS.get(network, {}).get(line)
        if not fallbacks:
            return []

        if station_limit is not None and station_limit > 0:
            fallbacks = fallbacks[:station_limit]

        jobs: List[StationJob] = []
        for index, station in enumerate(fallbacks):
            name = station.get("name") or station.get("slug")
            if not name:
                continue

            slug = station.get("slug") or _slugify(name)
            stop_info = self._match_stop(stop_lookup, name, slug)
            stop_id = stop_info.get("stop_id") if stop_info else None

            for direction in ("A", "B"):
                jobs.append(
                    StationJob(
                        network=network,
                        line=line,
                        line_id=line_id,
                        name=name,
                        slug=slug,
                        order=index,
                        direction=direction,
                        stop_id=stop_id,
                    )
                )

        return jobs

    def _build_station_snapshot(self, job: StationJob) -> StationSnapshot:
        timestamp = datetime.now(UTC).timestamp()
        vmtr_stop_ref = self._vmtr_stop_ref(job.stop_id) if job.stop_id else None

        metadata: Dict[str, Any] = {
            "network": job.network,
            "line": job.line,
            "line_id": job.line_id,
            "station": job.name,
            "direction": job.direction,
            "timestamp": timestamp,
        }
        if job.stop_id:
            metadata["stop_id"] = job.stop_id
        if vmtr_stop_ref:
            metadata["stop_place_ref"] = vmtr_stop_ref

        return StationSnapshot(
            job=job,
            departures=[],
            metadata=metadata,
        )

    @staticmethod
    def _assign_direction_indices(
        snapshots: List[StationSnapshot],
    ) -> Dict[str, List[StationSnapshot]]:
        sequences: Dict[str, List[StationSnapshot]] = {"A": [], "B": []}
        for snapshot in snapshots:
            direction = snapshot.job.direction.upper()
            if direction in sequences:
                sequences[direction].append(snapshot)

        for direction, sequence in sequences.items():
            reverse = direction == "A"
            sequence.sort(key=lambda snap: snap.job.order, reverse=reverse)
            for idx, snapshot in enumerate(sequence):
                snapshot.direction_index = idx

        return sequences

    def _build_vmtr_trains(
        self,
        sequences: Dict[str, List[StationSnapshot]],
        snapshots: List[StationSnapshot],
        line_id: str,
    ) -> Tuple[Dict[str, List[TrainEstimate]], Optional[str]]:
        trains: Dict[str, List[TrainEstimate]] = {direction: [] for direction in sequences.keys()}

        if not self._vmtr_client or not self._vmtr_client.enabled:
            return trains, "VMTR socket disabled"

        directions = [direction for direction, seq in sequences.items() if seq]
        if not directions:
            return trains, None

        stop_lookup: Dict[Tuple[str, str], StationSnapshot] = {}
        for snapshot in snapshots:
            stop_ref = snapshot.metadata.get("stop_place_ref")
            if stop_ref:
                stop_lookup[(snapshot.job.direction.upper(), str(stop_ref))] = snapshot

        try:
            vehicle_map = self._vmtr_client.fetch_positions(line_id, directions)
        except Exception as exc:  # pylint: disable=broad-except
            return trains, f"VMTR fetch failed: {exc}"

        for direction_key, vehicles in vehicle_map.items():
            normalized_direction = self._map_vmtr_direction(direction_key)
            sequence = sequences.get(normalized_direction)
            if not sequence:
                continue

            segment_divisor = max(len(sequence) - 1, 1)

            for vehicle in vehicles:
                direction_token = self._map_vmtr_direction(vehicle.direction)
                if direction_token != normalized_direction:
                    continue

                prev_snapshot = stop_lookup.get((normalized_direction, str(vehicle.previous_stop_ref)))
                next_snapshot = stop_lookup.get((normalized_direction, str(vehicle.next_stop_ref)))

                anchor = prev_snapshot or next_snapshot
                target = next_snapshot or prev_snapshot
                if not anchor or not target:
                    continue

                anchor_index = anchor.direction_index
                target_index = target.direction_index
                if anchor_index is None or target_index is None:
                    continue

                progress = vehicle.progress if vehicle.progress is not None else 0.0
                progress = max(0.0, min(progress, 1.0))

                if anchor_index == target_index:
                    segment_index = float(anchor_index)
                    segment_progress = 0.0
                else:
                    ascending = anchor_index < target_index
                    segment_index = float(min(anchor_index, target_index))
                    segment_progress = progress if ascending else 1.0 - progress

                absolute_progress = (segment_index + segment_progress) / segment_divisor
                absolute_progress = max(0.0, min(absolute_progress, 1.0))

                eta = self._estimate_eta(vehicle.status)
                confidence = self._status_to_confidence(vehicle.status)

                trains[normalized_direction].append(
                    TrainEstimate(
                        direction=normalized_direction,
                        from_station=anchor.job.name,
                        to_station=target.job.name,
                        eta_from=eta,
                        eta_to=eta,
                        progress=round(segment_progress, 3),
                        absolute_progress=round(absolute_progress, 3),
                        confidence=confidence,
                    )
                )

        for direction in trains:
            trains[direction].sort(key=lambda train: train.absolute_progress)

        return trains, None

    @staticmethod
    def _map_vmtr_direction(direction: str) -> str:
        token = (direction or "").upper()
        if token == "A":
            return "A"
        if token in {"B", "R"}:
            return "B"
        return token or "A"

    @staticmethod
    def _vmtr_stop_ref(stop_id: str) -> Optional[str]:
        if not stop_id:
            return None
        if stop_id.startswith("ART:"):
            return stop_id
        parts = stop_id.split(":")
        suffix = parts[-1]
        return f"ART:IDFM:{suffix}"

    @staticmethod
    def _estimate_eta(status: Optional[str]) -> Optional[int]:
        if not status:
            return None
        token = status.lower()
        if token == "atdock":
            return 0
        if token == "approaching":
            return 1
        if token == "transit":
            return 3
        return None

    @staticmethod
    def _status_to_confidence(status: Optional[str]) -> str:
        if not status:
            return "medium"
        token = status.lower()
        if token in {"atdock", "approaching"}:
            return "high"
        if token == "transit":
            return "medium"
        return "low"

    @staticmethod
    def _match_stop(stop_lookup: Dict[str, Dict[str, Any]], name: str, slug: str) -> Optional[Dict[str, Any]]:
        normalized_name = IdfmReferenceClient._normalize(name)
        normalized_slug = IdfmReferenceClient._slugify(slug)

        for key in (normalized_name, normalized_slug):
            if key in stop_lookup:
                return stop_lookup[key]

        for key, record in stop_lookup.items():
            if normalized_name and normalized_name in key:
                return record
            if normalized_slug and normalized_slug in key:
                return record
        return None


line_snapshot_service = LineSnapshotService()
