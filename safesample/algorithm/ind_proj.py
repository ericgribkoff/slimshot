import algorithm
import query_exp


class IndependentProject(object):

    def __init__(self, query, disjunctiveQuery, separator, init=True):
        self.query = query.copy()
        self.disjunctiveQuery = disjunctiveQuery
        self.separator = separator
        self.genericConstantStr = None

        self.genericIdentifiers = set()
        self.usedSeparatorVars = []
        # True means that missing tuples in the output count as True
        self.trueOnMissing = False

        # for webkb
        self.effectiveDomainSize = 0

        # this call must be last for initialization purposes
        self.getSafeQueryPlan(init)

    def hasGenericConstant(self):
        return self.genericConstantStr is not None

    def getGenericConstantStr(self):
        return self.genericConstantStr

    def getSafeQueryPlan(self, init=True):
        # we are interested in whether the separator represents
        # a generic inequality constraint - if so, it doesn't matter which
        # component it occurs in, as it must have the same
        # constraint everywhere

        representativeSeparator = self.separator[0]
        if representativeSeparator.isInequality(
        ) and representativeSeparator.getInequalityConstraint().isGeneric():
            self.replacementVal = "generic_%s" % representativeSeparator.getInequalityConstraint(
            ).getConstant()
        else:
            self.replacementVal = algorithm.attCounter()

        # for webkb
        if representativeSeparator.domainSize:
            self.effectiveDomainSize = representativeSeparator.domainSize

        d = self.disjunctiveQuery

        self.usedSeparatorVars = d.getUsedSeparators()

        d.applySeparator(self.separator, self.replacementVal)
        if isinstance(d, query_exp.DisjunctiveQuery):
            cons = []
            for c in d.getComponents():
                cons.append(
                    query_exp.ConjunctiveQuery(
                        query_exp.decomposeComponent(c)))
            self.childDNF = query_exp.DNF(cons)
        else:
            self.childDNF = d

        if init:
            self.child = algorithm.getSafeQueryPlan(self.childDNF)
        else:
            self.child = None

    def generateSQL_DNF(self, separatorSubs=None):
        if separatorSubs is None:
            separatorSubs = []
        replacementVal = algorithm.attCounter()

        groupBy = ["c%d" % i for (i, x) in separatorSubs]
        if len(groupBy):
            groupByString = 'group by ' + ', '.join(groupBy)
        else:
            groupByString = ''
        selectString = ', '.join(groupBy + ['ior(COALESCE(pUse,0))'])
        separatorSubs.append((self.replacementVal, self.separator))

        childSQL = self.child.generateSQL_DNF(separatorSubs[:])
        sql = "\n -- independent project \n select %s as pUse from (%s) as q%d %s " % (
            selectString, childSQL, algorithm.counter(), groupByString)

        if self.child.hasGenericConstant():
            genericConstantStr = self.child.getGenericConstantStr()
            self.genericConstantStr = genericConstantStr
            groupBy.append(genericConstantStr)
            groupByString = 'group by ' + ', '.join(groupBy)
            sql = "\n -- independent project \n select %s, %s as pUse from (%s) as q%d %s " % (
                genericConstantStr, selectString, childSQL, algorithm.counter(), groupByString)
        else:
            sql = "\n -- independent project \n select %s as pUse from (%s) as q%d %s " % (
                selectString, childSQL, algorithm.counter(), groupByString)

        return sql

    def isInequalityVar(self, separatorVar):
        return separatorVar[0].isInequality()

    def isGenericInequalityVar(self, separatorVar):
        return self.isInequalityVar(separatorVar) and self.separator[
            0].getInequalityConstraint().isGeneric()

    def generateSQL_CNF(self, params):
        replacementVal = algorithm.attCounter()

        childSQL = self.child.generateSQL_CNF(params)
        self.trueOnMissing = self.child.trueOnMissing

        self.genericIdentifiers = self.child.genericIdentifiers.copy()
        subqueryAlias = 'q%d' % algorithm.counter()

        # this steps replaces a universally (\forall) quantified variable
        # with a product - if some tuples can be missing, we need to count
        # and invalidate any products with too few terms (missing terms =
        # false terms)
        if params['missingTuples']:

            # for webkb
            if self.effectiveDomainSize:
                effectiveDomainSize = self.effectiveDomainSize
            else:
                effectiveDomainSize = params['domainSize']
            if self.isInequalityVar(self.separator):
                effectiveDomainSize = effectiveDomainSize - 1

        groupByAttributes = []
        selectAttributes = []
        joinClause = ''

        # take care of generic constants, which have been projected out but
        # must still be "bubbled up" to the previous level
        for genericIdentifier in self.genericIdentifiers:
            groupByAttributes.append(genericIdentifier)
            selectAttributes.append(genericIdentifier)

        if self.isGenericInequalityVar(self.separator):
            genericConstantIdentifier = "sep_var_%s" % str(self.replacementVal)
            selectAttributes.append('A.v0 as %s' % genericConstantIdentifier)
            joinClause = ', A WHERE A.v0 != %s.%s' % (
                subqueryAlias, genericConstantIdentifier)
            groupByAttributes.append('A.v0')
            self.genericIdentifiers.add(genericConstantIdentifier)

        for storedReplacementVal in self.usedSeparatorVars:
            selectAttributes.append("sep_var_%s" % str(storedReplacementVal))
            groupByAttributes.append("sep_var_%s" % str(storedReplacementVal))

        if len(groupByAttributes):
            groupByClause = 'group by ' + (', ' . join(groupByAttributes))
        else:
            groupByClause = ''

        havingClause = ''
        if params['useLog']:
            if self.trueOnMissing:
                if params['useNull']:
                    selectAttributes.append(
                        'CASE WHEN COUNT(*) = COUNT(pUse) THEN SUM(pUse) ELSE NULL END AS pUse')
                    # if the result is empty and trueOnMissing=True, we should
                    # return empty set (true)
                    havingClause = ' HAVING COUNT(*) > 0'
                else:
                    selectAttributes.append('SUM(pUse) AS pUse')
            else:
                if params['useNull']:
                    if params['missingTuples']:
                        selectAttributes.append(
                            'CASE WHEN COUNT(*) = COUNT(pUse) and COUNT(*) = %d THEN SUM(pUse) ELSE NULL END AS pUse' %
                            effectiveDomainSize)
                    else:
                        selectAttributes.append(
                            'CASE WHEN COUNT(*) = COUNT(pUse) THEN SUM(pUse) ELSE NULL END AS pUse')
                else:
                    if params['missingTuples']:
                        selectAttributes.append(
                            "CASE WHEN COUNT(*) = %d THEN SUM(pUse) ELSE '-Infinity' END AS pUse" %
                            effectiveDomainSize)
                    else:
                        selectAttributes.append('SUM(pUse) AS pUse')
        else:
            if not self.trueOnMissing and params['missingTuples']:
                selectAttributes.append(
                    "CASE WHEN COUNT(*) = %d THEN prod_double(pUse) ELSE 0 END AS pUse" %
                    effectiveDomainSize)
            else:
                selectAttributes.append('prod_double(pUse) AS pUse')
        selectClause = ', '.join(selectAttributes)

        sql = "\n -- independent project \n select %s from (%s) as %s%s %s %s" % (
            selectClause, childSQL, subqueryAlias, joinClause, groupByClause, havingClause)
        return sql

    def usesSeparator(self, sep):
        return self.query.usesSeparator(sep)

    def buildTree(self, T, parent=None):
        newId = len(T.nodes()) + 1
        T.add_node(newId, label=self.getLabel())
        T.add_edge(newId, self.child.buildTree(T, self))
        return newId

    def getLabel(self):
        separatorStrs = map(lambda x: x.getVar(), self.separator)
        return "Independent Project: %s\n%s" % (
            ', '.join(separatorStrs),
            self.query.prettyPrintCNF())

    def __repr__(self):
        return "Independent Project (true on missing = %s): %s" % (
            self.trueOnMissing, self.child.__repr__())
