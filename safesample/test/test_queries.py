import psycopg2
import pytest
from safesample.algorithm import algorithm
import safesample.query_parser

def exactProb(queryDNF):
    plan = algorithm.getSafeQueryPlan(queryDNF)
    querySQL = plan.generateSQL_DNF()
    exactProb = safesample.query_parser.executeSQL(querySQL)
    return exactProb

def test_q1():
  conn = psycopg2.connect(dbname="sampling")
  conn.autocommit = True
  cur = conn.cursor()  
  cur.execute(open("test/test_data/data1.sql", "r").read())
  dnf = safesample.query_parser.parse("R(x)")
  assert exactProb(dnf) == 0.975

def test_q2():
  conn = psycopg2.connect(dbname="sampling")
  conn.autocommit = True
  cur = conn.cursor()  
  cur.execute(open("test/test_data/data1.sql", "r").read())
  dnf = safesample.query_parser.parse("R(x),S(x,y)")
  print dnf
  assert exactProb(dnf) == 0.8716

def test_IE():
  conn = psycopg2.connect(dbname="sampling")
  conn.autocommit = True
  cur = conn.cursor()  
  cur.execute(open("test/test_data/data1.sql", "r").read())
  dnf = safesample.query_parser.parse("R(x1),S(x1,y1) v S(x2,y2),T(y2) v R(x3),T(y3)")
  assert exactProb(dnf) == 0.959765

def test_h0():
  dnf = safesample.query_parser.parse("R(x),S(x,y),T(y)")
  with pytest.raises(algorithm.UnsafeException) as excinfo:
    exactProb(dnf)
  assert excinfo.value.message == 'FAIL'

def test_h1():
  dnf = safesample.query_parser.parse("R(x),S(x,y) v S(x,y),T(y)")
  with pytest.raises(algorithm.UnsafeException) as excinfo:
    exactProb(dnf)
  assert excinfo.value.message == 'FAIL'

def test_needsRanking():
  dnf = safesample.query_parser.parse("S(x,y),S(y,x)")
  with pytest.raises(algorithm.UnsafeException) as excinfo:
    exactProb(dnf)
  assert excinfo.value.message == 'FAIL'

def test_det():
  conn = psycopg2.connect(dbname="sampling")
  conn.autocommit = True
  cur = conn.cursor()  
  cur.execute(open("test/test_data/deterministic.sql", "r").read())
  dnf = safesample.query_parser.parse("R(x),S(x,y),TD*(y)")
  assert exactProb(dnf) == 0.87988

def test_constants2():
  conn = psycopg2.connect(dbname="sampling")
  conn.autocommit = True
  cur = conn.cursor()  
  cur.execute(open("test/test_data/constants.sql", "r").read())
  dnf = safesample.query_parser.parse("RD*[1]() v P1[-1,1](x),RD*[-1](x),S[-1,1](x),~RD*[1]() v P1[-1,-1](x,y),RD*[-1](x),S[-1,-1](x,y),~RD*[-1](y)")
  assert exactProb(dnf) == 1

def test_constants3():
  dnf = safesample.query_parser.parse("P1(x,y),Smokes(x),Friends(x,y),~Smokes(y)")
  with pytest.raises(algorithm.UnsafeException) as excinfo:
    exactProb(dnf)
  assert excinfo.value.message == 'FAIL'

def test_constants4():
  conn = psycopg2.connect(dbname="sampling")
  conn.autocommit = True
  cur = conn.cursor()  
  cur.execute(open("test/test_data/constants.sql", "r").read())
  dnf = safesample.query_parser.parse("P1(x,y),RD*(x),S(x,y),~RD*(y)")
  assert exactProb(dnf) == 0.36

def test_constants5():
  dnf = safesample.query_parser.parse("P1*(x,y),RD(x),S*(x,y),~RD(y)")
  with pytest.raises(algorithm.UnsafeException) as excinfo:
    exactProb(dnf)
  assert excinfo.value.message == 'FAIL'

