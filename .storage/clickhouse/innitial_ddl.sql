SET allow_experimental_geo_types = 1;

DROP TABLE IF EXISTS trips;

CREATE TABLE IF NOT EXISTS trips (
    region String,
    origin_coord Point,
    destination_coord Point,
    date_time Datetime,
    datasource String
) ENGINE = MergeTree()
ORDER BY (region, datasource, date_time)
;


