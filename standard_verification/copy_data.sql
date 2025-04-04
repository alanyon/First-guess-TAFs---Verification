INSERT INTO TAF_DATA
(issue_date,
 issue_time,
 issue_station,
 issue_origin,
 start_date,
 start_time,
 end_date,
 end_time,
 station_id,
 issue_status,
 taf)
SELECT CASE SUBSTR(issue_date, 4, 3) 
            WHEN 'Jan' THEN DATETIME('20' || SUBSTR(issue_date, 8, 2) || '-01-' || SUBSTR(issue_date, 1, 2))
            WHEN 'Feb' THEN DATETIME('20' || SUBSTR(issue_date, 8, 2) || '-02-' || SUBSTR(issue_date, 1, 2))
            WHEN 'Mar' THEN DATETIME('20' || SUBSTR(issue_date, 8, 2) || '-03-' || SUBSTR(issue_date, 1, 2))
            WHEN 'Apr' THEN DATETIME('20' || SUBSTR(issue_date, 8, 2) || '-04-' || SUBSTR(issue_date, 1, 2))
            WHEN 'May' THEN DATETIME('20' || SUBSTR(issue_date, 8, 2) || '-05-' || SUBSTR(issue_date, 1, 2))
            WHEN 'Jun' THEN DATETIME('20' || SUBSTR(issue_date, 8, 2) || '-06-' || SUBSTR(issue_date, 1, 2))
            WHEN 'Jul' THEN DATETIME('20' || SUBSTR(issue_date, 8, 2) || '-07-' || SUBSTR(issue_date, 1, 2))
            WHEN 'Aug' THEN DATETIME('20' || SUBSTR(issue_date, 8, 2) || '-08-' || SUBSTR(issue_date, 1, 2))
            WHEN 'Sep' THEN DATETIME('20' || SUBSTR(issue_date, 8, 2) || '-09-' || SUBSTR(issue_date, 1, 2))
            WHEN 'Oct' THEN DATETIME('20' || SUBSTR(issue_date, 8, 2) || '-10-' || SUBSTR(issue_date, 1, 2))
            WHEN 'Nov' THEN DATETIME('20' || SUBSTR(issue_date, 8, 2) || '-11-' || SUBSTR(issue_date, 1, 2))
            WHEN 'Dec' THEN DATETIME('20' || SUBSTR(issue_date, 8, 2) || '-12-' || SUBSTR(issue_date, 1, 2))
            ELSE '' END,
       CAST(issue_time AS INTEGER),
       TRIM(issue_station),
       TRIM(issue_origin),
       CASE SUBSTR(start_date, 4, 3) 
            WHEN 'Jan' THEN DATETIME('20' || SUBSTR(start_date, 8, 2) || '-01-' || SUBSTR(start_date, 1, 2))
            WHEN 'Feb' THEN DATETIME('20' || SUBSTR(start_date, 8, 2) || '-02-' || SUBSTR(start_date, 1, 2))
            WHEN 'Mar' THEN DATETIME('20' || SUBSTR(start_date, 8, 2) || '-03-' || SUBSTR(start_date, 1, 2))
            WHEN 'Apr' THEN DATETIME('20' || SUBSTR(start_date, 8, 2) || '-04-' || SUBSTR(start_date, 1, 2))
            WHEN 'May' THEN DATETIME('20' || SUBSTR(start_date, 8, 2) || '-05-' || SUBSTR(start_date, 1, 2))
            WHEN 'Jun' THEN DATETIME('20' || SUBSTR(start_date, 8, 2) || '-06-' || SUBSTR(start_date, 1, 2))
            WHEN 'Jul' THEN DATETIME('20' || SUBSTR(start_date, 8, 2) || '-07-' || SUBSTR(start_date, 1, 2))
            WHEN 'Aug' THEN DATETIME('20' || SUBSTR(start_date, 8, 2) || '-08-' || SUBSTR(start_date, 1, 2))
            WHEN 'Sep' THEN DATETIME('20' || SUBSTR(start_date, 8, 2) || '-09-' || SUBSTR(start_date, 1, 2))
            WHEN 'Oct' THEN DATETIME('20' || SUBSTR(start_date, 8, 2) || '-10-' || SUBSTR(start_date, 1, 2))
            WHEN 'Nov' THEN DATETIME('20' || SUBSTR(start_date, 8, 2) || '-11-' || SUBSTR(start_date, 1, 2))
            WHEN 'Dec' THEN DATETIME('20' || SUBSTR(start_date, 8, 2) || '-12-' || SUBSTR(start_date, 1, 2))
            ELSE '' END,
       CAST(start_time AS INTEGER),
       CASE SUBSTR(end_date, 4, 3) 
            WHEN 'Jan' THEN DATETIME('20' || SUBSTR(end_date, 8, 2) || '-01-' || SUBSTR(end_date, 1, 2))
            WHEN 'Feb' THEN DATETIME('20' || SUBSTR(end_date, 8, 2) || '-02-' || SUBSTR(end_date, 1, 2))
            WHEN 'Mar' THEN DATETIME('20' || SUBSTR(end_date, 8, 2) || '-03-' || SUBSTR(end_date, 1, 2))
            WHEN 'Apr' THEN DATETIME('20' || SUBSTR(end_date, 8, 2) || '-04-' || SUBSTR(end_date, 1, 2))
            WHEN 'May' THEN DATETIME('20' || SUBSTR(end_date, 8, 2) || '-05-' || SUBSTR(end_date, 1, 2))
            WHEN 'Jun' THEN DATETIME('20' || SUBSTR(end_date, 8, 2) || '-06-' || SUBSTR(end_date, 1, 2))
            WHEN 'Jul' THEN DATETIME('20' || SUBSTR(end_date, 8, 2) || '-07-' || SUBSTR(end_date, 1, 2))
            WHEN 'Aug' THEN DATETIME('20' || SUBSTR(end_date, 8, 2) || '-08-' || SUBSTR(end_date, 1, 2))
            WHEN 'Sep' THEN DATETIME('20' || SUBSTR(end_date, 8, 2) || '-09-' || SUBSTR(end_date, 1, 2))
            WHEN 'Oct' THEN DATETIME('20' || SUBSTR(end_date, 8, 2) || '-10-' || SUBSTR(end_date, 1, 2))
            WHEN 'Nov' THEN DATETIME('20' || SUBSTR(end_date, 8, 2) || '-11-' || SUBSTR(end_date, 1, 2))
            WHEN 'Dec' THEN DATETIME('20' || SUBSTR(end_date, 8, 2) || '-12-' || SUBSTR(end_date, 1, 2))
            ELSE '' END,
       CAST(end_time AS INTEGER),
       TRIM(station_id),
       TRIM(issue_status),
       TRIM(taf)
