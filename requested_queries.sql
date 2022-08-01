-- ## 0
SELECT
    DATE_TRUNC('week', trip_day) AS start_of_week,
    region,
    CEIL(AVG(total)) AS weekly_average
    FROM (
        SELECT
            CAST(
                date_time AS DATE
            ) AS trip_day,
            region,
            count(1) AS total
        FROM
            trips
        GROUP BY
            CAST(
                date_time AS DATE
            ),
            region
    ) AS x
GROUP BY
    region,
    DATE_TRUNC('week', trip_day);

-- ## 1
SELECT
    datasource AS latest_datasource
FROM
    trips
WHERE
    region IN (
                SELECT
                    region
                FROM
                    trips
                GROUP BY
                    region
                ORDER BY
                    count(1) DESC
                LIMIT 2
    )
ORDER BY
    date_time DESC
LIMIT 1
;


-- ## 2 

SELECT
    DISTINCT region
FROM
    trips
WHERE
    datasource = 'cheap_mobile'
;