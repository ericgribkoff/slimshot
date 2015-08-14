# These classes represent the query expressions from section 2.6 of the paper
# Dichotomy of Probabilistic Inference for Unions of Conjunctive Queries
# by Dalvi, Suciu 2012

from collections import defaultdict
import itertools
import nltk

import algorithm


class Graph(object):

    def __init__(self, adjacencyList={}):
        self.adjacencyList = adjacencyList

    def connectedComponents(self):
        vertices = self.adjacencyList.keys()
        explored = set()
        components = []
        for v in vertices:
            if v not in explored:
                explored.add(v)
                component = set([v])
                neighbors = set(self.adjacencyList[v])
                [component.add(n) for n in self.adjacencyList[v]]
                while neighbors:
                    next = neighbors.pop()
                    if next not in explored:
                        explored.add(next)
                        [neighbors.add(n) for n in self.adjacencyList[next]]
                        [component.add(n) for n in self.adjacencyList[next]]
                components.append(component)
        return components


# Connected conjunctive query


class Component(object):

    def __init__(self, relations=[]):
        self.relations = relations

    def copy(self):
        return Component([r.copy() for r in self.getRelations()])

    def copyWithDeterminism(self, relsToMakeDeterministic):
        newRelations = []
        for r in self.relations:
            newRel = r.copy()
            relName = r.getName()
            if relName in relsToMakeDeterministic:
                newRel.deterministic = True
                newRel.sampled = True
            newRelations.append(newRel)
        return Component(newRelations)

    def getRelations(self):
        return self.relations

    def getProbabilisticRelations(self):
        return filter(lambda x: not x.isDeterministic(), self.relations)

    def getDeterministicRelations(self):
        return filter(lambda x: x.isDeterministic(), self.relations)

    def getProbabilisticRelationSymbols(self):
        return map(
            lambda x: x.getName(),
            filter(
                lambda x: not x.isDeterministic(),
                self.relations))

    def getRelationSymbols(self):
        return [rel.getName() for rel in self.getRelations()]

    def hasNegatedRelations(self):
        return any([rel.isNegated() for rel in self.getRelations()])

    def getVariables(self):
        return set([x for rel in self.relations for x in rel.getVariables()])
    # Returns a dictionary: {Var : { RelName : set([varPos1, [varPos2, ...]])
    # }}

    def hasVariables(self):
        return len(self.getVariables()) > 0

    def getVarPositions(self):
        varsToPositions = {}
        for rel in self.relations:
            if rel.hasVariables():
                varPos = rel.getVariablePositions()
                for var in varPos:
                    if var in varsToPositions:
                        varsToPositions[var][rel] = varPos[var]
                    else:
                        varsToPositions[var] = {rel: varPos[var]}
        return varsToPositions

    def containedIn(self, com2):
        # TODO(ericgribkoff) Implement minimization for queries with
        # negation
        c1Vars = self.getVariables()
        c2Vars = com2.getVariables()
        byVarMaps = []
        for var in c2Vars:
            byVarMaps.append(
                [pair for pair in itertools.product([var], c1Vars)])
        mappings = [h for h in itertools.product(*byVarMaps)]
        for mapping in mappings:
            h = dict((x, y) for x, y in list(mapping))
            if self.isHomomorphism(com2.applyH(h)):
                return True
        return False

    def applyH(self, h):
        mappedRels = []
        for rel in self.relations:
            newRel = rel.copy()
            newRel.applyH(h)
            mappedRels.append(newRel)
        return Component(mappedRels)

    def isHomomorphism(self, com2):
        relDict = {}
        for rel in self.getRelations():
            relStr = "%s:%s" % (
                rel.getNameWithEqualityConstraints(),
                ','.join(rel.getVariablesForHomomorphism()))
            relDict[relStr] = True
        for rel in com2.getRelations():
            relStr = "%s:%s" % (
                rel.getNameWithEqualityConstraints(),
                ','.join(rel.getVariablesForHomomorphism()))
            if relStr not in relDict:
                return False
        return True

    def minimize(self):
        for x in algorithm.powerset(self.getRelations()):
            if len(x) and not len(x) == len(self.getRelations()):
                c = Component(list(x))
                if c.containedIn(self) and self.containedIn(c):
                    return c
        return self.copy()

    def usesSeparator(self, subId):
        return any(r.usesSeparator(subId) for r in self.getRelations())

    def getUsedSeparators(self):
        seps = set()
        for r in self.getRelations():
            seps.update(r.getUsedSeparators())
        return seps

    def applySeparator(self, separator, replacement):
        for rel in self.relations:
            rel.applySeparator(separator, replacement)

    def hasRelation(self, rel):
        return rel.getName() in [r.getName() for r in self.relations]

    def isSuperset(self, c):
        return all([c.hasRelation(rel) for rel in self.relations])

    def getAdjacencyList(self):
        varsToRels = defaultdict(set)
        adjList = defaultdict(set)
        for rel in self.relations:
            if rel.hasVariables():
                [varsToRels[var].add(rel) for var in rel.getVariables()]
            else:
                # add any relations without vars as singleton components
                adjList[rel].add(rel)
        for var in varsToRels.keys():
            [adjList[rel1].add(rel2) for rel1 in varsToRels[var]
             for rel2 in varsToRels[var]]
        return adjList

    def quantifiersProver9(self, formula):
        quantifiedFormula = []
        for v in self.getVariables():
            quantifiedFormula.append('exists %s.(' % v.getVar())
        quantifiedFormula.append(formula)
        quantifiedFormula.append(')' * len(self.getVariables()))
        return ''.join(quantifiedFormula)

    def toProver9(self):
        return self.quantifiersProver9(" and ".join(
            ["(%s)" % x.toProver9()
             for x in self.relations]))

    def prettyPrint(self):
        return "%s" % ", ".join([x.__repr__() for x in self.relations])

    def prettyPrintCNF(self):
        return "%s" % " v ".join([x.__repr__() for x in self.relations])

    def __repr__(self):
        return "(%s)" % ", ".join([x.__repr__() for x in self.relations])


