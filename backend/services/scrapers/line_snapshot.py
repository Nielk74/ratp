"""Utilities to collect scraper data across an entire line."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pytz

from .ratp_playwright import RatpPlaywrightScraper, ScraperResult
from ..station_data import STATION_FALLBACKS


PARIS_TZ = pytz.timezone("Europe/Paris")


@dataclass
class StationJob:
    """Represents a scraping job for a station + direction."""

    network: str
    line: str
    name: str
    slug: str
    order: int
    direction: str


@dataclass
class StationSnapshot:
    """Scraped information for a given station/direction."""

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
    """Rudimentary inferred train position between two stations."""

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
    """Aggregated scraping information for a whole line."""

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


def _parse_wait_time(value: Optional[str], now: datetime) -> Optional[int]:
    """Convert wait strings like '3 mn' or '23:40' into minutes."""

    if not value:
        return None
    text = value.strip().lower()
    if not text:
        return None

    if "à quai" in text or "a quai" in text:
        return 0
    if "approche" in text:
        return 1
    if "retard" in text or "indisponible" in text:
        return None

    digits = ""
    for char in text:
        if char.isdigit():
            digits += char
        elif digits:
            break
    if digits and ("mn" in text or "min" in text):
        return int(digits)

    if ":" in text:
        try:
            hours, minutes = [int(part) for part in text.split(":", 1)]
            arrival = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
            if arrival < now - timedelta(minutes=5):
                arrival += timedelta(days=1)
            delta = arrival - now
            return max(int(delta.total_seconds() // 60), 0)
        except Exception:  # pylint: disable=broad-except
            return None

    return None


class LineSnapshotService:
    """Collects and caches aggregated scraper data for lines."""

    def __init__(self) -> None:
        self._cache: Dict[Tuple[str, str], _CacheEntry] = {}
        self._lock = Lock()

    def get_snapshot(
        self,
        network: str,
        line: str,
        *,
        refresh: bool = False,
        max_workers: int = 1,
    ) -> Dict[str, Any]:
        key = _normalize_key(network, line)
        now = datetime.now(UTC)

        if not refresh:
            with self._lock:
                entry = self._cache.get(key)
                if entry and (now - entry.timestamp) <= timedelta(seconds=60):
                    return entry.snapshot.to_dict()

        snapshot = self._collect_snapshot(network, line, max_workers=max_workers)
        with self._lock:
            self._cache[key] = _CacheEntry(snapshot=snapshot, timestamp=now)
        return snapshot.to_dict()

    def _collect_snapshot(self, network: str, line: str, *, max_workers: int) -> LineSnapshot:
        jobs = self._build_jobs(network, line)
        if not jobs:
            raise ValueError(f"No station fallback data for {network} line {line}")

        scraper = RatpPlaywrightScraper(headless=True, challenge_delay=8.0, wait_timeout=45.0)
        station_snapshots: List[StationSnapshot] = []
        errors: List[str] = []

        pause_seconds = max(0.5, 2.0 / max(1, max_workers))

        for job in jobs:
            try:
                result = scraper.fetch_station_board(
                    line=job.line,
                    station=job.slug,
                    direction=job.direction,
                    network=job.network,
                    language="fr",
                )
                station_snapshots.append(self._build_station_snapshot(job, result))
            except Exception as exc:  # pylint: disable=broad-except
                error_message = f"{job.slug} ({job.direction}): {exc}"
                errors.append(error_message)
                station_snapshots.append(
                    StationSnapshot(
                        job=job,
                        departures=[],
                        metadata={"error": str(exc)},
                        error=str(exc),
                    )
                )
            finally:
                time.sleep(pause_seconds)

        direction_sequences = self._assign_direction_indices(station_snapshots)
        trains = self._infer_trains(direction_sequences)

        latest_timestamp = max(
            [
                snap.metadata.get("timestamp", 0)
                for snap in station_snapshots
                if snap.metadata.get("timestamp")
            ],
            default=datetime.now(UTC).timestamp(),
        )

        scraped_at = datetime.fromtimestamp(latest_timestamp, tz=UTC)

        return LineSnapshot(
            scraped_at=scraped_at,
            network=network,
            line=line,
            stations=station_snapshots,
            trains=trains,
            errors=errors,
        )

    def _build_station_snapshot(self, job: StationJob, result: ScraperResult) -> StationSnapshot:
        departures = [departure.to_dict() for departure in result.departures]
        metadata = dict(result.metadata)
        metadata.setdefault("cloudflare_blocked", False)
        metadata.setdefault("form_flow", False)
        metadata.setdefault("timestamp", metadata.get("timestamp", datetime.now(UTC).timestamp()))
        return StationSnapshot(job=job, departures=departures, metadata=metadata)

    @staticmethod
    def _build_jobs(network: str, line: str) -> List[StationJob]:
        normalized_network = network.lower()
        normalized_line = line.upper()
        fallbacks = STATION_FALLBACKS.get(normalized_network, {}).get(normalized_line)
        if not fallbacks:
            return []

        jobs: List[StationJob] = []
        for index, station in enumerate(fallbacks):
            name = station.get("name") or station.get("slug")
            if not name:
                continue
            slug = station.get("slug") or name
            for direction in ("A", "B"):
                jobs.append(
                    StationJob(
                        network=normalized_network,
                        line=normalized_line,
                        name=name,
                        slug=slug,
                        order=index,
                        direction=direction,
                    )
                )
        return jobs

    def _assign_direction_indices(
        self,
        snapshots: List[StationSnapshot],
    ) -> Dict[str, List[StationSnapshot]]:
        sequences: Dict[str, List[StationSnapshot]] = {"A": [], "B": []}
        for snapshot in snapshots:
            if snapshot.job.direction in sequences:
                sequences[snapshot.job.direction].append(snapshot)

        for direction, sequence in sequences.items():
            reverse = direction == "A"
            sequence.sort(key=lambda snap: snap.job.order, reverse=reverse)
            for idx, snapshot in enumerate(sequence):
                snapshot.direction_index = idx
        return sequences

    def _infer_trains(
        self,
        sequences: Dict[str, List[StationSnapshot]],
    ) -> Dict[str, List[TrainEstimate]]:
        trains: Dict[str, List[TrainEstimate]] = {direction: [] for direction in sequences.keys()}
        now = datetime.now(PARIS_TZ)

        for direction, sequence in sequences.items():
            if len(sequence) < 2:
                continue

            for idx in range(len(sequence) - 1):
                current = sequence[idx]
                nxt = sequence[idx + 1]
                eta_from = self._first_numeric_wait(current.departures, now)
                eta_to = self._first_numeric_wait(nxt.departures, now)

                if eta_from is None or eta_to is None:
                    continue
                if eta_from > 30 or eta_to > 30:
                    continue
                denominator = eta_from + eta_to
                if denominator <= 0:
                    continue

                progress = eta_from / denominator
                absolute_progress = (idx + progress) / (len(sequence) - 1)

                max_eta = max(eta_from, eta_to)
                if max_eta <= 5:
                    confidence = "high"
                elif max_eta <= 10:
                    confidence = "medium"
                else:
                    confidence = "low"

                trains[direction].append(
                    TrainEstimate(
                        direction=direction,
                        from_station=current.job.name,
                        to_station=nxt.job.name,
                        eta_from=eta_from,
                        eta_to=eta_to,
                        progress=round(progress, 3),
                        absolute_progress=round(absolute_progress, 3),
                        confidence=confidence,
                    )
                )

            trains[direction].sort(
                key=lambda train: train.eta_from if train.eta_from is not None else 999
            )

        return trains

    @staticmethod
    def _first_numeric_wait(departures: Iterable[Dict[str, Any]], now: datetime) -> Optional[int]:
        for departure in departures:
            value = departure.get("waiting_time") or departure.get("wait") or departure.get("message")
            parsed = _parse_wait_time(value, now)
            if parsed is not None:
                return parsed
        return None


line_snapshot_service = LineSnapshotService()
