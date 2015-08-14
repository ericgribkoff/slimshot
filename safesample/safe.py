from __future__ import division
import psycopg2
import time
import math
import numpy as np


class SafeSample(object):
    sampleRecord = []
    estimatesRecord = []
    sampleTimes = []

    step2NumSamples = 0

    def __init__(self, dbConnection):
        self.conn = dbConnection

    def prepareQuery(self, relationsToSample, relsObjects, querySQL):
        sampledTables = []
        for rel in relsObjects:
            relSym = rel.getName()
            # TODO(ericgribkoff) generalize this for sampled relations with
            # more than just v0
            sampledTables.append(
                "%s as (select v0, CASE WHEN random() < p THEN 1 ELSE 0 END as p from %s)" % (relSym, relSym))

        safeSampleQuery = "with %s %s" % (', '.join(sampledTables),
                                          querySQL)

        print safeSampleQuery

        return safeSampleQuery

    def getEstimates(self):
        self.estimatesRecord = []
        sumSoFar = 0
        for i in range(len(self.sampleRecord)):
            sumSoFar += self.sampleRecord[i]
            self.estimatesRecord.append(sumSoFar / (i + 1))
        return self.estimatesRecord

    def safeSample(self, relationsToSample, relsObjects, querySQL, numSamples, epsilon=0, delta=0):
        safeSampleQuery = self.prepareQuery(
            relationsToSample, relsObjects, querySQL)
        self.sampleRecord = []
        self.estimatesRecord = []

        if epsilon > 0 and delta > 0:
            return self.sampleOptimal(safeSampleQuery, numSamples, epsilon, delta)
        else:
            return self.sample(safeSampleQuery, numSamples)

    def sample(self, safeSampleQuery, numSamples):
        cur = self.conn.cursor()
        total = 0
        try:
            for i in range(numSamples):
                if i > 0 and i % 500 == 0:
                    print "Computing sample %d" % (i + 1)
                initTime = time.time()
                cur.execute(safeSampleQuery)
                residualProb = cur.fetchone()[0]
                total = total + residualProb
                self.sampleRecord.append(residualProb)
                self.estimatesRecord.append(total / (i + 1))
                self.sampleTimes.append(time.time() - initTime)
            cur.close()
            return total / numSamples
        except psycopg2.Error as e:
            print "SQL error: %s" % e.pgerror
            cur.close()
            return -1

    def sampleOptimal(self, safeSampleQuery, numSamples, epsilon, delta):
        cur = self.conn.cursor()
        total = 0
        try:
            # def according to Dagum Karp Luby Ross paper
            lam = math.exp(1) - 2
            gamma = 4 * lam * math.log(2.0 / delta) / epsilon ** 2

            gamma2 = 2 * (1 + math.sqrt(epsilon)) * (1 + 2 * math.sqrt(epsilon)
                                                     ) * (1 + math.log(1.5) / math.log(2.0 / delta)) * gamma

            # step 1
            (muHatZ, sampledZ) = self.stoppingRuleAlgorithm(
                np.amin([0.5, math.sqrt(epsilon)]), delta / 3.0, safeSampleQuery)

            # step 2
            N = gamma2 * epsilon / muHatZ
            S = 0
            print "Step 2 N: ", N
            self.step2NumSamples = int(N) * 2  # each loop takes two samples
            for i in range(int(N)):
                ZPrime2i = self.doSampleStep(safeSampleQuery)
                ZPrime2iMinus1 = self.doSampleStep(safeSampleQuery)
                S += (ZPrime2iMinus1 - ZPrime2i) ** 2 / 2.0
            rhoTildeZ = np.amax([S / N, epsilon * muHatZ])

            # step 3
            N = gamma2 * rhoTildeZ / muHatZ ** 2
            S = 0
            print "Step 3 N: ", N
            for i in range(int(N)):
                if i < len(sampledZ):
                    S += sampledZ[i]
                else:
                    S += self.doSampleStep(safeSampleQuery, True)
            muTildeZ = S / N

            return muTildeZ
        except psycopg2.Error as e:
            print "SQL error: %s" % e.pgerror
            cur.close()
            return -1

    # def according to Dagum Karp Luby Ross paper
    def stoppingRuleAlgorithm(self, epsilon, delta, safeSampleQuery):
        lam = math.exp(1) - 2
        gamma = 4 * lam * math.log(2.0 / delta) / epsilon ** 2

        sampledZ = []

        # stopping rule algorithm
        gamma1 = 1 + (1 + epsilon) * gamma
        N = 0
        S = 0
        while S < gamma1:
            N += 1
            z = self.doSampleStep(safeSampleQuery, True)
            S += z
            sampledZ.append(z)

        muHatZ = gamma1 / N

        print "Step 1 N: ", N

        return (muHatZ, sampledZ)

    def doSampleStep(self, safeSampleQuery, record=False):
        cur = self.conn.cursor()
        initTime = time.time()
        cur.execute(safeSampleQuery)
        residualProb = cur.fetchone()[0]
        if record:
            self.sampleTimes.append(time.time() - initTime)
            self.sampleRecord.append(residualProb)
        return residualProb
