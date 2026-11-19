-- Average trips per day (over days with trips) for each week and region.
CREATE VIEW IF NOT EXISTS weekly_average_by_region AS
SELECT
    toMonday(day)          AS week_start,
    region,
    round(avg(daily_trips), 2)   AS avg_daily_trips,
    sum(daily_trips)             AS trips
FROM
(
    SELECT toDate(date_time) AS day, region, count() AS daily_trips
    FROM trips FINAL
    GROUP BY day, region
)
GROUP BY week_start, region;

-- Same, for trips starting inside a bounding box.
--   SELECT * FROM weekly_average_in_box(min_lon=14.3, min_lat=49.9, max_lon=14.6, max_lat=50.2)
CREATE VIEW IF NOT EXISTS weekly_average_in_box AS
SELECT
    toMonday(day)          AS week_start,
    round(avg(daily_trips), 2)   AS avg_daily_trips,
    sum(daily_trips)             AS trips
FROM
(
    SELECT toDate(date_time) AS day, count() AS daily_trips
    FROM trips FINAL
    WHERE origin_lon BETWEEN {min_lon:Float64} AND {max_lon:Float64}
      AND origin_lat BETWEEN {min_lat:Float64} AND {max_lat:Float64}
    GROUP BY day
)
GROUP BY week_start;

-- Trips grouped by similar origin, destination (about 1 km cells) and hour of day.
CREATE VIEW IF NOT EXISTS trip_groups AS
SELECT
    region,
    round(origin_lat, 2)       AS origin_lat_cell,
    round(origin_lon, 2)       AS origin_lon_cell,
    round(destination_lat, 2)  AS destination_lat_cell,
    round(destination_lon, 2)  AS destination_lon_cell,
    toHour(date_time)          AS hour_of_day,
    count()                    AS trips
FROM trips FINAL
GROUP BY region, origin_lat_cell, origin_lon_cell, destination_lat_cell, destination_lon_cell, hour_of_day;
