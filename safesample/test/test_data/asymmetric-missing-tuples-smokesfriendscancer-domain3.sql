-- n = 10, smokes = -1.4, friends = -4.6, cancer = -2.3, w(S,F => S) = 1.1, w(S=>C) = 1.5
-- command:  symmetricSmokesFriendsCancer.py 10 -1.4 -4.6 -2.3 1.1 1.5

DROP TABLE IF EXISTS P1;
DROP TABLE IF EXISTS P2;
DROP TABLE IF EXISTS Smokes;
DROP TABLE IF EXISTS Friends;
DROP TABLE IF EXISTS Cancer;
DROP TABLE IF EXISTS A;

CREATE TABLE A (
    v0   integer
);

CREATE TABLE P1 (
    id  serial,
    v0   integer,
    v1   integer,
    p   double precision
    --p   double precision
);

CREATE TABLE P2 (
    id  serial,
    v0   integer,
    p   double precision
    --p   double precision
);

CREATE TABLE Smokes (
    id  serial,
    v0   integer,
    p   double precision
    --p   double precision
);

CREATE TABLE Friends (
    id  serial,
    v0   integer,
    v1   integer,
    p   double precision
    --p   double precision
);

CREATE TABLE Cancer (
    id  serial,
    v0   integer,
    p   double precision
    --p   double precision
);

INSERT INTO A (v0) VALUES
(1),
(2),
(3)
;
INSERT INTO P1 (v0, v1, p) VALUES
(1, 1, 0.667129),
(1, 2, 0.667129),
(1, 3, 0.667129),
(2, 1, 0.667129),
(2, 2, 0.667129),
(2, 3, 0.667129),
(3, 1, 0.667129),
(3, 2, 0.667129),
(3, 3, 0.667129)
;
INSERT INTO P2 (v0, p) VALUES
(1, 0.776870),
(2, 0.776870),
(3, 0.776870)
;
INSERT INTO Smokes (v0, p) VALUES
(1, 0.3),
--(2, 0.0),
(3, 1.0)
;
INSERT INTO Friends (v0, v1, p) VALUES
(1, 1, 0.1),
(1, 2, 0.2),
(1, 3, 0.3),
(2, 1, 0.7),
--(2, 2, 0.8),
--(2, 3, 0.9),
(3, 1, 0.4)
--(3, 2, 0.5),
--(3, 3, 0.6)
;
INSERT INTO Cancer (v0, p) VALUES
(1, 0.3),
(2, 0.6),
(3, 0.9)
;