# Conjunction of components
class ConjunctiveQuery(object):

    def __init__(self, components=[]):
        self.components = components

    def copy(self):
        return ConjunctiveQuery([c.copy() for c in self.components])

    def copyWithDeterminism(self, relsToMakeDeterministic):
        return ConjunctiveQuery(
            [c.copyWithDeterminism(relsToMakeDeterministic)
             for c in self.components])

    def getComponents(self):
        return self.components

    def getComponent(self, index):
        return self.components[index]

    def getRelations(self):
        return [rel for c in self.components for rel in c.getRelations()]

    def getRelationSymbols(self):
        return [rel.getName() for rel in self.getRelations()]

    def getVariables(self):
        vars = set()
        for rel in self.getRelations():
            vars.update(set(rel.getVariables()))
        return vars

    def hasVariables(self):
        return len(self.getVariables()) > 0

    def usesSeparator(self, subId):
        return any(c.usesSeparator(subId) for c in self.components)

    def getUsedSeparators(self):
        seps = set()
        for c in self.components:
            seps.update(c.getUsedSeparators())
        return seps

    def applySeparator(self, separator, replacement):
        componentsWithVars = [c for c in self.components if c.hasVariables()]
        for i in range(len(componentsWithVars)):
            componentsWithVars[i].applySeparator(separator[i], replacement)

    def getSeparator(self):
        componentsWithVars = [c for c in self.components if c.hasVariables()]
        varPositions = [c.getVarPositions() for c in componentsWithVars]
        componentVars = [c.keys()
                         for c in varPositions]  # used to fix an ordering
        for potentialSep in itertools.product(*componentVars):
            potentialMap = {}
            validMap = True
            for ind, var in enumerate(potentialSep):
                relationsWithThisVarInThisComponent = set(
                    varPositions[ind][var].keys())
                probabilisticRelationsInThisComponent = set(
                    componentsWithVars[ind].getProbabilisticRelations())
                if (len(probabilisticRelationsInThisComponent.difference(
                        relationsWithThisVarInThisComponent))):
                    validMap = False
                    break

                deterministicRelationsInThisComponent = set(
                    self.components[ind].getDeterministicRelations())
                for detR in deterministicRelationsInThisComponent.difference(
                        relationsWithThisVarInThisComponent):
                    if detR.getName() in potentialMap:
                        del potentialMap[detR.getName()]

                # look at all relations in the component with this variable
                for rel in varPositions[ind][var]:
                    if rel.getName() not in potentialMap:
                        # haven't seen this relation before, add it to potential separator
                        # mapping
                        potentialMap[
                            rel.getName()] = varPositions[ind][var][rel]
                    # we have seen this relation before, see if the potential separator
                    # positions intersect with those seen before
                    elif len(potentialMap[rel.getName()].intersection(varPositions[ind][var][rel])) == 0:
                        if not rel.isDeterministic():
                            validMap = False
                            break
                        elif rel.getName() in potentialMap:
                            del potentialMap[rel.getName()]
                    else:
                        potentialMap[
                            rel.getName()] = potentialMap[
                            rel.getName()].intersection(
                            varPositions[ind][var][rel])
                if not validMap:
                    break
            if validMap:
                return potentialSep

    def minimize(self):
        minCom = [c.minimize() for c in self.getComponents()]
        redundant = [False] * len(minCom)
        for i in range(len(minCom)):
            for j in range(len(minCom)):
                if i == j or redundant[i]:
                    continue
                else:
                    if minCom[i].containedIn(minCom[j]):
                        redundant[j] = True
        finalCom = []
        for i in range(len(minCom)):
            if not redundant[i]:
                finalCom.append(minCom[i])
        return ConjunctiveQuery(finalCom)

    def containedIn(self, con2):
        for com in con2.getComponents():
            if not any([c.containedIn(com) for c in self.getComponents()]):
                return False
        return True

    def toProver9(self):
        return " and ".join(["(%s)" % x.toProver9() for x in self.components])

    def prettyPrint(self):
        return "(%s)" % " ^ ".join([x.prettyPrint() for x in self.components])

    def prettyPrintCNF(self):
        return "(%s)" % " v ".join(
            [x.prettyPrintCNF() for x in self.components])

    def __repr__(self):
        return "c(%s)" % " ^ ".join([x.__repr__() for x in self.components])

