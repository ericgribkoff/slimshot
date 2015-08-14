DROP TABLE IF EXISTS RD;
DROP TABLE IF EXISTS S;
DROP TABLE IF EXISTS P1;

CREATE TABLE RD (
    id  serial,
    v0   integer,
    p   double precision
);

CREATE TABLE S (
    id  serial,
    v0   integer,
    v1   integer,
    p   double precision
);

CREATE TABLE P1 (
    id  serial,
    v0   integer,
    v1   integer,
    p   double precision
);

INSERT INTO RD (v0, p) VALUES
(1, 1),
(2, 0),
(3, 1)
;

INSERT INTO S (v0, v1, p) VALUES
(1, 1, 0.500000),
(1, 2, 0.600000),
(1, 3, 0),
(2, 1, 0),
(2, 2, 0.900000),
(2, 3, 1.000000),
(3, 1, 0.300000),
(3, 2, 0),
(3, 3, 0.900000)
;

INSERT INTO P1 (v0, v1, p) VALUES
(1, 1, 0.600000),
(1, 2, 0.600000),
(2, 1, 0.600000),
(2, 2, 0.600000),
(2, 3, 0.600000),
(3, 1, 0.600000),
(3, 2, 0.600000),
(3, 3, 0.600000)
;

