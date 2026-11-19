-- One row per distinct trip. Replayed or re-sent trips share a trip_id and collapse on merge;
-- read with FINAL (the views below do) to see the deduplicated result immediately.
CREATE TABLE IF NOT EXISTS trips
(
    trip_id          FixedString(32),
    region           LowCardinality(String),
    origin_lon       Float64,
    origin_lat       Float64,
    destination_lon  Float64,
    destination_lat  Float64,
    date_time        DateTime,
    datasource       LowCardinality(String),
    source_file      String,
    source_line      UInt32,
    kafka_partition  UInt16,
    kafka_offset     UInt64,
    ingested_at      DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(ingested_at)
PARTITION BY toYYYYMM(date_time)
ORDER BY (region, date_time, trip_id);
