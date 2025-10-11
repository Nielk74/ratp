"""Unit tests for line snapshot helpers."""

from backend.services.scrapers.line_snapshot import (
    LineSnapshotService,
    StationJob,
    StationSnapshot,
    TrainEstimate,
)


def test_populate_station_departures_from_train_estimates():
    service = LineSnapshotService()

    job_a = StationJob(
        network="metro",
        line="1",
        line_id="IDFM:C0001",
        name="Station A",
        slug="station-a",
        order=0,
        direction="B",
        stop_id="STOP:A",
    )
    job_b = StationJob(
        network="metro",
        line="1",
        line_id="IDFM:C0001",
        name="Station B",
        slug="station-b",
        order=1,
        direction="B",
        stop_id="STOP:B",
    )

    snapshot_a = StationSnapshot(job=job_a, departures=[], metadata={}, direction_index=0)
    snapshot_b = StationSnapshot(job=job_b, departures=[], metadata={}, direction_index=1)

    sequences = {"A": [], "B": [snapshot_a, snapshot_b]}

    trains = {
        "B": [
            TrainEstimate(
                direction="B",
                from_station="Station A",
                to_station="Station B",
                eta_from=1,
                eta_to=1,
                progress=0.5,
                absolute_progress=0.6,
                confidence="high",
                status="approaching",
            )
        ]
    }

    service._populate_station_departures(sequences, trains)

    assert snapshot_a.departures, "Expected departures to be populated for Station A"
    assert snapshot_b.departures, "Expected departures to be populated for Station B"

    assert snapshot_a.departures[0]["status"] == "Departing"
    assert snapshot_b.departures[0]["status"] == "Arriving"
    assert "Station A → Station B" in snapshot_a.departures[0]["raw_text"]
