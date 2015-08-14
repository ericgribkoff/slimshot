-- from Oblivious Bounds on the Probability of Boolean Functions 2014, Gatterbauer and Suciu
create or replace function ior_sfunc (double precision, double precision) returns double precision as
'select $1 * (1.0 - $2)'
language SQL;

create or replace function ior_finalfunc (double precision) returns double precision as
'select 1.0 - $1'
language SQL;

drop aggregate if exists ior (double precision);
create aggregate ior (double precision) (
  sfunc = ior_sfunc,
  stype = double precision,
  finalfunc = ior_finalfunc,
  initcond = '1.0');
