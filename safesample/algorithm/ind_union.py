import itertools

import algorithm


class IndependentUnion(object):

    def __init__(self, query, subqueries, init=True):
        self.query = query
        self.subqueries = subqueries
        self.genericConstantStr = None

        self.genericIdentifiers = set()
        self.usedSeparatorVars = []
        # True means that missing tuples in the output count as True
        self.trueOnMissing = False

        # this call must be last for initialization purposes
        self.getSafeQueryPlan(init)

    def getSafeQueryPlan(self, init=True):
        if isinstance(self.query, list):
            self.usedSeparatorVars = set()
            for q in self.query:
                self.usedSeparatorVars.update(q.getUsedSeparators())
        else:
            self.usedSeparatorVars = self.query.getUsedSeparators()
        self.formattedUsedSeparators = [
            self.formatSeparatorVariable(sep) for sep in
            self.usedSeparatorVars]
        if init:
            self.children = map(algorithm.getSafeQueryPlan, self.subqueries)
        else:
            self.children = []

    def hasGenericConstant(self):
        return self.genericConstantStr is not None

    def getGenericConstantStr(self):
        return self.genericConstantStr

    def generateSQL_DNF(self, separatorSubs=None):
        if separatorSubs is None:
            separatorSubs = []
        results = []
        counters = []

        selectAtts = []

        identToTermSubs = {}
        counterIdentToGenericConstantStr = {}
        genericConstantStrIdent = 0

        for (i, child) in enumerate(self.children):
            sql = child.generateSQL_DNF(separatorSubs[:])
            ident = algorithm.counter()
            if child.hasGenericConstant():
                genericConstantStr = child.getGenericConstantStr()
                # doesn't matter which one, just pick arbitrarily
                self.genericConstantStr = genericConstantStr
                counterIdentToGenericConstantStr[ident] = genericConstantStr
                genericConstantStrIdent = ident
            counters.append(ident)
            results.append((sql, ident))
            thisTermSubs = set()
            for (subId, varList) in separatorSubs:
                if child.usesSeparator(subId):
                    thisTermSubs.add(subId)
            identToTermSubs[ident] = thisTermSubs

        if self.hasGenericConstant():
            selectAtts.append(
                "q%d.%s" % (genericConstantStrIdent, self.genericConstantStr))

        subqueryPairs = [pair for pair in itertools.product(
            counters, counters) if pair[0] < pair[1]]

        joinConditions = []
        for (j1, j2) in subqueryPairs:
            if j1 in counterIdentToGenericConstantStr and j2 in counterIdentToGenericConstantStr:
                joinConditions.append(
                    "q%d.%s = q%d.%s" %
                    (j1,
                     counterIdentToGenericConstantStr[j1],
                     j2,
                     counterIdentToGenericConstantStr[j2]))
        if len(joinConditions):
            joinCondition = "where %s" % ' and '.join(joinConditions)
        else:
            joinCondition = ""

        subqueries = []
        previousIdent = False
        for (sql, ident) in results:
            newSubquery = "(%s) as q%d" % (sql, ident)
            if previousIdent:
                if len(separatorSubs):
                    condition = "ON %s" % " and ".join(
                        ["q%d.c%d = q%d.c%d" % (previousIdent, i, ident, i)
                         for(i, x) in separatorSubs
                         if i in identToTermSubs[previousIdent] and i in identToTermSubs
                         [ident]])
                    subqueries.append(
                        "FULL OUTER JOIN %s %s" % (newSubquery, condition))
                else:
                    subqueries.append(
                        "FULL OUTER JOIN %s ON true" % (newSubquery))
            else:
                subqueries.append("%s" % (newSubquery))

            previousIdent = ident

        subqueryString = " ".join(subqueries)

        pString = '*'.join(["COALESCE(1-q%d.pUse,1)" % i for i in counters])

        for (i, x) in separatorSubs:
            attsToCoalesce = ", ".join(
                ["q%d.c%d" % (ident, i) for ident in counters
                 if i in identToTermSubs[previousIdent] and i in identToTermSubs
                 [ident]])
            if len(attsToCoalesce) > 0:
                selectAtts.append("COALESCE(%s) as c%d" % (attsToCoalesce, i))
        attString = ', '.join(selectAtts)

        if attString:
            selectString = '%s, 1-%s as pUse' % (attString, pString)
        else:
            selectString = '1-%s as pUse' % (pString)

        sql = "\n -- independent union \n select %s from %s %s" % (
            selectString, subqueryString, joinCondition)
        return sql

    def formatSeparatorVariable(self, sep):
        return "sep_var_%s" % str(sep)

    # we have an order on attributes to follow, but some will require complex statements such
    # as CASE/WHEN or COALESCE, which are passed in using
    # attributeToFormattedStringMap
    def getOrderedSelectString(
            self,
            orderedAttributes,
            attributeToFormattedStringMap):
        selectAttributes = []
        for attribute in orderedAttributes:
            if attribute in attributeToFormattedStringMap:
                selectAttributes.append(
                    attributeToFormattedStringMap[attribute])
        return ", ".join(selectAttributes)

    def generateSQL_CNF(self, params):
        if params['useLog']:
            if params['useNull']:
                defaultValue = "NULL"
            else:
                defaultValue = "'-Infinity'"
        else:
            defaultValue = "0"

        tableAliases = []
        tableAliasToSubquerySQLMap = {}
        tableAliasToGenericIdentifiersMap = {}
        tableAliasToUsedSeparatorsMap = {}
        genericIdentifierToTableAliasMap = {}
        usedSeparatorToTableAliasMap = {}
        tableAliasesUsingAllSeparators = set()
        tableAliasesUsingAllSeparatorsAndGenericIdentifiers = set()
        tableAliasIsTrueOnMissing = {}
        tableAliasToMissingGenericIdentifiersMap = {}
        tableAliasToMissingSeparatorsMap = {}
        restOfTableAliases = set()
        self.genericIdentifiers = set()

        # if any child is not true on missing, this gets set to False
        self.trueOnMissing = True
        # assign each child a table alias and fetch its SQL code, then build the maps
        # that say which identifiers/separator vars are used by each child
        for child in self.children:
            currentSubqueryID = algorithm.counter()
            subquerySQL = child.generateSQL_CNF(params)
            tableAlias = "q%d" % currentSubqueryID
            tableAliases.append(tableAlias)
            tableAliasToSubquerySQLMap[tableAlias] = subquerySQL
            tableAliasIsTrueOnMissing[tableAlias] = child.trueOnMissing
            if not child.trueOnMissing:
                self.trueOnMissing = False

            childGenericIdentifiers = child.genericIdentifiers.copy()
            tableAliasToGenericIdentifiersMap[
                tableAlias] = childGenericIdentifiers
            self.genericIdentifiers.update(childGenericIdentifiers)

            for genericIdentifier in childGenericIdentifiers:
                if genericIdentifier in genericIdentifierToTableAliasMap:
                    genericIdentifierToTableAliasMap[
                        genericIdentifier].add(tableAlias)
                else:
                    genericIdentifierToTableAliasMap[
                        genericIdentifier] = set([tableAlias])

            usesAllSeparators = True
            tableAliasToUsedSeparatorsMap[tableAlias] = set()
            for usedSeparatorVariable in self.usedSeparatorVars:
                if child.usesSeparator(usedSeparatorVariable):
                    formattedSeparator = self.formatSeparatorVariable(
                        usedSeparatorVariable)
                    tableAliasToUsedSeparatorsMap[
                        tableAlias].add(formattedSeparator)
                    if formattedSeparator in usedSeparatorToTableAliasMap:
                        usedSeparatorToTableAliasMap[
                            formattedSeparator].add(tableAlias)
                    else:
                        usedSeparatorToTableAliasMap[
                            formattedSeparator] = set([tableAlias])
                else:
                    usesAllSeparators = False
            if usesAllSeparators:
                tableAliasesUsingAllSeparators.add(tableAlias)

        for tableAlias in tableAliases:
            tableAliasToMissingGenericIdentifiersMap[tableAlias] = self.genericIdentifiers.difference(
                tableAliasToGenericIdentifiersMap[tableAlias])
            tableAliasToMissingSeparatorsMap[tableAlias] = set(
                self.formattedUsedSeparators).difference(
                tableAliasToUsedSeparatorsMap[tableAlias])
            if tableAliasToMissingGenericIdentifiersMap[tableAlias]:
                restOfTableAliases.add(tableAlias)
            elif tableAlias in tableAliasesUsingAllSeparators:
                tableAliasesUsingAllSeparatorsAndGenericIdentifiers.add(
                    tableAlias)
            else:
                restOfTableAliases.add(tableAlias)

        # need a fixed order for selected attributes, before building the union
        # queries
        orderedAttributes = []
        for previousSeparatorVariable in self.formattedUsedSeparators:
            orderedAttributes.append(previousSeparatorVariable)
        for genericIdentifier in self.genericIdentifiers:
            orderedAttributes.append(genericIdentifier)
        orderedAttributes.append("pUse")
        orderedAttributes.append("trueOnMissing")

        unionSubqueries = []

        selectVariables = set(self.formattedUsedSeparators).union(
            self.genericIdentifiers)

        for tableAlias in tableAliases:
            if tableAlias in tableAliasesUsingAllSeparatorsAndGenericIdentifiers:
                selectAttributeMap = {
                    attribute: "%s.%s" % (tableAlias, attribute)
                    for attribute in selectVariables}
                selectAttributeMap["pUse"] = "%s.pUse" % tableAlias
                selectAttributeMap["trueOnMissing"] = "%s as trueOnMissing" % str(
                    tableAliasIsTrueOnMissing[tableAlias])
                selectAttributeString = self.getOrderedSelectString(
                    orderedAttributes, selectAttributeMap)
                unionSubqueries.append(
                    "SELECT %s FROM %s" % (selectAttributeString, tableAlias))
            else:
                # skip if this tableAlias has no joining variables?
                missingSelectVariables = tableAliasToMissingGenericIdentifiersMap[
                    tableAlias].union(tableAliasToMissingSeparatorsMap[tableAlias])
                selectAttributeMap = {}
                additionalTables = []
                index = 0
                for attribute in selectVariables:
                    if attribute in missingSelectVariables:
                        domainTable = "A%d" % index
                        additionalTables.append("A %s" % domainTable)
                        selectAttributeMap[attribute] = "%s.v0 as %s" % (
                            domainTable, attribute)
                        index += 1
                    else:
                        selectAttributeMap[attribute] = "%s.%s" % (
                            tableAlias, attribute)
                selectAttributeMap["pUse"] = "%s.pUse" % tableAlias
                selectAttributeMap["trueOnMissing"] = "%s as trueOnMissing" % str(
                    tableAliasIsTrueOnMissing[tableAlias])
                selectAttributeString = self.getOrderedSelectString(
                    orderedAttributes, selectAttributeMap)
                additionalTablesString = ", ".join(additionalTables)
                unionSubqueries.append("SELECT %s FROM %s, %s" % (
                    selectAttributeString, tableAlias, additionalTablesString))
        selectAttributeMap = {attribute: "%s" %
                              (attribute) for attribute in selectVariables}
        numberOfChildrenFalseOnMissing = len(
            self.children) - sum(tableAliasIsTrueOnMissing.values())
        if params['useLog']:
            if params['useNull']:
                selectAttributeMap[
                    "pUse"] = "iunion_log_null_%d_false_on_missing(pUse, trueOnMissing) as pUse" % numberOfChildrenFalseOnMissing
            else:
                selectAttributeMap[
                    "pUse"] = "iunion_log_neginf_%d_false_on_missing(pUse, trueOnMissing) as pUse" % numberOfChildrenFalseOnMissing
        else:
            selectAttributeMap[
                "pUse"] = "iunion_%d_false_on_missing(pUse, trueOnMissing) as pUse" % numberOfChildrenFalseOnMissing
        selectClause = self.getOrderedSelectString(
            orderedAttributes, selectAttributeMap)

        groupByAttributeMap = {attribute: "%s" %
                               (attribute) for attribute in selectVariables}
        if groupByAttributeMap:
            groupByClause = "GROUP BY %s" % self.getOrderedSelectString(
                orderedAttributes, groupByAttributeMap)
        else:
            groupByClause = ""

        withClause = ",\n".join(
            ["%s as (%s)" %
             (tableAlias, tableAliasToSubquerySQLMap[tableAlias])
             for tableAlias in tableAliases])

        unionClause = " UNION ALL ".join(unionSubqueries)
        unionClauseAlias = "q%d" % algorithm.counter()
        joinSQL = "\n -- independent union \n WITH %s select %s from (%s) %s %s" % (
            withClause, selectClause, unionClause, unionClauseAlias, groupByClause)

        return joinSQL

    def usesSeparator(self, sep):
        return self.query.usesSeparator(sep)

    def buildTree(self, T, parent=None):
        newId = len(T.nodes()) + 1
        T.add_node(newId, label=self.getLabel())
        for n in self.children:
            T.add_edge(newId, n.buildTree(T, self))
        return newId

    def getLabel(self):
        # TODO(ericgribkoff) make the join/union distinction for CNF versus DNF
        # more clear
        return "Independent Join\n%s" % self.query.prettyPrintCNF()

    def __repr__(self):
        return "Independent Union (true on missing = %s): %s" % (
            self.trueOnMissing, ", ".join(
                [x.__repr__() for x in self.children]))
