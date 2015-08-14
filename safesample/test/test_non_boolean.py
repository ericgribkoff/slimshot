import psycopg2
import pytest
import random

from safesample.algorithm import algorithm
import safesample.query_parser

def exactProb(queryDNF):
    conn = psycopg2.connect(dbname="sampling_test")
    conn.autocommit = True
    cur = conn.cursor()
    plan = algorithm.getSafeQueryPlan(queryDNF)
    querySQL = plan.generateSQL_DNF()
    cur.execute(querySQL)
    return cur.fetchone()[0]

def test_q1():
    conn = psycopg2.connect(dbname="sampling_test")
    conn.autocommit = True
    cur = conn.cursor()  
    cur.execute(open("test/test_data/non_boolean_sampling.sql", "r").read())
    dnf = safesample.query_parser.parse("Smokes*![3](),Friends[3,3]()")
    assert exactProb(dnf) == 0.009952

def test_q1_generic():
    conn = psycopg2.connect(dbname="sampling_test")
    conn.autocommit = True
    cur = conn.cursor()  
    cur.execute(open("test/test_data/non_boolean_sampling.sql", "r").read())
    dnf = safesample.query_parser.parse("Smokes*![c](),Friends[c,c]()")
    plan = algorithm.getSafeQueryPlan(dnf)
    sql = plan.generateSQL_DNF()
    cur.execute(sql)
    constants = set()
    for (c, p) in cur:
        constants.add(c)
        assert p == 0.009952 
    assert constants == set((3,4,6))

def test_q2_generic():
    conn = psycopg2.connect(dbname="sampling_test")
    conn.autocommit = True
    cur = conn.cursor()  
    cur.execute(open("test/test_data/non_boolean_sampling.sql", "r").read())
    dnf = safesample.query_parser.parse("Smokes*![-c](x),Friends[-c,c](x)")
    plan = algorithm.getSafeQueryPlan(dnf)
    sql = plan.generateSQL_DNF()
    cur.execute(sql)
    constants = set((3,4,6))
    count = 0
    for (c, p) in cur:
        count += 1
        if c in constants:
            assert p == 0.0198049576959999
        else:
            assert p == 0.0295598587570093 
    assert count == 10

def test_q3_generic():
    conn = psycopg2.connect(dbname="sampling_test")
    conn.autocommit = True
    cur = conn.cursor()  
    cur.execute(open("test/test_data/non_boolean_sampling.sql", "r").read())
    dnf = safesample.query_parser.parse("Smokes*![c](),Friends[-c](x)")
    plan = algorithm.getSafeQueryPlan(dnf)
    sql = plan.generateSQL_DNF()
    cur.execute(sql)
    constants = set()
    for (c, p) in cur:
        constants.add(c)
        assert p == 0.59349810824172 
    assert constants == set((3,4,6))

def test_smokes_friends_cancer_gamma():
    conn = psycopg2.connect(dbname="sampling_test")
    conn.autocommit = True
    cur = conn.cursor()  
    cur.execute(open("test/test_data/smokesfriendscancer-symmetric-20.sql", "r").read())
    
    domain = 20
    P1 = 0.667129
    P2 = 0.776870
    F = 0.009952
    C = 0.091123

    dnf = safesample.query_parser.parse("P1(x,y),Rel*!(x),Friends(x,y),~Rel*!(y) v P2(x),Rel*!(x),~Cancer(x)")
    plan = algorithm.getSafeQueryPlan(dnf)
    sql = plan.generateSQL_DNF()

    for r in range(5):
        cur.execute("drop table if exists Rel;")
        cur.execute("create table Rel as (select id, v0, CASE WHEN random() < p THEN 1 ELSE 0 END as p from smokes);")
        cur.execute("select count(*) from Rel where p = 1")
        cardinality = cur.fetchone()[0]

        cur.execute(sql)
        prob = cur.fetchone()[0]
        #print prob
        #print (1 - (1-(1 - (1-P2*(1-C))**cardinality))*(1-(1-(1-P1*F)**(cardinality*(domain-cardinality)))))

        assert abs(prob - (1 - (1-(1 - (1-P2*(1-C))**cardinality))*(1-(1-(1-P1*F)**(cardinality*(domain-cardinality)))))) < 0.000001

# TODO(ericgribkoff) standardize sampling across all estimators
# These rely on the sampled relation created as done manually here
def test_smokes_friends_cancer_query1():
    conn = psycopg2.connect(dbname="sampling_test")
    conn.autocommit = True
    cur = conn.cursor()  
    cur.execute(open("test/test_data/smokesfriendscancer-symmetric-20.sql", "r").read())
    
    domain = 20
    P1 = 0.667129
    P2 = 0.776870
    F = 0.009952
    C = 0.091123

    for r in range(1):
        cur.execute("drop table if exists Rel;")
        cur.execute("create table Rel as (select id, v0, CASE WHEN random() < p THEN 1 ELSE 0 END as p from smokes);")
        cur.execute("select count(*) from Rel where p = 1")
        cardinality = cur.fetchone()[0]

        probGamma = (1 - (1-(1 - (1-P2*(1-C))**cardinality))*(1-(1-(1-P1*F)**(cardinality*(domain-cardinality)))))

        for c in range(1, domain+1):
            dnf = safesample.query_parser.parse("Rel*![%d]() v P1(x,y),Rel*!(x),Friends(x,y),~Rel*(y) v P2(x),Rel*!(x),~Cancer(x)" % (c))
            plan = algorithm.getSafeQueryPlan(dnf)
            sql = plan.generateSQL_DNF()
            cur.execute(sql)
            probQ1 = cur.fetchone()[0]

            cur.execute("select count(*) from Rel where p = 1 and v0 = %d" % (c))
            inRelSample = (cur.fetchone()[0] > 0)

            if inRelSample:
                assert probQ1 == 1
            else:
                assert abs(probQ1 - probGamma) < 0.000001