# Disjunction of components


class DisjunctiveQuery(object):

    def __init__(self, components=[]):
        self.components = components

    def copy(self):
        return DisjunctiveQuery([c.copy() for c in self.components])

    def getComponents(self):
        return self.components

    def getRelations(self):
        return [rel for c in self.components for rel in c.getRelations()]

    def getRelationSymbols(self):
        return [rel.getName() for rel in self.getRelations()]

    def hasVariables(self):
        return any([len(c.getVariables()) > 0 for c in self.components])

    def containedIn(self, dis2):
        for com in self.getComponents():
            # forall i, does there exist a j s.t. c_i => c_j
            if not any([com.containedIn(c) for c in dis2.getComponents()]):
                return False
        return True

    def minimize(self):
        minCom = [c.minimize() for c in self.getComponents()]
        redundant = [False] * len(minCom)
        for i in range(len(minCom)):
            for j in range(len(minCom)):
                if i == j or redundant[j]:
                    continue
                else:
                    if minCom[i].containedIn(minCom[j]):
                        redundant[i] = True
        finalCom = []
        for i in range(len(minCom)):
            if not redundant[i]:
                finalCom.append(minCom[i])
        return DisjunctiveQuery(finalCom)

    def usesSeparator(self, subId):
        return any(c.usesSeparator(subId) for c in self.components)

    def getUsedSeparators(self):
        seps = set()
        for c in self.components:
            seps.update(c.getUsedSeparators())
        return seps

    def applySeparator(self, separator, replacement):
        componentsWithVars = [c for c in self.components if c.hasVariables()]
        for i in range(len(componentsWithVars)):
            componentsWithVars[i].applySeparator(separator[i], replacement)

    # TODO this function and getAdjacencyList should be using
    # getNameWithEqualityConstraints()
    def getSeparator(self):
        componentsWithVars = [c for c in self.components if c.hasVariables()]
        varPositions = [c.getVarPositions() for c in componentsWithVars]
        componentVars = [c.keys()
                         for c in varPositions]  # used to fix an ordering
        for potentialSep in itertools.product(*componentVars):
            potentialMap = {}
            validMap = True
            for ind, var in enumerate(potentialSep):
                relationsWithThisVarInThisComponent = set(
                    varPositions[ind][var].keys())
                probabilisticRelationsInThisComponent = set(
                    componentsWithVars[ind].getProbabilisticRelations())
                if (len(probabilisticRelationsInThisComponent.difference(
                        relationsWithThisVarInThisComponent))):
                    validMap = False
                    break

                deterministicRelationsInThisComponent = set(
                    self.components[ind].getDeterministicRelations())
                for detR in deterministicRelationsInThisComponent.difference(
                        relationsWithThisVarInThisComponent):
                    if detR.getName() in potentialMap:
                        del potentialMap[detR.getName()]

                # look at all relations in the component with this variable
                for rel in varPositions[ind][var]:
                    if rel.getName() not in potentialMap:
                        # haven't seen this relation before, add it to potential separator
                        # mapping
                        potentialMap[
                            rel.getName()] = varPositions[ind][var][rel]
                    # we have seen this relation before, see if the potential separator
                    # positions intersect with those seen before
                    elif len(potentialMap[rel.getName()].intersection(varPositions[ind][var][rel])) == 0:
                        if not rel.isDeterministic():
                            validMap = False
                            break
                        elif rel.getName() in potentialMap:
                            del potentialMap[rel.getName()]
                    else:
                        potentialMap[
                            rel.getName()] = potentialMap[
                            rel.getName()].intersection(
                            varPositions[ind][var][rel])
                if not validMap:
                    break
            if validMap:
                return potentialSep

    # TODO(ericgribkoff) using getNameWithEqualityConstraints() for adjacencyList computation is not
    # sufficient, as components are independent iff their equality constraints don't overlap
    # although, depending on how "complete" the shattering is, and if only one set of constants
    # were introduced with equality, this might be sufficient
    def getAdjacencyList(self):
        relsToComponents = defaultdict(set)
        adjList = defaultdict(set)
        for c in self.components:
            if all(r.isDeterministic() for r in c.getRelations()):
                pass
            else:
                [relsToComponents[rel.getRelationNameForAdjacency()].add(c)
                 for rel in c.getRelations() if not rel.isDeterministic()]
        for rel in relsToComponents.keys():
            [adjList[c1].add(c2) for c1 in relsToComponents[rel]
             for c2 in relsToComponents[rel]]
        # TODO(ericgribkoff) Fix this hack
        for c in self.components:
            if c not in adjList:
                adjList[c].add(c)
        return adjList

    def toProver9(self):
        return " or ".join(["(%s)" % x.toProver9() for x in self.components])

    def prettyPrint(self):
        return "(%s)" % " v ".join([x.prettyPrint() for x in self.components])

    def prettyPrintCNF(self):
        return "(%s)" % " ^ ".join(
            [x.prettyPrintCNF() for x in self.components])

    def __repr__(self):
        return "d(\n%s)" % " v \n".join(
            [x.__repr__() for x in self.components])

