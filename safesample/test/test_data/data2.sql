DROP TABLE IF EXISTS R;
DROP TABLE IF EXISTS S;
DROP TABLE IF EXISTS T;

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

CREATE TABLE T (
    id  serial,
    v0   integer,
    p   double precision
);

INSERT INTO R (v0, p) VALUES
(1, 0.950000),
(2, 0.300000)
;

INSERT INTO S (v0, v1, p) VALUES
(1, 1, 0.500000),
(1, 2, 0.600000),
(2, 1, 0.300000),
(2, 2, 0.900000)
;

INSERT INTO T (v0, p) VALUES
(1, 0.7),
(2, 0.1)
;

