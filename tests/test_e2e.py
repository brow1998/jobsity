"""End-to-end against the real stack. Run with: docker compose up -d --wait kafka clickhouse && uv run pytest -m e2e"""

import pytest

from trips import pipeline
from trips.parse import read_events

pytestmark = pytest.mark.e2e

SAMPLE = "data/trips.csv"


def count(client, sql):
    return client.query(sql).result_rows[0][0]


@pytest.fixture(scope="module")
def loaded():
    client = pipeline.clickhouse()
    client.command("TRUNCATE TABLE trips")
    # Send the same file twice: at-least-once delivery must still end with each trip once.
    for _ in range(2):
        report = pipeline.ingest([SAMPLE])
        assert report.failed == 0 and report.delivered == 100
    pipeline.sink(idle_seconds=5)
    return client


def test_every_trip_lands_exactly_once(loaded):
    assert count(loaded, "SELECT count() FROM trips FINAL") == 100
    assert count(loaded, "SELECT uniqExact(trip_id) FROM trips") == 100


def test_every_row_has_a_receipt(loaded):
    lines = {e["source_line"] for e in read_events(SAMPLE)}
    rows = loaded.query("SELECT source_file, source_line, kafka_offset FROM trips FINAL").result_rows
    assert {r[1] for r in rows} == lines
    assert all(r[0] == SAMPLE for r in rows)


def test_weekly_averages_add_up(loaded):
    assert count(loaded, "SELECT sum(trips) FROM weekly_average_by_region") == 100
    prague = "SELECT sum(trips) FROM weekly_average_in_box(min_lon=14.2, min_lat=49.9, max_lon=14.7, max_lat=50.2)"
    assert count(loaded, prague) == 34


def test_trip_groups_cover_every_trip(loaded):
    assert count(loaded, "SELECT sum(trips) FROM trip_groups") == 100