# Disjunction of conjuctive queries


class DNF(object):

    def __init__(self, conjuncts=[]):
        self.conjuncts = conjuncts

    def copy(self):
        return DNF([c.copy() for c in self.conjuncts])

    def copyWithDeterminism(self, relsToMakeDeterministic):
        return DNF(
            [c.copyWithDeterminism(relsToMakeDeterministic)
             for c in self.conjuncts])

    def containedIn(self, dnf2):
        for con in self.getConjuncts():
            if not any([c.containedIn(con) for c in dnf2.getConjuncts()]):
                return False
        return True

    def getUsedSeparators(self):
        seps = set()
        for c in self.conjuncts:
            seps.update(c.getUsedSeparators())
        return seps

    def applySeparator(self, separator, replacement):
        for c in self.conjuncts:
            c.applySeparator(separator, replacement)

    def getConjuncts(self):
        return self.conjuncts

    def getRelations(self):
        rels = set()
        for d in self.conjuncts:
            rels.update(set(d.getRelations()))
        return rels

    def getRelationSymbols(self):
        rels = set()
        for d in self.conjuncts:
            rels.update(set(d.getRelationSymbols()))
        return rels

    def minimize(self):
        minCom = [c.minimize() for c in self.getConjuncts()]
        redundant = [False] * len(minCom)
        for i in range(len(minCom)):
            for j in range(len(minCom)):
                if i == j or redundant[j]:
                    continue
                else:
                    if minCom[i].containedIn(minCom[j]):
                        redundant[i] = True
        finalCom = []
        for i in range(len(minCom)):
            if not redundant[i]:
                finalCom.append(minCom[i])
        return DNF(finalCom)

    def getAdjacencyList(self):

        relsToConjuncts = defaultdict(set)
        adjList = defaultdict(set)
        for d in self.conjuncts:
            # don't include deterministic relations without vars
            if all(r.isDeterministic() for r in d.getRelations()):
                pass
            else:
                [relsToConjuncts[rel.getRelationNameForAdjacency()].add(d)
                 for rel in d.getRelations()]
        for rel in relsToConjuncts.keys():
            [adjList[d1].add(d2) for d1 in relsToConjuncts[rel]
             for d2 in relsToConjuncts[rel]]
        # TODO(ericgribkoff) Fix this hack
        for d in self.conjuncts:
            if d not in adjList:
                adjList[d].add(d)
        return adjList

    def toCNF(self):
        conjI = 0
        comI = 0
        stack = [(conjI, comI)]
        disjuncts = []
        # Applying distributivity
        while True:
            if len(stack) < len(self.conjuncts):
                stack.append((conjI + 1, 0))
                conjI = conjI + 1
            else:
                disjuncts.append(
                    DisjunctiveQuery(
                        [self.conjuncts[i].getComponent(j) for(i, j) in
                         stack]))
                (lastConj, lastCom) = stack.pop()
                if lastCom + 1 < len(self.conjuncts[lastConj].getComponents()):
                    stack.append((lastConj, lastCom + 1))
                else:
                    while stack:
                        (lastConj, lastCom) = stack.pop()
                        conjI = conjI - 1
                        if lastCom + 1 < len(
                                self.conjuncts[lastConj].getComponents()):
                            stack.append((lastConj, lastCom + 1))
                            break
                    if not stack:
                        break
        return CNF(disjuncts)

    def prettyPrint(self):
        return "(%s)" % " v ".join([x.prettyPrint() for x in self.conjuncts])

    def prettyPrintCNF(self):
        return "(%s)" % " ^ ".join(
            [x.prettyPrintCNF() for x in self.conjuncts])

    def __repr__(self):
        return "dnf(\n%s\n)" % "\n v ".join(
            [x.__repr__() for x in self.conjuncts])

