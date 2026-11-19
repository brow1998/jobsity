# trips

[![ci](https://github.com/brow1998/jobsity/actions/workflows/ci.yml/badge.svg)](https://github.com/brow1998/jobsity/actions/workflows/ci.yml)

On-demand ingestion of trip CSV files into ClickHouse, through Kafka. Each trip has a region,
origin and destination coordinates, a timestamp and the datasource that reported it.

```text
CSV files ──► trips ingest ──► Kafka topic "trips" ──► trips sink ──► ClickHouse
              validate rows     3 partitions,           batch insert,     ReplacingMergeTree
              content-hash ids  idempotent producer     commit offsets    + analytical views
                                                        after insert
```

## Quick start

Needs Docker. One command, from a clean checkout:

```bash
docker compose run --rm pipeline
```

That starts Kafka (KRaft, no ZooKeeper) and ClickHouse, sends `data/trips.csv` through the topic
and reports what happened:

```text
INFO ingest: 100 sent, 100 delivered, 0 failed, 0 rejected
INFO sink: 100 rows written to ClickHouse
```

Ingest your own files the same way (put them in `data/`):

```bash
docker compose run --rm pipeline trips run data/may.csv data/june.csv
```

Files need the header `region,origin_coord,destination_coord,date_time,datasource`, with
coordinates as WKT points (`POINT (14.49 50.00)`) and times as `YYYY-MM-DD HH:MM:SS`.

## Querying

ClickHouse is on <http://localhost:8123> (user `default`, no password). Open a client with
`docker compose exec clickhouse clickhouse-client`.

```sql
-- Average trips per day, by week and region
SELECT * FROM weekly_average_by_region ORDER BY week_start, region;

-- The same for any bounding box (here, Prague)
SELECT * FROM weekly_average_in_box(min_lon=14.2, min_lat=49.9, max_lon=14.7, max_lat=50.2);

-- Trips with similar origin and destination (about 1 km cells) and hour of day
SELECT * FROM trip_groups ORDER BY trips DESC LIMIT 10;
```

```text
┌─week_start─┬─region──┬─avg_daily_trips─┬─trips─┐
│ 2018-04-30 │ Hamburg │            1.25 │     5 │
│ 2018-04-30 │ Prague  │               2 │    10 │
│ 2018-04-30 │ Turin   │             1.6 │     8 │
└────────────┴─────────┴─────────────────┴───────┘
```

The two questions from the original brief are in [`clickhouse/bonus_queries.sql`](clickhouse/bonus_queries.sql).

## How it behaves

**Sending a file twice doesn't double the data.** Every trip gets an id hashed from its content.
`trips` is a `ReplacingMergeTree` ordered by that id, so repeats collapse; the views read with
`FINAL`, so they're right immediately. The end-to-end test sends the sample twice and expects each
trip exactly once.

**Nothing is acknowledged before it's stored.** The producer is idempotent and waits for every
broker ack. The sink commits Kafka offsets only after ClickHouse accepted the batch. A crash in
between means a redelivery, which the content id absorbs.

**Every row has a receipt.** Each trip in ClickHouse keeps the file and line it came from, plus
its Kafka partition and offset.

**Bad rows don't stop the file.** A malformed point, an unparseable time or a missing field is
reported with its file and line number; the rest of the file goes through. A file with the wrong
header is refused before anything is sent.

**You hear about progress without polling.** Delivery callbacks report as acks arrive, and each
command ends with a summary of what was sent, delivered, rejected and written.

## Scaling

The topic is partitioned, so sinks scale out by running more `trips sink` processes in the same
consumer group. Inserts are batched (up to 10,000 rows) and the table is partitioned by month and
sorted by region and time, which keeps the weekly and regional queries scanning only what they need.

## Tests

```bash
uv run pytest                                              # unit tests, no services needed
docker compose up -d --wait kafka clickhouse && uv run pytest -m e2e   # end to end
```

## Layout

```text
src/trips/parse.py      CSV rows → validated events with content ids and receipts
src/trips/pipeline.py   Kafka producer and ClickHouse sink
src/trips/cli.py        `trips run | ingest | sink`
clickhouse/             schema, views and the bonus queries
tests/                  unit tests and the end-to-end suite
```

## License

[MIT](LICENSE)
