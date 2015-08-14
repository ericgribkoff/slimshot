DROP TABLE IF EXISTS R;
DROP TABLE IF EXISTS S;
DROP TABLE IF EXISTS TD;

CREATE TABLE R (
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

CREATE TABLE TD (
    id  serial,
    v0   integer,
    p   double precision
);

INSERT INTO R (v0, p) VALUES
(1, 0.950000),
(2, 0.500000),
(3, 0.300000)
;

INSERT INTO S (v0, v1, p) VALUES
(1, 1, 0.500000),
(1, 2, 0.600000),
(2, 1, 0),
(2, 2, 0.900000),
(2, 3, 1.000000),
(3, 1, 0.300000),
(3, 3, 0.900000)
;

INSERT INTO TD (v0, p) VALUES
(1, 1),
(2, 1),
(3, 0)
;

