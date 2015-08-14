import psycopg2
import pytest

from safesample.algorithm import algorithm, query_exp
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
  dnf = safesample.query_parser.parse("R[1](),S[1,2]()")
  assert exactProb(dnf) == 0.57

def test_q2():
  conn = psycopg2.connect(dbname="sampling")
  conn.autocommit = True
  cur = conn.cursor()  
  cur.execute(open("test/test_data/data1.sql", "r").read())
  dnf = safesample.query_parser.parse("R[1](),S[1,*](y),T(y)")
  assert exactProb(dnf) == 0.36955

def test_q3():
  conn = psycopg2.connect(dbname="sampling")
  conn.autocommit = True
  cur = conn.cursor()  
  cur.execute(open("test/test_data/data1.sql", "r").read())
  dnf = safesample.query_parser.parse("R[-1](x),S[*,2](x)")
  assert exactProb(dnf) == 0.45

def test_q4():
  conn = psycopg2.connect(dbname="sampling")
  conn.autocommit = True
  cur = conn.cursor()  
  cur.execute(open("test/test_data/data2.sql", "r").read())
  dnf = safesample.query_parser.parse("R[1](),R[2]()")
  assert exactProb(dnf) == 0.285

def test_q5():
  conn = psycopg2.connect(dbname="sampling")
  conn.autocommit = True
  cur = conn.cursor()  
  cur.execute(open("test/test_data/data2.sql", "r").read())
  dnf = safesample.query_parser.parse("R[1](),~R[2]()")
  assert exactProb(dnf) == 0.665

def test_q6():
  conn = psycopg2.connect(dbname="sampling")
  conn.autocommit = True
  cur = conn.cursor()  
  cur.execute(open("test/test_data/data2.sql", "r").read())
  dnf = safesample.query_parser.parse("S[1,*](x),S[2,*](x)")
  assert exactProb(dnf) == 0.609

def test_q7():
  conn = psycopg2.connect(dbname="sampling")
  conn.autocommit = True
  cur = conn.cursor()  
  cur.execute(open("test/test_data/data2.sql", "r").read())
  dnf = safesample.query_parser.parse("~S[1,*](y),S[2,*](y)")
  assert exactProb(dnf) == 0.456

def test_q8():
  conn = psycopg2.connect(dbname="sampling")
  conn.autocommit = True
  cur = conn.cursor()  
  cur.execute(open("test/test_data/data2.sql", "r").read())
  dnf = safesample.query_parser.parse("~S[1,*](y) v S[2,*](y)")
  assert exactProb(dnf) == 0.979

# This will be a good query to test minimization on
# Also, computes the wrong probability currently - wrong probability fixed,
# issue was an incomplete table (missing tuples not always treated as probability 0)
def test_q9():
  conn = psycopg2.connect(dbname="sampling")
  conn.autocommit = True
  cur = conn.cursor()  
  cur.execute(open("test/test_data/constants2.sql", "r").read())
  dnf = safesample.query_parser.parse("RD*[2]() v P1[-2,2](x),RD*[-2](x),S[-2,2](x),~RD*[2]() v P1[-2,-2](x,y),RD*[-2](x),S[-2,-2](x,y),~RD*[-2](y)")
  assert exactProb(dnf) == 0.36

# TODO(ericgribkoff) This tests currently passed, which might be a problem
# This query is unsafe, because my current computation of the adjacency list incorrectly treats S[*,-1]
# and S[-1,*] as independent - need to think about whether this type of query should ever be processed
#def test_q10():
#  dnf = safesample.query_parser.parse("R(x),S[*,-1](x,y) v S[-1,*](u,v),T(v)")
#  with pytest.raises(safesample.algorithm.UnsafeException) as excinfo:
#    exactProb(dnf)
#  assert excinfo.value.message == 'FAIL'


def test_q11():
  conn = psycopg2.connect(dbname="sampling")
  conn.autocommit = True
  cur = conn.cursor()  
  cur.execute(open("test/test_data/constants2.sql", "r").read())
  dnf1 = safesample.query_parser.parse("R(x),S(x,y) v ~S(x,y),T(y) v R(x),T(y)")
  dnf2 = safesample.query_parser.parse("R(x),S(x,y) v ~S(x,y),T(y)")
  assert exactProb(dnf1) == exactProb(dnf2)
  assert exactProb(dnf1) == 0.95464

def test_containment():
    R1 = safesample.query_parser.parseRelation("R","[1]","()")
    R2 = safesample.query_parser.parseRelation("R","[2]","()")
    com1 = safesample.algorithm.query_exp.Component([R1])
    com2 = safesample.algorithm.query_exp.Component([R2])
    assert com2.containedIn(com1) == False

def test_containment2():
    R1 = safesample.query_parser.parseRelation("R","[1]","()")
    R2 = safesample.query_parser.parseRelation("R","[1]","()")
    com1 = safesample.algorithm.query_exp.Component([R1])
    com2 = safesample.algorithm.query_exp.Component([R2])
    assert com2.containedIn(com1) == True

