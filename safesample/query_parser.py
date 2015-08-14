from __future__ import division
import argparse
import cmd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
try:
    import pygraphviz as pgv
except:
    pass
import logging
import psycopg2
import re
import sys
import time

from algorithm import algorithm, query_exp, query_sym
import karp_luby
import naive
import safe


class ParseError(Exception):

    def __init__(self, arg):
        self.args = arg


def getPlan(queryDNF):
    return algorithm.getSafeQueryPlan(queryDNF)


def executeSQL(sql):
    prob = None
    cur = conn.cursor()
    try:
        cur.execute(sql)
        prob = cur.fetchone()[0]
        cur.close()
    except psycopg2.Error as e:
        print "SQL error: %s" % e.pgerror
        cur.close()
    return prob


def printProbability(sql):
    prob = executeSQL(sql)
    if prob is not None:
        print "Query probability: %f (exact)" % prob
        return prob


def drawTree(plan, filename):
    T = pgv.AGraph(directed=True)
    T.graph_attr['dpi'] = 300
    plan.buildTree(T)
    T.layout(prog='dot')
    T.draw(filename)


def parseRelation(
        relString,
        constantString,
        varString,
        useConstraintClass=False):
    relName = relString
    relDet = False
    relNeg = False
    relSampled = False
    if len(relString) > 1 and relString[-1] == '!' and relString[-2] == '*':
        relName = relName[:-2]
        relDet = True
        relSampled = True
    if relString[-1] == '*':
        relName = relName[:-1]
        relDet = True
    if relString[0] == '~':
        relName = relName[1:]
        relNeg = True
    if len(varString):
        relVars = map(lambda x: query_sym.Variable(x), varString.split(','))
    else:
        relVars = []
    constraints = []
    if constantString:
        constantString = constantString[1:-1]
        constants = constantString.split(',')
        for (i, c) in enumerate(constants):
            if useConstraintClass:
                constraints.append(query_sym.Constraint(c))
            else:
                if c == '*':
                    constraints.append(None)
                    continue
                if c == 'c' or c == '-c':
                    constraints.append(c)
                    continue
                cInt = int(c)
                constraints.append(cInt)
    if useConstraintClass:
        varIndex = 0
        inequalityGenericConstants = set()
        for constraint in constraints:
            if constraint.isInequality() and constraint.isGeneric():
                if constraint.getConstant() in inequalityGenericConstants:
                    raise Exception(
                        "Inequality generic constraints must be ",
                        "unique for non-joined variables")
                inequalityGenericConstants.add(constraint.getConstant())
            if constraint.isInequality():
                relVars[varIndex].setInequality(constraint)
            if not constraint.isEquality():
                varIndex += 1

    if relName == 'A':
        raise Exception(
            "A is a reserved relation name ",
            "(used for active domain in sampling)")
    return query_sym.Relation(
        relName,
        relVars,
        deterministic=relDet,
        negated=relNeg,
        sampled=relSampled,
        constraints=constraints)


def parseConjunct(conjunct):
    relations = []
    regex = re.compile("(~?[A-Za-z0-9]+\*?\!?)(\[[,\-0-9c\*]+\])?\((.*?)\)")
    if not regex.match(conjunct):
        raise ParseError("Failed to parse")
    for (relString, constantString, varString) in regex.findall(conjunct):
        relations.append(parseRelation(relString, constantString, varString))
    return query_exp.ConjunctiveQuery(
        query_exp.decomposeComponent(
            query_exp.Component(relations)))


def parseConjunctUsingConstraintClass(conjunct):
    relations = []
    regex = re.compile("(~?[A-Za-z0-9]+\*?\!?)(\[[,\-0-9a-z\*]+\])?\((.*?)\)")
    if not regex.match(conjunct):
        raise ParseError("Failed to parse")
    for (relString, constantString, varString) in regex.findall(conjunct):
        relations.append(
            parseRelation(
                relString,
                constantString,
                varString,
                useConstraintClass=True))
    return query_exp.ConjunctiveQuery(
        query_exp.decomposeComponent(
            query_exp.Component(relations)))