# Conjunction of disjunctive queries


class CNF(object):

    def __init__(self, disjuncts=[]):
        self.disjuncts = [d.minimize() for d in disjuncts]

    def copy(self):
        return CNF([d.copy() for d in self.disjuncts])

    def getDisjuncts(self):
        return self.disjuncts

    def getRelations(self):
        rels = set()
        for d in self.disjuncts:
            rels.update(set(d.getRelations()))
        return rels

    def getRelationSymbols(self):
        rels = set()
        for d in self.disjuncts:
            rels.update(set(d.getRelationSymbols()))
        return rels

    def minimize(self):

        minCom = [c.minimize() for c in self.getDisjuncts()]

        redundant = [False] * len(minCom)
        for i in range(len(minCom)):
            for j in range(len(minCom)):
                if i == j or redundant[i]:
                    continue
                else:
                    if minCom[i].containedIn(minCom[j]):
                        redundant[j] = True

        lexpr = nltk.Expression.fromstring

        finalCom = []
        for i in range(len(minCom)):
            if not redundant[i]:
                p9Component = lexpr(minCom[i].toProver9())
                prover = nltk.Prover9Command(p9Component)
                if not prover.prove():  # component is not always true
                    finalCom.append(minCom[i])
        return CNF(finalCom)

    def containedIn(self, cnf2):
        for con in cnf2.getDisjuncts():
            if not any([c.containedIn(con) for c in self.getDisjuncts()]):
                return False
        return True

    def usesSeparator(self, subId):
        return any(d.usesSeparator(subId) for d in self.disjuncts)

    def getUsedSeparators(self):
        seps = set()
        for d in self.disjuncts:
            seps.update(d.getUsedSeparators())
        return seps

    def getAdjacencyList(self):

        relsToDisjuncts = defaultdict(set)
        adjList = defaultdict(set)
        for d in self.disjuncts:
            # don't include deterministic relations without vars
            if all(r.isDeterministic() for r in d.getRelations()):
                pass
            else:
                [relsToDisjuncts[rel.getRelationNameForAdjacency()].add(d)
                 for rel in d.getRelations()]
        for rel in relsToDisjuncts.keys():
            [adjList[d1].add(d2) for d1 in relsToDisjuncts[rel]
             for d2 in relsToDisjuncts[rel]]
        # TODO(ericgribkoff) Fix this hack
        for d in self.disjuncts:
            if d not in adjList:
                adjList[d].add(d)
        return adjList

    def toProver9(self):
        return " and ".join(["(%s)" % x.toProver9() for x in self.disjuncts])

    def prettyPrint(self):
        return "(%s)" % " ^ ".join([x.prettyPrint() for x in self.disjuncts])

    def prettyPrintCNF(self):
        return "(%s)" % " v ".join(
            [x.prettyPrintCNF() for x in self.disjuncts])

    def __repr__(self):
        return "cnf(\n%s\n)" % " ^ \n".join(
            [x.__repr__() for x in self.disjuncts])


def decomposeComponent(orig):
    connectedComponents = Graph(orig.getAdjacencyList()).connectedComponents()
    if len(connectedComponents) == 1:
        return [orig]
    else:
        return [Component(list(c)) for c in connectedComponents]


def computeSymbolComponentsDNF(dnf):
    connectedComponents = Graph(dnf.getAdjacencyList()).connectedComponents()
    return connectedComponents


def computeSymbolComponentsCNF(cnf):
    connectedComponents = Graph(cnf.getAdjacencyList()).connectedComponents()
    return connectedComponents


def computeSymbolComponentsDisjunct(d):
    connectedComponents = Graph(d.getAdjacencyList()).connectedComponents()
    return connectedComponents
