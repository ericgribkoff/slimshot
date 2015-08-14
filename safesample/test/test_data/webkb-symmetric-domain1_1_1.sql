-- command:  asymmetricRulesWebKB.py 1 1 1 1 1 1 1.1 1.1 1.1 0

DROP TABLE IF EXISTS P1;
DROP TABLE IF EXISTS P2;
DROP TABLE IF EXISTS P3;
DROP TABLE IF EXISTS Has;
DROP TABLE IF EXISTS Class;
DROP TABLE IF EXISTS Link;
DROP TABLE IF EXISTS A_Pages;
DROP TABLE IF EXISTS A_Words;
DROP TABLE IF EXISTS A_Classes;

CREATE TABLE A_Pages (
    v0   integer
);

CREATE TABLE A_Words (
    v0   integer
);

CREATE TABLE A_Classes (
    v0   integer
);

CREATE TABLE P1 (
    id  serial,
    v0   integer,
    v1   integer,
    v2   integer,
    --p   double precision
    p   double precision
);

CREATE TABLE P2 (
    id  serial,
    v0   integer,
    v1   integer,
    v2   integer,
    --p   double precision
    p   double precision
);

CREATE TABLE P3 (
    id  serial,
    v0   integer,
    v1   integer,
    v2   integer,
    v3   integer,
    --p   double precision
    p   double precision
);

CREATE TABLE Has (
    id  serial,
    v0   integer,
    v1   integer,
    --p   double precision
    p   double precision
);

CREATE TABLE Class (
    id  serial,
    v0   integer,
    v1   integer,
    --p   double precision
    p   double precision
);

CREATE TABLE Link (
    id  serial,
    v0   integer,
    v1   integer,
    --p   double precision
    p   double precision
);

INSERT INTO A_Pages (v0) VALUES
(1);
INSERT INTO A_Words (v0) VALUES
(1);
INSERT INTO A_Classes (v0) VALUES
(1);
INSERT INTO P1 (v0, v1, v2, p) VALUES
(1, 1, 1, 0.667129)
;
INSERT INTO P2 (v0, v1, v2, p) VALUES
(1, 1, 1, 0.667129)
;
INSERT INTO Has (v0, v1, p) VALUES
(1, 1, 0.731059)
;
INSERT INTO Class (v0, v1, p) VALUES
(1, 1, 0.731059)
;
INSERT INTO Link (v0, v1, p) VALUES
(1, 1, 1.000000)
;
INSERT INTO P3 (v0, v1, v2, v3, p) VALUES
(1, 1, 1, 1, 0.667129)
;
