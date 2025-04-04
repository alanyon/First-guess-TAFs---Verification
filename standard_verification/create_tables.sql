DROP TABLE IF EXISTS TAF_LOAD;
DROP TABLE IF EXISTS TAF_DECODED_LOAD;
DROP TABLE IF EXISTS TAF_DATA;
DROP TABLE IF EXISTS TAF_DECODED_DATA;

CREATE TABLE taf_load
(issue_date    TEXT,
 issue_time    INTEGER,
 issue_station TEXT,
 issue_origin  TEXT,
 start_date    TEXT,
 start_time    INTEGER,
 end_date      TEXT,
 end_time      INTEGER,
 station_id    TEXT,
 issue_status  TEXT,
 taf           TEXT);

CREATE TABLE taf_decoded_load
(issue_date    TEXT,
 issue_time    INTEGER,
 issue_station TEXT,
 issue_origin  TEXT,
 start_date    TEXT,
 start_time    INTEGER,
 end_date      TEXT,
 end_time      INTEGER,
 station_id    TEXT,
 issue_status  TEXT,
 change_type   TEXT,
 parameter     TEXT,
 value         TEXT,
 dummy         REAL);

CREATE TABLE taf_data
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

CREATE TABLE taf_decoded_data
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
