import algorithm
import itertools


class InclusionExclusion(object):

    def __init__(self, query, subqueries, coeffs, init=True):
        self.query = query
        self.subqueries = subqueries
        self.coeffs = coeffs
        self.genericConstantStr = None

        self.genericIdentifiers = set()
        self.usedSeparatorVars = []
        # True means that missing tuples in the output count as True
        self.trueOnMissing = False

        # this call must be last for initialization purposes
        self.getSafeQueryPlan(init)

    def hasGenericConstant(self):
        return self.genericConstantStr is not None

    def getGenericConstantStr(self):
        return self.genericConstantStr

    def formatSeparatorVariable(self, sep):
        return "sep_var_%s" % str(sep)

    def getSafeQueryPlan(self, init=True):
        self.usedSeparatorVars = self.query.getUsedSeparators()
        self.formattedUsedSeparators = [
            self.formatSeparatorVariable(sep)
            for sep in self.usedSeparatorVars]

        self.children = []
        if init:
            for ind, term in enumerate(self.subqueries):
                plan = algorithm.getSafeQueryPlan(term)
                self.children.append(plan)

    def generateSQL_DNF(self, separatorSubs=None):
        if separatorSubs is None:
            separatorSubs = []
        results = []
        counters = []
        selectAtts = []

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

        if self.hasGenericConstant():
            selectAtts.append(
                "q%d.%s" % (genericConstantStrIdent, self.genericConstantStr))

        subqueryPairs = [pair for pair in itertools.product(
            counters, counters) if pair[0] < pair[1]]

        joinConditions = []
        for (j1, j2) in subqueryPairs:
            if (j1 in counterIdentToGenericConstantStr and
                    j2 in counterIdentToGenericConstantStr):
                joinConditions.append(
                    "q%d.%s = q%d.%s" %
                    (j1, counterIdentToGenericConstantStr[j1],
                     j2, counterIdentToGenericConstantStr[j2]))
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
                         for(i, x) in separatorSubs])
                    subqueries.append(
                        "FULL OUTER JOIN %s %s" % (newSubquery, condition))
                else:
                    subqueries.append(newSubquery)
            else:
                subqueries.append("%s" % (newSubquery))
            previousIdent = ident

        if len(separatorSubs):
            subqueryString = " ".join(subqueries)
        else:
            subqueryString = ", ".join(subqueries)

        pString = ' + '.join(["( -1 * %d * q%d.pUse)" %
                              (self.coeffs[ind],
                               i) for ind, i in enumerate(counters)])

        for (i, x) in separatorSubs:
            selectAtts.append("COALESCE(%s) as c%d" % (
                ", ".join(["q%d.c%d" % (ident, i) for ident in counters]), i))
        attString = ', '.join(selectAtts)

        if attString:
            selectString = '%s, %s as pUse' % (attString, pString)
        else:
            selectString = '%s as pUse' % (pString)

        sql = "\n -- inclusion/exclusion \n select %s from %s %s" % (
            selectString, subqueryString, joinCondition)
        return sql

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
        tableAliasesTrueOnMissing = set()
        tableAliasesFalseOnMissing = set()
        tableAliasToVariablesMap = {}
        variableToTableAliasMap = {}
        restOfTableAliases = set()
        self.genericIdentifiers = set()

        tableAliasToCoeffMap = {}

        # for webkb:
        constantInSelectClause = None

        # assign each child a table alias and fetch its SQL code,
        # then build the maps
        # that say which identifiers/separator vars are used
        # by each child
        for i, child in enumerate(self.children):
            # for webkb:
            if isinstance(child, int):
                constantInSelectClause = child * self.coeffs[i]
                continue

            currentSubqueryID = algorithm.counter()
            subquerySQL = child.generateSQL_CNF(params)
            tableAlias = "q%d" % currentSubqueryID
            tableAliases.append(tableAlias)
            tableAliasToSubquerySQLMap[tableAlias] = subquerySQL
            tableAliasIsTrueOnMissing[tableAlias] = child.trueOnMissing
            if child.trueOnMissing:
                # we are in an or operator (I/E), so if any child is true on
                # missing, missing tuples are true
                self.trueOnMissing = True
                tableAliasesTrueOnMissing.add(tableAlias)
            else:
                tableAliasesFalseOnMissing.add(tableAlias)
            tableAliasToCoeffMap[tableAlias] = self.coeffs[i]

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
                if genericIdentifier in variableToTableAliasMap:
                    variableToTableAliasMap[genericIdentifier].add(tableAlias)
                else:
                    variableToTableAliasMap[
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
                    if formattedSeparator in variableToTableAliasMap:
                        variableToTableAliasMap[
                            formattedSeparator].add(tableAlias)
                    else:
                        variableToTableAliasMap[
                            formattedSeparator] = set([tableAlias])
                else:
                    usesAllSeparators = False
            if usesAllSeparators:
                tableAliasesUsingAllSeparators.add(tableAlias)

            tableAliasToVariablesMap[tableAlias] = \
                tableAliasToUsedSeparatorsMap[tableAlias].\
                union(childGenericIdentifiers)

        if not tableAliasesUsingAllSeparators:
            raise Exception("No subquery containing all separators!")

        for tableAlias in tableAliases:
            tableAliasToMissingGenericIdentifiersMap[tableAlias] = \
                self.genericIdentifiers.difference(
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

        if not tableAliasesUsingAllSeparatorsAndGenericIdentifiers:
            raise Exception(
                "No subquery containing all subqueries and generic identifiers"
            )

        orderedAttributes = []
        for previousSeparatorVariable in self.formattedUsedSeparators:
            orderedAttributes.append(previousSeparatorVariable)
        for genericIdentifier in self.genericIdentifiers:
            orderedAttributes.append(genericIdentifier)
        orderedAttributes.append("pUse")
        orderedAttributes.append("trueOnMissing")

        # use the child subquery sql, except if there are missing
        # generic identifiers:
        # then we need to cross product the child relation with the
        # active domain to fill these
        # in - essentially the difficulty comes from the fact that
        # we are only "pretending" to
        # project out these generic values, so we can't just ignore
        # them as constant as when
        # we have a regular separator variable
        withClauses = []
        for tableAlias in tableAliases:
            if tableAliasToMissingGenericIdentifiersMap[tableAlias]:
                # we need to cross product with the active domain to fill-in
                # the missing generic vars
                aliasForMissingGenericVarsTable = "%s_missing_generic_vars" % (
                    tableAlias)
                withClauses.append(
                    "%s as (%s)" %
                    (aliasForMissingGenericVarsTable,
                     tableAliasToSubquerySQLMap[tableAlias]))
                index = 1
                extraDomainSelectVars = []
                extraDomainTables = []
                for missingGenericVariable in \
                        tableAliasToMissingGenericIdentifiersMap[tableAlias]:
                    extraDomainAlias = "A_%d" % index
                    extraDomainSelectVars.append(
                        "%s.v0 as %s" %
                        (extraDomainAlias, missingGenericVariable))
                    extraDomainTables.append("A %s" % extraDomainAlias)
                    index += 1
                    # now this generic identifier is in the table alias
                    tableAliasToVariablesMap[tableAlias].add(
                        missingGenericVariable)
                    variableToTableAliasMap[
                        missingGenericVariable].add(tableAlias)
                extraDomainSelectClause = "*, %s" % ", ".join(
                    extraDomainSelectVars)
                extraDomainFromClause = "%s, %s" % (
                    aliasForMissingGenericVarsTable, ", ".join(
                        extraDomainTables))
                withClauses.append(
                    "%s as (select %s from %s)" %
                    (tableAlias, extraDomainSelectClause,
                     extraDomainFromClause))
            else:
                withClauses.append(
                    "%s as (%s)" %
                    (tableAlias, tableAliasToSubquerySQLMap[tableAlias]))

        joinSubqueries = []
        previousAliases = []
        # these can be done via an inner join, as any one missing => true
        for tableAlias in tableAliasesTrueOnMissing:
            if not previousAliases:
                joinSubqueries.append(tableAlias)
            else:
                joinConditions = []
                for variable in tableAliasToVariablesMap[tableAlias]:
                    for previousAlias in previousAliases:
                        if variable in tableAliasToVariablesMap[previousAlias]:
                            joinConditions.append(
                                "%s.%s = %s.%s" % (
                                    tableAlias, variable,
                                    previousAlias, variable
                                ))
                            break
                if joinConditions:
                    joinConditionsString = " AND ".join(joinConditions)
                else:
                    joinConditionsString = "TRUE"
                joinSubqueries.append(
                    " INNER JOIN %s ON %s" %
                    (tableAlias, joinConditionsString))
            previousAliases.append(tableAlias)

        if previousAliases:
            joinType = "LEFT OUTER"
        else:
            joinType = "FULL OUTER"

        # these require an outer join, as any missing do not imply true
        for tableAlias in tableAliasesFalseOnMissing:
            # possible there were no tables true on missing, so we may still
            # start here
            if not previousAliases:
                joinSubqueries.append(tableAlias)
            else:
                joinConditions = []
                for variable in tableAliasToVariablesMap[tableAlias]:
                    falseOnMissingJoinAliases = []
                    # if this variable is in a true on missing table, we only
                    # need to join
                    trueOnMissingJoinAlias = None
                    # with this; otherwise, we need to COALESCE()
                    # over all potentialJoinAlias
                    # tables from earlier left outer joins, as
                    # any of these tables may have
                    # had a NULL value
                    for previousAlias in previousAliases:
                        if variable in tableAliasToVariablesMap[previousAlias]:
                            if tableAliasIsTrueOnMissing[previousAlias]:
                                trueOnMissingJoinAlias = previousAlias
                                break
                            else:
                                falseOnMissingJoinAliases.append(previousAlias)
                    if trueOnMissingJoinAlias:
                        joinConditions.append(
                            "%s.%s = %s.%s" %
                            (
                                tableAlias, variable,
                                trueOnMissingJoinAlias, variable
                            ))
                    elif falseOnMissingJoinAliases:
                        falseOnMissingJoinAliasesString = ", ".join(
                            ["%s.%s" % (alias, variable)
                             for alias in falseOnMissingJoinAliases])
                        joinConditions.append(
                            "%s.%s = COALESCE(%s)" %
                            (tableAlias, variable,
                             falseOnMissingJoinAliasesString))
                if joinConditions:
                    joinConditionsString = " AND ".join(joinConditions)
                else:
                    joinConditionsString = "TRUE"
                joinSubqueries.append(
                    " %s JOIN %s ON %s" %
                    (joinType, tableAlias, joinConditionsString))
            previousAliases.append(tableAlias)

        selectVariables = set(self.formattedUsedSeparators).union(
            self.genericIdentifiers)
        selectClause = []
        for variable in selectVariables:
            falseOnMissingTableAliases = []
            # if the variable to select is in at least one true on missing
            # table, we just
            trueOnMissingTableAlias = None
            # arbitrarily select out (as they all must be non-null and equal in
            # any result row)
            for tableAlias in variableToTableAliasMap[variable]:
                if tableAliasIsTrueOnMissing[tableAlias]:
                    trueOnMissingTableAlias = tableAlias
                    break
                else:
                    falseOnMissingTableAliases.append(tableAlias)
            if trueOnMissingTableAlias:
                selectClause.append(
                    "%s.%s" % (trueOnMissingTableAlias, variable))
            else:
                falseOnMissingTableAliasesString = ", ".join(
                    ["%s.%s" % (alias, variable) for alias in
                     falseOnMissingTableAliases])
                selectClause.append(
                    "COALESCE(%s) as %s" %
                    (falseOnMissingTableAliasesString, variable))

        if params['useLog']:
            if params['useNull']:
                pUseTemplate = "(1-exp(%%s.pUse))"
            else:
                pUseTemplate = "CASE WHEN %s.pUse != '-Infinity'" + \
                               "THEN 1-exp(%s.pUse) ELSE 1 END"
        else:
            pUseTemplate = "(1-%%s.pUse)"
        pSelect = []
        pCoeff = []
        for tableAlias in tableAliases:
            pCoeff.append(tableAliasToCoeffMap[tableAlias])
            if params['useLog']:
                if params['useNull']:
                    pSelect.append("COALESCE(exp(%s.pUse), 0)" % tableAlias)
                else:
                    pSelect.append(
                        "COALESCE(CASE WHEN %s.pUse != " +
                        "'-Infinity' THEN exp(%s.pUse) ELSE 0 END, 0)"
                        % (tableAlias, tableAlias))
            else:
                pSelect.append("COALESCE(%s.pUse, 0)" % tableAlias)

        # for webkb
        if constantInSelectClause:
            pUseString = "( %s + %d)" % (' + '.join(
                ["( -1 * %d * %s)" %
                 (pCoeff[i],
                  pSelect[i]) for i in range(
                     len(pSelect))]),
                constantInSelectClause)
        else:
            pUseString = "( %s )" % (
                ' + '.join(["( -1 * %d * %s)" %
                            (pCoeff[i], pSelect[i])
                            for i in range(len(pSelect))]))

        if params['useLog']:
            if params['useNull']:
                selectClause.append(
                    "CASE WHEN %s > 0 THEN ln(%s) ELSE NULL END AS pUse" %
                    (pUseString, pUseString))
            else:
                selectClause.append(
                    "CASE WHEN %s > 0 THEN ln(%s) ELSE '-Infinity' END AS pUse"
                    %
                    (pUseString, pUseString))
        else:
            selectClause.append("%s as pUse" % pUseString)

        fromString = "".join(joinSubqueries)
        selectString = ", ".join(selectClause)
        withString = ",\n".join(withClauses)
        joinSQL = "\n -- inclusion/exclusion \nWITH %s\nselect %s from %s" % (
            withString, selectString, fromString)

        return joinSQL

    def usesSeparator(self, sep):
        return self.query.usesSeparator(sep)

    def buildTree(self, T, parent=None):
        newId = len(T.nodes()) + 1
        T.add_node(newId, label=self.getLabel())
        for (i, n) in enumerate(self.children):
            # for webkb
            if isinstance(n, int):
                if n:
                    T.add_edge(newId, "true", label="%+d" % self.coeffs[i])
                else:
                    T.add_edge(newId, "false", label="%+d" % self.coeffs[i])
            else:
                T.add_edge(newId, n.buildTree(T, self), label="%+d" %
                           self.coeffs[i])
        return newId

    def getLabel(self):
        return "Inclusion/Exclusion\n%s" % self.query.prettyPrintCNF()

    def __repr__(self):
        return "Inclusion/Exclusion: %s" % " + ".join(
            ["%+d * (%s)" % (self.coeffs[i],
                             x.__repr__())
             for(i, x) in enumerate(self.children)])