FROM taf_load;

INSERT INTO TAF_DECODED_DATA
(issue_date,
 issue_time,
 issue_station,
 issue_origin,
 start_date,
 start_time,
 end_date,
 end_time,
 station_id,
 issue_status,
 change_type,
 parameter,
 value)
SELECT CASE SUBSTR(issue_date, 4, 3) 
            WHEN 'Jan' THEN DATETIME('20' || SUBSTR(issue_date, 8, 2) || '-01-' || SUBSTR(issue_date, 1, 2))
            WHEN 'Feb' THEN DATETIME('20' || SUBSTR(issue_date, 8, 2) || '-02-' || SUBSTR(issue_date, 1, 2))
            WHEN 'Mar' THEN DATETIME('20' || SUBSTR(issue_date, 8, 2) || '-03-' || SUBSTR(issue_date, 1, 2))
            WHEN 'Apr' THEN DATETIME('20' || SUBSTR(issue_date, 8, 2) || '-04-' || SUBSTR(issue_date, 1, 2))
            WHEN 'May' THEN DATETIME('20' || SUBSTR(issue_date, 8, 2) || '-05-' || SUBSTR(issue_date, 1, 2))
            WHEN 'Jun' THEN DATETIME('20' || SUBSTR(issue_date, 8, 2) || '-06-' || SUBSTR(issue_date, 1, 2))
            WHEN 'Jul' THEN DATETIME('20' || SUBSTR(issue_date, 8, 2) || '-07-' || SUBSTR(issue_date, 1, 2))
            WHEN 'Aug' THEN DATETIME('20' || SUBSTR(issue_date, 8, 2) || '-08-' || SUBSTR(issue_date, 1, 2))
            WHEN 'Sep' THEN DATETIME('20' || SUBSTR(issue_date, 8, 2) || '-09-' || SUBSTR(issue_date, 1, 2))
            WHEN 'Oct' THEN DATETIME('20' || SUBSTR(issue_date, 8, 2) || '-10-' || SUBSTR(issue_date, 1, 2))
            WHEN 'Nov' THEN DATETIME('20' || SUBSTR(issue_date, 8, 2) || '-11-' || SUBSTR(issue_date, 1, 2))
            WHEN 'Dec' THEN DATETIME('20' || SUBSTR(issue_date, 8, 2) || '-12-' || SUBSTR(issue_date, 1, 2))
            ELSE '' END,
       CAST(issue_time AS INTEGER),
       TRIM(issue_station),
       TRIM(issue_origin),
       CASE SUBSTR(start_date, 4, 3) 
            WHEN 'Jan' THEN DATETIME('20' || SUBSTR(start_date, 8, 2) || '-01-' || SUBSTR(start_date, 1, 2))
            WHEN 'Feb' THEN DATETIME('20' || SUBSTR(start_date, 8, 2) || '-02-' || SUBSTR(start_date, 1, 2))
            WHEN 'Mar' THEN DATETIME('20' || SUBSTR(start_date, 8, 2) || '-03-' || SUBSTR(start_date, 1, 2))
            WHEN 'Apr' THEN DATETIME('20' || SUBSTR(start_date, 8, 2) || '-04-' || SUBSTR(start_date, 1, 2))
            WHEN 'May' THEN DATETIME('20' || SUBSTR(start_date, 8, 2) || '-05-' || SUBSTR(start_date, 1, 2))
            WHEN 'Jun' THEN DATETIME('20' || SUBSTR(start_date, 8, 2) || '-06-' || SUBSTR(start_date, 1, 2))
            WHEN 'Jul' THEN DATETIME('20' || SUBSTR(start_date, 8, 2) || '-07-' || SUBSTR(start_date, 1, 2))
            WHEN 'Aug' THEN DATETIME('20' || SUBSTR(start_date, 8, 2) || '-08-' || SUBSTR(start_date, 1, 2))
            WHEN 'Sep' THEN DATETIME('20' || SUBSTR(start_date, 8, 2) || '-09-' || SUBSTR(start_date, 1, 2))
            WHEN 'Oct' THEN DATETIME('20' || SUBSTR(start_date, 8, 2) || '-10-' || SUBSTR(start_date, 1, 2))
            WHEN 'Nov' THEN DATETIME('20' || SUBSTR(start_date, 8, 2) || '-11-' || SUBSTR(start_date, 1, 2))
            WHEN 'Dec' THEN DATETIME('20' || SUBSTR(start_date, 8, 2) || '-12-' || SUBSTR(start_date, 1, 2))
            ELSE '' END,
       CAST(start_time AS INTEGER),
       CASE SUBSTR(end_date, 4, 3) 
            WHEN 'Jan' THEN DATETIME('20' || SUBSTR(end_date, 8, 2) || '-01-' || SUBSTR(end_date, 1, 2))
            WHEN 'Feb' THEN DATETIME('20' || SUBSTR(end_date, 8, 2) || '-02-' || SUBSTR(end_date, 1, 2))
            WHEN 'Mar' THEN DATETIME('20' || SUBSTR(end_date, 8, 2) || '-03-' || SUBSTR(end_date, 1, 2))
            WHEN 'Apr' THEN DATETIME('20' || SUBSTR(end_date, 8, 2) || '-04-' || SUBSTR(end_date, 1, 2))
            WHEN 'May' THEN DATETIME('20' || SUBSTR(end_date, 8, 2) || '-05-' || SUBSTR(end_date, 1, 2))
            WHEN 'Jun' THEN DATETIME('20' || SUBSTR(end_date, 8, 2) || '-06-' || SUBSTR(end_date, 1, 2))
            WHEN 'Jul' THEN DATETIME('20' || SUBSTR(end_date, 8, 2) || '-07-' || SUBSTR(end_date, 1, 2))
            WHEN 'Aug' THEN DATETIME('20' || SUBSTR(end_date, 8, 2) || '-08-' || SUBSTR(end_date, 1, 2))
            WHEN 'Sep' THEN DATETIME('20' || SUBSTR(end_date, 8, 2) || '-09-' || SUBSTR(end_date, 1, 2))
            WHEN 'Oct' THEN DATETIME('20' || SUBSTR(end_date, 8, 2) || '-10-' || SUBSTR(end_date, 1, 2))
            WHEN 'Nov' THEN DATETIME('20' || SUBSTR(end_date, 8, 2) || '-11-' || SUBSTR(end_date, 1, 2))
            WHEN 'Dec' THEN DATETIME('20' || SUBSTR(end_date, 8, 2) || '-12-' || SUBSTR(end_date, 1, 2))
            ELSE '' END,
       CAST(end_time AS INTEGER),
       TRIM(station_id),
       TRIM(issue_status),
       TRIM(change_type),
       TRIM(parameter),
       CAST(value AS REAL)
FROM taf_decoded_load;

.exit