def test_smokes_friends_cancer_query1_generic():
    conn = psycopg2.connect(dbname="sampling_test")
    conn.autocommit = True
    cur = conn.cursor()  
    cur.execute(open("test/test_data/smokesfriendscancer-symmetric-20.sql", "r").read())
    
    domain = 20
    P1 = 0.667129
    P2 = 0.776870
    F = 0.009952
    C = 0.091123

    for r in range(1):
        cur.execute("drop table if exists Rel;")
        cur.execute("create table Rel as (select id, v0, CASE WHEN random() < p THEN 1 ELSE 0 END as p from smokes);")
        cur.execute("select count(*) from Rel where p = 1")
        cardinality = cur.fetchone()[0]

        probGamma = (1 - (1-(1 - (1-P2*(1-C))**cardinality))*(1-(1-(1-P1*F)**(cardinality*(domain-cardinality)))))

        probConstants = [0]*(domain+1)
        dnf = safesample.query_parser.parse("Rel*![c]() v P1(x,y),Rel*!(x),Friends(x,y),~Rel*(y) v P2(x),Rel*!(x),~Cancer(x)" )
        plan = algorithm.getSafeQueryPlan(dnf)
        sql = plan.generateSQL_DNF()
        cur.execute(sql)
        for (const, prob) in cur:
            probConstants[const] = prob

        for c in range(1, domain+1):
            cur.execute("select count(*) from Rel where p = 1 and v0 = %d" % (c))
            inRelSample = (cur.fetchone()[0] > 0)
            if inRelSample:
                assert probConstants[c] == 1
            else:
                assert abs(probConstants[c] - probGamma) < 0.000001


def test_smokes_friends_cancer_query2():
    conn = psycopg2.connect(dbname="sampling_test")
    conn.autocommit = True
    cur = conn.cursor()  
    cur.execute(open("test/test_data/smokesfriendscancer-symmetric-20.sql", "r").read())
    
    domain = 20
    P1 = 0.667129
    P2 = 0.776870
    F = 0.009952
    C = 0.091123

    for r in range(1):
        cur.execute("drop table if exists Rel;")
        cur.execute("create table Rel as (select id, v0, CASE WHEN random() < p THEN 1 ELSE 0 END as p from smokes);")
        cur.execute("select count(*) from Rel where p = 1")
        cardinality = cur.fetchone()[0]

        for c in range(1, domain+1):
            dnf = safesample.query_parser.parse("Cancer[%d]() v P1(x,y),Rel*(x),Friends(x,y),~Rel*(y) v P2[-%d](x),Rel*[-%d](x),~Cancer[-%d](x) v P2[%d](),Rel*[%d]()" % (c,c,c,c,c,c))
            plan = algorithm.getSafeQueryPlan(dnf)
            sql = plan.generateSQL_DNF()
            cur.execute(sql)
            probQ1 = cur.fetchone()[0]

            cur.execute("select count(*) from Rel where p = 1 and v0 = %d" % (c))
            cardinalityJustC = cur.fetchone()[0] # because we shattered, need to see if c is in Rel* or not

            q1 = C
            q2 = 1-(1-P1*F)**(cardinality*(domain-cardinality))
            q3 = 1-(1-P2*(1-C))**(cardinality - cardinalityJustC)
            q4 = P2*cardinalityJustC
            probQuery = 1 - (1-q1)*(1-q2)*(1-q3)*(1-q4)
               
            print "Cancer[%d]() v P1(x,y),Rel*(x),Friends(x,y),~Rel*(y) v P2[-%d](x),Rel*[-%d](x),~Cancer[-%d](x) v P2[%d](),Rel*[%d]()" % (c,c,c,c,c,c)
            print probQ1
            print probQuery
            assert abs(probQ1 - probQuery) < 0.000001


def test_smokes_friends_cancer_query2_generic1():
    conn = psycopg2.connect(dbname="sampling_test")
    conn.autocommit = True
    cur = conn.cursor()  
    cur.execute(open("test/test_data/smokesfriendscancer-symmetric-20.sql", "r").read())
    
    domain = 20
    P1 = 0.667129
    P2 = 0.776870
    F = 0.009952
    C = 0.091123

    for r in range(1):
        cur.execute("drop table if exists Rel;")
        cur.execute("create table Rel as (select id, v0, CASE WHEN random() < p THEN 1 ELSE 0 END as p from smokes);")
        cur.execute("select count(*) from Rel where p = 1")
        cardinality = cur.fetchone()[0]

        probConstants = [0]*(domain+1)
        dnf = safesample.query_parser.parse("Cancer[c]() v P1(x,y),Rel*(x),Friends(x,y),~Rel*(y) v P2[-c](x),Rel*[-c](x),~Cancer[-c](x) v P2[c](),Rel*[c]()" )
        plan = algorithm.getSafeQueryPlan(dnf)
        sql = plan.generateSQL_DNF()
        cur.execute(sql)
        for (const, prob) in cur:
            probConstants[const] = prob

        for c in range(1, domain+1):
            cur.execute("select count(*) from Rel where p = 1 and v0 = %d" % (c))
            cardinalityJustC = cur.fetchone()[0] # because we shattered, need to see if c is in Rel* or not

            q1 = C
            q2 = 1-(1-P1*F)**(cardinality*(domain-cardinality))
            q3 = 1-(1-P2*(1-C))**(cardinality - cardinalityJustC)
            q4 = P2*cardinalityJustC
            probQuery = 1 - (1-q1)*(1-q2)*(1-q3)*(1-q4)

            assert abs(probConstants[c] - probQuery) < 0.000001

