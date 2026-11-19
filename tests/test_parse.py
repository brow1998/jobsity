from datetime import datetime

import pytest

from trips.parse import Rejected, parse_point, read_events, to_event, trip_id

ROW = {
    "region": "Prague",
    "origin_coord": "POINT (14.4973794438195 50.00136875782316)",
    "destination_coord": "POINT (14.43109483523328 50.04052930943246)",
    "date_time": "2018-05-28 09:03:40",
    "datasource": "funny_car",
}


def test_parses_wkt_points_as_lon_lat():
    assert parse_point("POINT (14.5 50.0)") == (14.5, 50.0)
    assert parse_point("POINT(-7.1 -45)") == (-7.1, -45.0)


@pytest.mark.parametrize("text", ["", "POINT (1)", "LINESTRING (1 2, 3 4)", "POINT (200 10)", "POINT (10 95)"])
def test_rejects_anything_else(text):
    with pytest.raises(ValueError):
        parse_point(text)


def test_the_same_trip_always_gets_the_same_id():
    a = to_event(ROW, "a.csv", 2)
    b = to_event(dict(ROW), "b.csv", 99)  # same trip, re-sent in another file
    assert a["trip_id"] == b["trip_id"]
    assert len(a["trip_id"]) == 32


def test_a_different_trip_gets_a_different_id():
    other = to_event({**ROW, "datasource": "baba_car"}, "a.csv", 2)
    assert other["trip_id"] != to_event(ROW, "a.csv", 2)["trip_id"]


def test_trip_id_is_stable_across_releases():
    # Changing this hash would break deduplication against data already in ClickHouse.
    at = datetime(2018, 5, 28, 9, 3, 40)
    assert trip_id("Prague", (14.5, 50.0), (14.4, 50.1), at, "x") == "97f186c287e47651d4ec42b6cc10b336"


def test_every_bad_line_is_rejected_with_its_line_number(tmp_path):
    path = tmp_path / "trips.csv"
    path.write_text(
        "region,origin_coord,destination_coord,date_time,datasource\n"
        "Prague,POINT (14.5 50.0),POINT (14.4 50.1),2018-05-28 09:03:40,funny_car\n"
        "Prague,POINT (14.5 50.0),nowhere,2018-05-28 09:03:40,funny_car\n"
        "Turin,POINT (7.6 45.0),POINT (7.7 45.1),yesterday,baba_car\n"
        ",POINT (7.6 45.0),POINT (7.7 45.1),2018-05-21 02:54:04,baba_car\n"
    )
    items = list(read_events(str(path)))
    assert [i["source_line"] for i in items if isinstance(i, dict)] == [2]
    assert [(r.source_line, r.reason.split(":")[0]) for r in items if isinstance(r, Rejected)] == [
        (3, "not a WKT point"),
        (4, "bad date_time"),
        (5, "missing"),
    ]


def test_a_file_with_the_wrong_header_is_refused(tmp_path):
    path = tmp_path / "trips.csv"
    path.write_text("a,b,c\n1,2,3\n")
    with pytest.raises(ValueError, match="expected header"):
        list(read_events(str(path)))


def test_the_sample_file_is_clean():
    items = list(read_events("data/trips.csv"))
    assert len(items) == 100
    assert not [i for i in items if isinstance(i, Rejected)]
