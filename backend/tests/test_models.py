"""Tests for database models."""

import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models.line import Line
from backend.models.station import Station, LineStation
from backend.models.traffic import TrafficEvent


@pytest.mark.asyncio
async def test_create_line(test_db: AsyncSession):
    """Test creating a line model."""
    line = Line(
        line_code="1",
        line_name="La Défense - Château de Vincennes",
        transport_type="metro",
        color="#FFCD00"
    )

    test_db.add(line)
    await test_db.commit()
    await test_db.refresh(line)

    assert line.id is not None
    assert line.line_code == "1"
    assert line.created_at is not None


@pytest.mark.asyncio
async def test_create_station(test_db: AsyncSession):
    """Test creating a station model."""
    station = Station(
        station_code="chatelet",
        station_name="Châtelet",
        latitude=48.8584,
        longitude=2.3470,
        city="Paris"
    )

    test_db.add(station)
    await test_db.commit()
    await test_db.refresh(station)

    assert station.id is not None
    assert station.station_code == "chatelet"


@pytest.mark.asyncio
async def test_line_station_relationship(test_db: AsyncSession):
    """Test the many-to-many relationship between lines and stations."""
    # Create line
    line = Line(
        line_code="1",
        line_name="Test Line",
        transport_type="metro"
    )
    test_db.add(line)

    # Create station
    station = Station(
        station_code="test_station",
        station_name="Test Station",
        latitude=48.8566,
        longitude=2.3522
    )
    test_db.add(station)

    await test_db.commit()
    await test_db.refresh(line)
    await test_db.refresh(station)

    # Create association
    line_station = LineStation(
        line_id=line.id,
        station_id=station.id,
        position=1
    )
    test_db.add(line_station)
    await test_db.commit()

    # Query the relationship
    result = await test_db.execute(
        select(LineStation).where(LineStation.line_id == line.id)
    )
    ls = result.scalar_one()

    assert ls.line_id == line.id
    assert ls.station_id == station.id
    assert ls.position == 1


@pytest.mark.asyncio
async def test_create_traffic_event(test_db: AsyncSession):
    """Test creating a traffic event."""
    # Create a line first
    line = Line(
        line_code="1",
        line_name="Test Line",
        transport_type="metro"
    )
    test_db.add(line)
    await test_db.commit()
    await test_db.refresh(line)

    # Create traffic event
    event = TrafficEvent(
        line_id=line.id,
        event_type="incident",
        severity="high",
        title="Service Interruption",
        description="Train stopped between stations",
        start_time=datetime.now(),
        is_active=True
    )

    test_db.add(event)
    await test_db.commit()
    await test_db.refresh(event)

    assert event.id is not None
    assert event.line_id == line.id
    assert event.is_active is True


@pytest.mark.asyncio
async def test_line_unique_constraint(test_db: AsyncSession):
    """Test that line codes must be unique."""
    line1 = Line(
        line_code="1",
        line_name="Line 1",
        transport_type="metro"
    )
    test_db.add(line1)
    await test_db.commit()

    # Try to create duplicate
    line2 = Line(
        line_code="1",
        line_name="Another Line 1",
        transport_type="metro"
    )
    test_db.add(line2)

    with pytest.raises(Exception):  # Should raise IntegrityError
        await test_db.commit()


@pytest.mark.asyncio
async def test_station_unique_constraint(test_db: AsyncSession):
    """Test that station codes must be unique."""
    station1 = Station(
        station_code="chatelet",
        station_name="Châtelet"
    )
    test_db.add(station1)
    await test_db.commit()

    station2 = Station(
        station_code="chatelet",
        station_name="Another Châtelet"
    )
    test_db.add(station2)

    with pytest.raises(Exception):  # Should raise IntegrityError
        await test_db.commit()


@pytest.mark.asyncio
async def test_cascade_delete_line_stations(test_db: AsyncSession):
    """Test that deleting a line cascades to line_stations."""
    line = Line(line_code="1", line_name="Test", transport_type="metro")
    station = Station(station_code="s1", station_name="Station 1")

    test_db.add(line)
    test_db.add(station)
    await test_db.commit()
    await test_db.refresh(line)
    await test_db.refresh(station)

    line_station = LineStation(line_id=line.id, station_id=station.id, position=1)
    test_db.add(line_station)
    await test_db.commit()

    # Delete the line
    await test_db.delete(line)
    await test_db.commit()

    # LineStation should also be deleted
    result = await test_db.execute(
        select(LineStation).where(LineStation.line_id == line.id)
    )
    assert result.scalar_one_or_none() is None
