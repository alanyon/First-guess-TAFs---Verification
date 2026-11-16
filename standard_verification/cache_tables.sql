CREATE TABLE IF NOT EXISTS taf_data
(issue_date    DATE,
 issue_time    INTEGER,
 issue_station TEXT,
 issue_origin  TEXT,
 start_date    DATE,
 start_time    INTEGER,
 end_date      DATE,
 end_time      INTEGER,
 station_id    TEXT,
 issue_status  TEXT,
 taf           TEXT,
PRIMARY KEY
(issue_date,
 issue_time,
 issue_station,
 issue_origin,
 start_date,
 start_time,
 end_date,
 end_time,
 station_id,
 issue_status)
ON CONFLICT REPLACE);

CREATE INDEX IF NOT EXISTS taf_data_start_date_idx
ON taf_data(start_date);

CREATE INDEX IF NOT EXISTS taf_data_station_start_idx
ON taf_data(station_id, start_date);

CREATE TABLE IF NOT EXISTS taf_decoded_data
(issue_date    DATE,
 issue_time    INTEGER,
 issue_station TEXT,
 issue_origin  TEXT,
 start_date    DATE,
 start_time    INTEGER,
 end_date      DATE,
 end_time      INTEGER,
 station_id    TEXT,
 issue_status  TEXT,
 change_type   TEXT,
 parameter     TEXT,
 value         REAL,
PRIMARY KEY
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
 parameter)
ON CONFLICT REPLACE);

CREATE INDEX IF NOT EXISTS taf_decoded_start_date_idx
ON taf_decoded_data(start_date);

CREATE INDEX IF NOT EXISTS taf_decoded_station_start_idx
ON taf_decoded_data(station_id, start_date);

CREATE TABLE IF NOT EXISTS processed_sources
(source TEXT PRIMARY KEY,
 size INTEGER NOT NULL,
 mtime_ns INTEGER NOT NULL);