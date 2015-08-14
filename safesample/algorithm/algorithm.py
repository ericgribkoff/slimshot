from collections import defaultdict
import itertools
import nltk
import sqlparse
import pprint

import ground_tup
import incl_excl
import ind_join
import ind_proj
import ind_union
import query_exp
import query_sym


def getSafeQueryPlan(dnf):
    if isinstance(dnf, query_exp.DNF):
        cnf = dnf.toCNF().minimize()
    else:
        cnf = dnf.minimize()

    symbolComponentsDNF = query_exp.computeSymbolComponentsDNF(dnf)

    if len(symbolComponentsDNF) > 1:
        termList = [query_exp.DNF((list(s))) for s in symbolComponentsDNF]
        return ind_union.IndependentUnion(cnf, termList)

    symbolComponents = query_exp.computeSymbolComponentsCNF(cnf)

    # independent join
    if len(symbolComponents) > 1:
        termList = [query_exp.CNF(list(s)) for s in symbolComponents]
        return ind_join.IndependentJoin(cnf, termList)

    # inclusion/exclusion
    if len(cnf.getDisjuncts()) > 1:
        termList = []
        coeffList = []

        for x in powerset(cnf.getDisjuncts()):
            if len(x):
                termList.append(
                    query_exp.CNF(
                        [query_exp.DisjunctiveQuery(
                            [c.copy() for d in x for c in d.getComponents()]
                        )
                        ]
                    )
                )
                coeffList.append((-1) ** len(x))

        lexpr = nltk.Expression.fromstring
        for i in range(len(termList)):
            if coeffList[i] == 0:
                continue
            for j in range(i + 1, len(termList)):
                if coeffList[j] == 0:
                    continue
                p9termI = lexpr(termList[i].toProver9())
                p9termJ = lexpr(termList[j].toProver9())
                proverItoJ = nltk.Prover9Command(
                    p9termJ, assumptions=[p9termI])
                proverJtoI = nltk.Prover9Command(
                    p9termI, assumptions=[p9termJ])
                if proverItoJ.prove() and proverJtoI.prove():
                    coeffList[i] += coeffList[j]
                    coeffList[j] = 0

        subplans = []
        finalCoeffList = []
        for ind, term in enumerate(termList):
            if coeffList[ind] == 0:
                continue
            subplans.append(term)
            finalCoeffList.append(coeffList[ind])

        return incl_excl.InclusionExclusion(cnf, subplans, finalCoeffList)

    d = cnf.getDisjuncts()[0]
    symbolComponents = query_exp.computeSymbolComponentsDisjunct(d)

    # independent union
    if len(symbolComponents) > 1:
        termList = [
            query_exp.CNF(
                [query_exp.DisjunctiveQuery(list(s))]
            ) for s in symbolComponents]

        return ind_union.IndependentUnion(cnf, termList)

    # ground tuple
    if not d.hasVariables():
        comInd = 0  # only one component in a ground tuple
        rel = d.getComponents()[comInd].getRelations()[comInd]
        return ground_tup.GroundTuple(cnf, d, rel)

    # separator variable
    separator = d.getSeparator()
    if separator:
        return ind_proj.IndependentProject(cnf, d, separator)

    lexpr = nltk.Expression.fromstring
    p9d = lexpr(d.toProver9())

    for x in powerset(d.getRelations()):
        if len(x) > 1:
            proposedComponent = query_exp.Component(x)

            # TODO(ericgribkoff) Fix query R(x,y),R(y,z),~R(z,x)
            # right now prover9 is timing out on:
            # p9 assertion: (R(x,y), ~R(z,x)) p9 kb: exists y x z.(R(x,y) &
            # R(y,z) & -R(z,x))

            # TODO(ericgribkoff) Temporary fix for the above problem
            if any([r.isNegated() for r in x]):
                continue

            p9component = lexpr(proposedComponent.toProver9())
            prover = nltk.Prover9Command(p9d, assumptions=[p9component])
            componentFalse = nltk.Prover9Command(
                lexpr(r'False'), assumptions=[p9component])
            if (prover.prove() and not componentFalse.prove() and not any(
                [proposedComponent.containedIn(c) for c in d.getComponents()]
            )):
                newConjQueries = []
                newConjQueries.append(query_exp.ConjunctiveQuery(
                    query_exp.decomposeComponent(proposedComponent)))
                for c in d.getComponents():
                    newConjQueries.append(query_exp.ConjunctiveQuery([c]))
                newDNF = query_exp.DNF(newConjQueries)
                return getSafeQueryPlan(newDNF)
    raise UnsafeException("FAIL")


# TODO(ericgribkoff) Should be aware of already-deterministic relations
def findSafeResidualQuery(dnf):
    relations = dnf.getRelations()
    relNames = set()
    for rel in relations:
        relName = rel.getName()
        relNames.add(relName)
    for rels in powerset(relNames):
        if len(rels) == 0:
            continue
        residualDNF = dnf.copyWithDeterminism(set(rels))
        try:
            plan = getSafeQueryPlan(residualDNF)
            sql = plan.generateSQL_DNF()
            relsObjects = []
            relObjectsAdded = {}
            for rel in residualDNF.getRelations():
                relName = rel.getName()
                if relName in rels and relName not in relObjectsAdded:
                    relsObjects.append(rel)
                    relObjectsAdded[relName] = 1
            return (rels, residualDNF, sql, relsObjects)
        except UnsafeException:
            pass
    raise UnsafeException("NO SAFE RESIDUAL QUERY FOUND")


def getPrettySQL(sql):
    return sqlparse.format(sql,  reindent=True, keyword_case='upper')


class UnsafeException(Exception):
    pass


def powerset(iterable):
    "powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"
    s = list(iterable)
    return itertools.chain.from_iterable(
        itertools.combinations(s, r) for r in range(len(s) + 1))


def resetCounters():
    counter.counter = 0
    attCounter.counter = 0


def counter():
    counter.counter += 1
    return counter.counter
counter.counter = 0


def attCounter():
    attCounter.counter += 1
    return attCounter.counter
attCounter.counter = 0