def parse(queryStr, useConstraintClass=False):
    conjunctsRaw = queryStr.split(' v ')
    if useConstraintClass:
        conjunctsParsed = map(parseConjunctUsingConstraintClass, conjunctsRaw)
    else:
        conjunctsParsed = map(parseConjunct, conjunctsRaw)
    return query_exp.DNF(conjunctsParsed)


class CommandLineParser(cmd.Cmd):
    prompt = '> '
    rankQueries = False
    execSQL = True
    graph = False
    graphQueryPlan = False
    sample = True
    karpluby = False
    naive = False
    numSamples = 1000
    graphQueryPlanFile = "/tmp/query.png"
    showGraph = False
    exact = 0
    epsilon = 0.1
    delta = 0.1

    def default(self, line):
        try:
            safeSampleEstimates = []
            safeSampleTimes = []
            karpLubyEstimates = []
            karpLubyTimes = []
            naiveEstimates = []
            naiveTimes = []
            exactProb = 0
            queryStr = line
            queryDNF = parse(queryStr)
            print "Query: ", queryDNF
            try:
                plan = getPlan(queryDNF)
                querySQL = plan.generateSQL_DNF()
                print algorithm.getPrettySQL(querySQL), "\n"
                if self.graphQueryPlan:
                    drawTree(plan, self.graphQueryPlanFile)
                    print "\nQuery plan saved to %s" % self.graphQueryPlanFile
                if self.execSQL:
                    exactProb = printProbability(querySQL)
            except algorithm.UnsafeException:
                if self.sample:
                    try:
                        startTime = time.time()
                        print ("Query unsafe, ",
                               "trying to find safe residual query")
                        (relationsToSample,
                         residualDNF,
                         querySQL,
                         relsObjects) = algorithm.\
                            findSafeResidualQuery(queryDNF)
                        print ("Relations to sample: ",
                               ', '.join(relationsToSample))
                        print "Residual Query: ", residualDNF
                        print algorithm.getPrettySQL(querySQL), "\n"
                        if self.execSQL:
                            ssExecutor = safe.SafeSample(conn)
                            estimate = ssExecutor.safeSample(
                                relationsToSample,
                                relsObjects,
                                querySQL,
                                self.numSamples,
                                self.epsilon,
                                self.delta)
                            print "SafeSample Estimate:", estimate
                            safeSampleTimes = ssExecutor.sampleTimes
                            print "SafeSample Total Time: %f seconds" % (
                                time.time() - startTime)
                            print "SafeSample Mean Sample Time: %f seconds" % (
                                sum(safeSampleTimes) /
                                float(len(safeSampleTimes)))
                            safeSampleEstimates = ssExecutor.getEstimates()
                            print "SafeSample Number of Samples: " + \
                                   "%d (%d + %d to estimate variance)" % (
                                len(safeSampleEstimates) +
                                ssExecutor.step2NumSamples,
                                len(safeSampleEstimates),
                                ssExecutor.step2NumSamples)
                    except algorithm.UnsafeException:
                        print "Error: No safe residual query found"
                else:
                    print "Query is unsafe"

            if self.naive:
                print ""
                startTime = time.time()
                naiveExecutor = naive.NaiveSampler(conn)
                estimate = naiveExecutor.naiveSample(queryDNF, self.numSamples)
                print "Naive Sampler Estimate: %f (%d samples)" % (
                    estimate, self.numSamples)
                naiveEstimates = naiveExecutor.estimatesRecord
                naiveTimes = naiveExecutor.sampleTimes
                print "Naive Sampler Total Time: %f seconds" % (
                    time.time() - startTime)
                print "Naive Sampler Mean Sample Time: %f seconds" % (
                    sum(naiveTimes) / float(len(naiveTimes)))

            if self.karpluby:
                print ""
                startTime = time.time()
                klExecutor = karp_luby.KarpLuby(conn)
                estimate = klExecutor.karpLuby(
                    queryDNF, self.numSamples, self.epsilon, self.delta)
                print "Karp-Luby Estimate:", estimate
                karpLubyTimes = klExecutor.sampleTimes
                print "Karp-Luby Total Time: %f seconds" % (
                    time.time() - startTime)
                print "Karp-Luby Mean Sample Time: %f seconds" % (
                    sum(karpLubyTimes) / float(len(karpLubyTimes)))
                karpLubyEstimates = klExecutor.getEstimates()
                print "Karp-Luby Number of Samples: %d (%d + %d to estimate variance)" % (
                    len(karpLubyEstimates) + klExecutor.step2NumSamples,
                    len(karpLubyEstimates), klExecutor.step2NumSamples)
                print "Karp-Luby Stopping Rule Samples " + \
                       "(included in total above): %d" % (
                    klExecutor.step1NumSamples)

        except ParseError:
            print "Failed to parse"

    def emptyline(self):
        pass

    def do_1(self, line):
        self.default("R(x),S(y)")

    def do_2(self, line):
        self.default("R1(x),R2(x),S1(y),S2(y)")

    def do_3(self, line):
        self.default("S(x,y),S(y,x)")

    def do_4(self, line):
        self.default("R*(x),S(x,y),~R*(y) v ~R*(x),S(x,y),R*(y)")

    def do_5(self, line):
        self.default("R(x),S(x,y),~R(y) v ~R(x),S(x,y),R(y)")

    def do_6(self, line):
        self.default("R*(x),S(x,y),~R*(y) v ~R*(x),S(x,y),R*(y) v ~R*(x),T(x)")

    def do_7(self, line):
        self.default("R(x),S(x,y),~R(y) v ~R(x),S(x,y),R(y) v ~R(x),T(x)")

    def do_h0(self, line):
        self.default("R(x),S(x,y),T(y)")

    def do_h1(self, line):
        self.default("R(x),S(x,y) v S(x,y),T(y)")

    def do_exact(self, line):
        self.exact = float(line)
        print "Exact query probability set to %f" % self.exact

    def do_numsamples(self, line):
        try:
            self.numSamples = int(line)
            print "Number of samples set to %d" % self.numSamples
        except:
            print "Failed to parse number of samples"

    def do_graph(self, line):
        self.graph = not self.graph
        if line:
            self.graph = True
            self.graphFile = line
            print "Graph will be saved to %s" % line
        else:
            if self.graph:
                print "Save graph on"
            else:
                print "Save graph off"

    def do_queryplan(self, line):
        self.graphQueryPlan = not self.graphQueryPlan
        if line:
            self.graphQueryPlan = True
            self.graphQueryPlanFile = line
            print "Query plan graph will be saved to %s" % line
        else:
            if self.graphQueryPlan:
                print "Save query plan graph on"
            else:
                print "Save query plan graph off"

    def do_sample(self, line):
        self.sample = not self.sample
        if self.sample:
            print "Safe sample on"
        else:
            print "Safe sample off"

    def do_sql(self, line):
        self.execSQL = not self.execSQL
        if self.execSQL:
            print "Execute SQL on"
        else:
            print "Execute SQL off"

    def do_karpluby(self, line):
        self.karpluby = not self.karpluby
        if self.karpluby:
            print "Karp-Luby on"
        else:
            print "Karp-Luby off"

    def do_naive(self, line):
        self.naive = not self.naive
        if self.naive:
            print "Naive sample on"
        else:
            print "Naive sample off"

    def do_epsilon(self, line):
        self.epsilon = float(line)
        print "Epsilon = %f" % self.epsilon

    def do_delta(self, line):
        self.delta = float(line)
        print "Delta = %f" % self.delta

    def do_EOF(self, line):
        print ""
        return True

    def help_overview(self):
        print "\nQuery Format:\n"
        print "R(x),S*(x,y) v S*(x,y),T(y)"
        print "(* denotes deterministic relation)\n"
        print "Extra commands:\n"
        print "karpluby : toggle Karp-Luby estimate (default=True)"
        print ("numsamples INT : number of samples for SafeSample ",
               "and Karp-Luby (default=1000)")
        print "sample : toggle sampling for unsafe queries (default=True)"
        print "queryplan [file]: save query plan to file, or /tmp/query.png"
        print "sql : toggle executing SQL (default=True)\n"

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Usage: python query_parser.py [--db database: default=sampling]')
    parser.add_argument("--db", default="sampling")
    args = parser.parse_args()
    database = args.db

    conn = psycopg2.connect(dbname=database)
    conn.autocommit = True
    
    CommandLineParser().cmdloop()
