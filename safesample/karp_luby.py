from __future__ import division
import psycopg2
import time

from numpy import *
import math

from algorithm import algorithm


class KarpLuby(object):
    sampleRecord = []
    estimatesRecord = []
    sampleTimes = []
    timesPerSample = []

    sumTermProbs = 0
    step1NumSamples = 0
    step2NumSamples = 0

    def __init__(self, dbConnection):
        self.conn = dbConnection

    def prepareQuery(self, query):
        maxComponentRels = max([len(c.getRelations())
                                for c in query.getConjuncts()])
        conjunctSQL = []
        for conjunct in query.getConjuncts():
            relations = conjunct.getRelations()

            relationNamesUsed = {}
            relationSQLIds = {}
            for rel in relations:
                relName = rel.getName()
                if relName in relationNamesUsed:
                    relationSQLIds[rel] = relName + \
                        str(relationNamesUsed[relName] + 1)
                    relationNamesUsed[relName] += 1
                else:
                    relationSQLIds[rel] = relName + str(1)
                    relationNamesUsed[relName] = 1

            relationNames = []
            for rel in relations:
                relName = rel.getName()
                relationNames.append(
                    "%s as %s" % (relName, relationSQLIds[rel]))
            relationsSQL = ', '.join(relationNames)

            relationsUsed = {}
            selectAtts = []
            equalityConstraints = []

            for rel in relations:
                if rel.isNegated():
                    selectAtts.append(
                        "'%s', -%s.id, %s.p" % (rel.getName(), relationSQLIds[rel], relationSQLIds[rel]))
                else:
                    selectAtts.append("'%s', %s.id, %s.p" % (
                        rel.getName(), relationSQLIds[rel], relationSQLIds[rel]))
                for i, constant in enumerate(rel.getConstraints()):
                    if not constant:
                        continue
                    elif constant > 0:
                        equalityConstraints.append(
                            "%s.v%d = %d" % (relationSQLIds[rel], i, constant))
                    else:
                        equalityConstraints.append(
                            "%s.v%d != %d" % (relationSQLIds[rel], i, -1 * constant))

            if len(relations) < maxComponentRels:
                for dummy in range(len(relations), maxComponentRels):
                    selectAtts.append("'', 0, 0")

            selectSQL = ', '.join(selectAtts)

            varPositions = [component.getVarPositions()
                            for component in conjunct.getComponents()]
            for componentVarPositions in varPositions:
                for v in componentVarPositions.keys():
                    relsWithVar = componentVarPositions[v].keys()

                    for i in range(len(relsWithVar) - 1):
                        positionsRelI = componentVarPositions[
                            v][relsWithVar[i]]
                        positionsRelIPlus1 = componentVarPositions[
                            v][relsWithVar[i + 1]]
                        for pos1 in positionsRelI:
                            for pos2 in positionsRelIPlus1:
                                equalityConstraints.append("%s.v%d = %s.v%d" %
                                                           (relationSQLIds[relsWithVar[i]], relsWithVar[i].getTableColumn(pos1),
                                                            relationSQLIds[relsWithVar[i + 1]], relsWithVar[i + 1].getTableColumn(pos2)))

            if len(equalityConstraints):
                whereSQL = "WHERE %s" % ' AND '.join(equalityConstraints)
            else:
                whereSQL = ""

            conjunctSQL.append("SELECT %s FROM %s %s" % (selectSQL, relationsSQL,
                                                         whereSQL))

        lineageQuery = ' UNION '.join(conjunctSQL)
        print algorithm.getPrettySQL(lineageQuery)
        return lineageQuery

    def getEstimates(self):
        self.estimatesRecord = []
        sumSoFar = 0
        for i in range(len(self.sampleRecord)):
            sumSoFar += self.sampleRecord[i]
            self.estimatesRecord.append(
                sumSoFar / (i + 1) * self.sumTermProbs)
        return self.estimatesRecord

    def karpLuby(self, query, numSamples, epsilon=0, delta=0):
        lineageQuery = self.prepareQuery(query)
        if epsilon > 0 and delta > 0:
            return self.sampleOptimal(lineageQuery, numSamples, epsilon, delta)
        else:
            return self.sample(lineageQuery, numSamples)

    def sample(self, lineageQuery, numSamples):
        cur = self.conn.cursor()

        self.sampleRecord = []
        self.estimatesRecord = []

        varsHashMap = {}
        varCounter = 1
        varProbs = [0]  # skip 0-index, so literals can be + or - indices
        terms = []
        termProbs = []
        termsSeen = set()

        try:
            cur.execute(lineageQuery)
            for c in cur:
                term = []
                prob = 1
                # Rows have format [R1,V1,P1,R2,V2,P2,...]
                # for queries with self-joins, may have repeated id/rel
                literalsInTerm = {}
                termIsFalse = False  # lineage may include x ^ ~x
                for i in range(0, len(c), 3):
                    relation = c[i]
                    relId = c[i + 1]
                    varProb = float(c[i + 2])

                    if relation == '':
                        # Skip "dummy" columns added to satisfy SQL union
                        # condition
                        continue

                    litSign = sign(relId)

                    hashKey = (relation, abs(relId))

                    if hashKey in literalsInTerm:
                        if literalsInTerm[hashKey] == litSign:
                            continue
                        else:
                            termIsFalse = True
                            break
                    else:
                        literalsInTerm[hashKey] = litSign

                    if hashKey in varsHashMap:
                        term.append(litSign * varsHashMap[hashKey])
                    else:
                        varsHashMap[hashKey] = varCounter
                        term.append(litSign * varsHashMap[hashKey])
                        varProbs.append(varProb)
                        varCounter += 1
                    if litSign > 0:
                        prob *= varProb
                    else:
                        prob *= (1 - varProb)
                if termIsFalse:
                    continue
                term.sort()
                termAsTuple = tuple(term)
                if termAsTuple not in termsSeen:
                    termsSeen.add(termAsTuple)
                    terms.append(term)
                    termProbs.append(prob)

            numVars = varCounter - 1
            numTerms = len(terms)
            self.sumTermProbs = sum(termProbs)
            if self.sumTermProbs == 0:
                return 0
            P = array(termProbs) / self.sumTermProbs

            # print terms
            startTime = time.time()
            sampledSum = 0
            for k in range(numSamples):
                if k > 0 and k % 500 == 0:
                    print "Computing sample %d" % (k + 1)
                initTime = time.time()
                i = random.choice(numTerms, p=P)

                pickedTerm = terms[i]
                # sample a random number for each var
                sampleProbs = random.sample(numVars + 1)

                sampledTruth = sampleProbs < varProbs

                # Force literals in the chosen term to be true/false
                for lit in pickedTerm:
                    var = abs(lit)
                    litSign = sign(lit)
                    if litSign > 0:
                        sampledTruth[var] = 1
                    else:
                        sampledTruth[var] = 0

                lowerTermSat = False
                for term in terms[0:i]:
                    sat = True
                    for lit in term:
                        var = abs(lit)
                        litSign = sign(lit)
                        if (litSign > 0 and not sampledTruth[var]) or \
                                (litSign < 0 and sampledTruth[var]):
                            sat = False
                            break
                    if sat:
                        lowerTermSat = True
                        break
                if not lowerTermSat:
                    self.sampleRecord.append(1)
                    sampledSum += 1
                else:
                    self.sampleRecord.append(0)
                self.estimatesRecord.append(
                    sampledSum / (k + 1) * self.sumTermProbs)
                self.sampleTimes.append(time.time() - initTime)
                self.timesPerSample.append(time.time() - startTime)
            return sampledSum / numSamples * self.sumTermProbs
        except psycopg2.Error as e:
            print "SQL error: %s" % e.pgerror
            cur.close()
            return -1

    def sampleOptimal(self, lineageQuery, numSamples, epsilon, delta):
        cur = self.conn.cursor()

        self.sampleRecord = []
        self.estimatesRecord = []

        try:
            (varsHashMap, varCounter, varProbs, terms, termProbs, termsSeen, numVars,
             numTerms, self.sumTermProbs, P) = self.processLineage(lineageQuery, cur)
        except psycopg2.Error as e:
            print "SQL error: %s" % e.pgerror
            cur.close()
            return -1
        except TypeError as e:
            print "Error: %s" % e
            cur.close()
            return 0

        # def according to Dagum Karp Luby Ross paper
        lam = math.exp(1) - 2
        gamma = 4 * lam * math.log(2.0 / delta) / epsilon ** 2

        # this is the correct computation of gamma2 (upsilon2):
        gamma2 = 2 * (1 + math.sqrt(epsilon)) * (1 + 2 * math.sqrt(epsilon)
                                                 ) * (1 + math.log(1.5) / math.log(2.0 / delta)) * gamma
        # this is the wrong computation of gamma2 (upsilon2), which is implemented in MayBMS:
        #gamma2 = 2 * (1 + math.sqrt(epsilon)) * (1 + 2*math.sqrt(epsilon)) * (1 + math.log(1.5)) / math.log(2.0/delta) * gamma

        # step 1
        (muHatZ, sampledZ) = self.stoppingRuleAlgorithm(amin(
            [0.5, math.sqrt(epsilon)]), delta / 3.0, terms, P, numTerms, numVars, varProbs)

        # step 2
        N = gamma2 * epsilon / muHatZ
        S = 0
        self.step2NumSamples = int(N) * 2  # each loop takes two samples
        print "Step 2 N: ", N
        for i in range(int(N)):
            ZPrime2i = self.doSampleStep(terms, P, numTerms, numVars, varProbs)
            ZPrime2iMinus1 = self.doSampleStep(
                terms, P, numTerms, numVars, varProbs)
            S += (ZPrime2iMinus1 - ZPrime2i) ** 2 / 2.0
        rhoTildeZ = amax([S / N, epsilon * muHatZ])

        # step 3
        N = gamma2 * rhoTildeZ / muHatZ ** 2
        S = 0
        print "Step 3 N: ", N
        for i in range(int(N)):
            if i < len(sampledZ):
                S += sampledZ[i]
            else:
                initTime = time.time()
                z = self.doSampleStep(terms, P, numTerms, numVars, varProbs)
                self.sampleTimes.append(time.time() - initTime)
                self.sampleRecord.append(z)
                S += z
        muTildeZ = S / N

        return muTildeZ * self.sumTermProbs

    # def according to Dagum Karp Luby Ross paper
    def stoppingRuleAlgorithm(self, epsilon, delta, terms, P, numTerms, numVars, varProbs):
        lam = math.exp(1) - 2
        gamma = 4 * lam * math.log(2.0 / delta) / epsilon ** 2

        sampledZ = []

        gamma1 = 1 + (1 + epsilon) * gamma
        N = 0
        S = 0
        while S < gamma1:
            N += 1
            initTime = time.time()
            z = self.doSampleStep(terms, P, numTerms, numVars, varProbs)
            self.sampleTimes.append(time.time() - initTime)
            self.sampleRecord.append(z)
            S += z
            sampledZ.append(z)

        muHatZ = gamma1 / N

        self.step1NumSamples = N
        print "Step 1 N: ", N
        return (muHatZ, sampledZ)

    def processLineage(self, lineageQuery, cur):
        varsHashMap = {}
        varCounter = 1
        varProbs = [0]  # skip 0-index, so literals can be + or - indices
        terms = []
        termProbs = []
        termsSeen = set()
        numVars = 0

        cur.execute(lineageQuery)
        for c in cur:
            term = []
            prob = 1
            # Rows have format [R1,V1,P1,R2,V2,P2,...]
            # for queries with self-joins, may have repeated id/rel
            literalsInTerm = {}
            termIsFalse = False  # lineage may include x ^ ~x
            for i in range(0, len(c), 3):
                relation = c[i]
                relId = c[i + 1]
                varProb = float(c[i + 2])

                if relation == '':
                    # Skip "dummy" columns added to satisfy SQL union
                    # condition
                    continue

                litSign = sign(relId)

                hashKey = (relation, abs(relId))

                if hashKey in literalsInTerm:
                    if literalsInTerm[hashKey] == litSign:
                        continue
                    else:
                        termIsFalse = True
                        break
                else:
                    literalsInTerm[hashKey] = litSign

                if hashKey in varsHashMap:
                    term.append(litSign * varsHashMap[hashKey])
                else:
                    varsHashMap[hashKey] = varCounter
                    term.append(litSign * varsHashMap[hashKey])
                    varProbs.append(varProb)
                    varCounter += 1
                if litSign > 0:
                    prob *= varProb
                else:
                    prob *= (1 - varProb)
            if termIsFalse:
                continue
            term.sort()
            termAsTuple = tuple(term)
            if termAsTuple not in termsSeen:
                termsSeen.add(termAsTuple)
                terms.append(term)
                termProbs.append(prob)

        numVars = varCounter - 1
        numTerms = len(terms)
        self.sumTermProbs = sum(termProbs)
        if self.sumTermProbs == 0:
            return 0
        P = array(termProbs) / self.sumTermProbs

        return (varsHashMap, varCounter, varProbs, terms, termProbs, termsSeen, numVars, numTerms, self.sumTermProbs, P)

    def doSampleStep(self, terms, termProbs, numTerms, numVars, varProbs):
        return self.doSampleStepFractional(terms, termProbs, numTerms, numVars, varProbs)

    # return a 0/1 estimator, as defined by Karp-Luby
    def doSampleStepOriginal(self, terms, termProbs, numTerms, numVars, varProbs):

        initTime = time.time()
        i = random.choice(numTerms, p=termProbs)

        pickedTerm = terms[i]
        # sample a random number for each var
        sampleProbs = random.sample(numVars + 1)

        sampledTruth = sampleProbs < varProbs

        # Force literals in the chosen term to be true/false
        for lit in pickedTerm:
            var = abs(lit)
            litSign = sign(lit)
            if litSign > 0:
                sampledTruth[var] = 1
            else:
                sampledTruth[var] = 0

        lowerTermSat = False
        for term in terms[0:i]:
            sat = True
            for lit in term:
                var = abs(lit)
                if (lit > 0 and not sampledTruth[var]) or \
                        (lit < 0 and sampledTruth[var]):
                    sat = False
                    break
            if sat:
                lowerTermSat = True
                break

        if not lowerTermSat:
            return 1
        else:
            return 0

    # Vazirani estimator (implemented in MayBMS, returns fraction of clauses
    # satisfied)
    def doSampleStepFractional(self, terms, termProbs, numTerms, numVars, varProbs):
        initTime = time.time()

        i = random.choice(numTerms, p=termProbs)

        pickedTerm = terms[i]
        # sample a random number for each var
        sampleProbs = random.sample(numVars + 1)

        sampledTruth = sampleProbs < varProbs

        # Force literals in the chosen term to be true/false
        for lit in pickedTerm:
            var = abs(lit)
            if lit > 0:
                sampledTruth[var] = True
            else:
                sampledTruth[var] = False

        numTermsSat = 0
        for term in terms:
            sat = True
            for lit in term:
                var = abs(lit)
                if (lit > 0 and not sampledTruth[var]) or \
                        (lit < 0 and sampledTruth[var]):
                    sat = False
                    break
            if sat:
                numTermsSat += 1
        return 1.0 / numTermsSat
