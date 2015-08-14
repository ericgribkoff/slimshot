-- command:  asymmetricRulesWebKB.py 2 -1 -1 -1 1.1 1.1 1.1

DROP TABLE IF EXISTS P1;
DROP TABLE IF EXISTS P2;
DROP TABLE IF EXISTS P3;
DROP TABLE IF EXISTS Has;
DROP TABLE IF EXISTS Class;
DROP TABLE IF EXISTS Link;
DROP TABLE IF EXISTS A;

CREATE TABLE A (
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

INSERT INTO A (v0) VALUES
(1),
(2);
INSERT INTO P1 (v0, v1, v2, p) VALUES
(1, 1, 1, 0.670951),
(1, 1, 2, 0.678022),
(1, 2, 1, 0.742360),
(1, 2, 2, 0.804196),
(2, 1, 1, 0.690258),
(2, 1, 2, 0.791731),
(2, 2, 1, 0.779920),
(2, 2, 2, 0.771444)
;
INSERT INTO P2 (v0, v1, v2, p) VALUES
(1, 1, 1, 0.748533),
(1, 1, 2, 0.769832),
(1, 2, 1, 0.821704),
(1, 2, 2, 0.692392),
(2, 1, 1, 0.784641),
(2, 1, 2, 0.854516),
(2, 2, 1, 0.805700),
(2, 2, 2, 0.772533)
;
INSERT INTO P3 (v0, v1, v2, v3, p) VALUES
(1, 1, 1, 1, 0.785698),
(1, 1, 1, 2, 0.712648),
(1, 1, 2, 1, 0.783924),
(1, 1, 2, 2, 0.669050),
(1, 2, 1, 1, 0.680531),
(1, 2, 1, 2, 0.681501),
(1, 2, 2, 1, 0.752243),
(1, 2, 2, 2, 0.744741),
(2, 1, 1, 1, 0.797396),
(2, 1, 1, 2, 0.785965),
(2, 1, 2, 1, 0.755958),
(2, 1, 2, 2, 0.732221),
(2, 2, 1, 1, 0.716132),
(2, 2, 1, 2, 0.705328),
(2, 2, 2, 1, 0.722678),
(2, 2, 2, 2, 0.751291)
;
INSERT INTO Has (v0, v1, p) VALUES
(1, 1, 0.268941),
(1, 2, 0.268941),
(2, 1, 0.268941),
(2, 2, 0.268941)
;
INSERT INTO Class (v0, v1, p) VALUES
(1, 1, 0.268941),
(1, 2, 0.268941),
(2, 1, 0.268941),
(2, 2, 0.268941)
;
INSERT INTO Link (v0, v1, p) VALUES
(1, 1, 0.268941),
(1, 2, 0.268941),
(2, 1, 0.268941),
(2, 2, 0.268941)
;
