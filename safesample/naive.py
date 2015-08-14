from __future__ import division
import psycopg2
import time

from numpy import *

from algorithm import algorithm


class NaiveSampler(object):
    sampleRecord = []
    estimatesRecord = []
    sampleTimes = []

    def __init__(self, dbConnection):
        self.conn = dbConnection

    def prepareQuery(self, query):

        allRelationsUsed = set()
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
                    if relName not in allRelationsUsed:
                        allRelationsUsed.add(relName)

            relationNames = []
            for rel in relations:
                relName = rel.getName()
                relationNames.append(
                    "%s as %s" % (relName, relationSQLIds[rel]))
            relationsSQL = ', '.join(relationNames)

            relationsUsed = {}
            equalityConstraints = []

            for rel in relations:
                if rel.isNegated():
                    equalityConstraints.append(
                        "%s.InSample = 0" % (relationSQLIds[rel]))
                else:
                    equalityConstraints.append(
                        "%s.InSample = 1" % (relationSQLIds[rel]))
                for i, constant in enumerate(rel.getConstraints()):
                    if not constant:
                        continue
                    elif constant > 0:
                        equalityConstraints.append(
                            "%s.v%d = %d" % (relationSQLIds[rel], i, constant))
                    else:
                        equalityConstraints.append(
                            "%s.v%d != %d" % (relationSQLIds[rel], i, -1 * constant))

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

            conjunctSQL.append("SELECT EXISTS (SELECT * FROM %s %s)" % (relationsSQL,
                                                                        whereSQL))

        sampledTables = []
        for relName in allRelationsUsed:
            sampledTables.append(
                "%s as (select *, CASE WHEN random() < p THEN 1 ELSE 0 END as InSample FROM %s)" % (relName, relName))

        sampleTableSQL = ', '.join(sampledTables)

        querySQL = 'WITH %s SELECT true IN (%s) Q' % (
            sampleTableSQL, ' UNION '.join(conjunctSQL))
        print algorithm.getPrettySQL(querySQL)
        return querySQL

    def naiveSample(self, query, numSamples):
        querySQL = self.prepareQuery(query)
        return self.sample(querySQL, numSamples)

    def sample(self, querySQL, numSamples):
        cur = self.conn.cursor()
        self.sampleRecord = []
        self.estimatesRecord = []
        sampledSum = 0
        for i in range(numSamples):
            if i > 0 and i % 500 == 0:
                print "Computing sample %d" % (i + 1)
            initTime = time.time()
            cur.execute(querySQL)
            queryTrue = cur.fetchone()[0]
            if queryTrue:
                sampledSum = sampledSum + 1
                self.sampleRecord.append(1)
            else:
                self.sampleRecord.append(0)
            self.estimatesRecord.append(sampledSum / (i + 1))
            self.sampleTimes.append(time.time() - initTime)
        return sampledSum / (i + 1)
