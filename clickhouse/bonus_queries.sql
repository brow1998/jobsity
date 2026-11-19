-- 1. Of the two regions with the most trips, which datasource appeared most recently?
SELECT datasource AS latest_datasource, region, date_time
FROM trips FINAL
WHERE region IN (
    SELECT region FROM trips FINAL GROUP BY region ORDER BY count() DESC, region LIMIT 2
)
ORDER BY date_time DESC
LIMIT 1;

-- 2. In which regions has the "cheap_mobile" datasource appeared?
SELECT DISTINCT region
FROM trips FINAL
WHERE datasource = 'cheap_mobile'
ORDER BY region;
