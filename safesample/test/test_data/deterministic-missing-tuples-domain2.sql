-- n = 2, smokes = -1.4, friends = -4.6, cancer = -2.3, w(S,F => S) = 1.1, w(S=>C) = 1.5
-- command:  symmetricSmokesFriendsCancer.py 2 -1.4 -4.6 -2.3 1.1 1.5

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
    --p   double precision
    p   double precision
);

CREATE TABLE P2 (
    id  serial,
    v0   integer,
    --p   double precision
    p   double precision
);

CREATE TABLE Smokes (
    id  serial,
    v0   integer,
    --p   double precision
    p   double precision
);

CREATE TABLE Friends (
    id  serial,
    v0   integer,
    v1   integer,
    --p   double precision
    p   double precision
);

CREATE TABLE Cancer (
    id  serial,
    v0   integer,
    --p   double precision
    p   double precision
);

INSERT INTO A (v0) VALUES
(1),
(2);
INSERT INTO P1 (v0, v1, p) VALUES
(1, 1, 0.667129),
(1, 2, 0.667129),
(2, 1, 0.667129),
(2, 2, 0.667129)
;
INSERT INTO P2 (v0, p) VALUES
(1, 0.776870),
(2, 0.776870)
;
INSERT INTO Smokes (v0, p) VALUES
(2, 1)
;
INSERT INTO Friends (v0, v1, p) VALUES
(1, 1, 0.009952),
(1, 2, 0.009952),
(2, 1, 0.009952),
(2, 2, 0.009952)
;
INSERT INTO Cancer (v0, p) VALUES
(1, 0.091123),
(2, 0.091123)
;
