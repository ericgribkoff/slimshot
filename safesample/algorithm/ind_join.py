import algorithm


class IndependentJoin(object):

    def __init__(self, query, subqueries, init=True):
        self.query = query
        self.subqueries = subqueries
        self.genericConstantStr = None
        self.genericConstantStrs = []

        self.genericIdentifiers = set()
        self.usedSeparatorVars = []
        self.formattedUsedSeparators = []
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
            self.formatSeparatorVariable(sep) for sep in self.usedSeparatorVars
        ]

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

        selectAttributes = []

        counters = []
        counterIdentToRelations = {}
        counterIdentToGenericConstantStr = {}
        genericConstantStrIdent = 0
        identOfSampledRelation = -1
        for (i, child) in enumerate(self.children):
            subquerySQL = child.generateSQL_DNF(separatorSubs[:])
            ident = algorithm.counter()
            if child.hasGenericConstant():
                if hasattr(child, 'isSampled'):
                    identOfSampledRelation = ident
                genericConstantStr = child.getGenericConstantStr()
                # doesn't matter which one, just pick arbitrarily
                self.genericConstantStr = genericConstantStr
                self.genericConstantStrs.append(
                    "q%d.%s" % (ident, genericConstantStr))
                counterIdentToGenericConstantStr[ident] = genericConstantStr
                genericConstantStrIdent = ident
            counters.append(ident)
            results.append((subquerySQL, ident))
            counterIdentToRelations[ident] = self.subqueries[i].getRelations()

        if self.hasGenericConstant():
            selectAttributes.append(
                "q%d.%s" % (genericConstantStrIdent, self.genericConstantStr))

        subqueries = []
        previousIdent = False
        for (sql, ident) in results:
            newSubquery = "(%s) as q%d" % (sql, ident)
            if previousIdent:
                joinType = "INNER JOIN"
                if len(separatorSubs):
                    if ident in counterIdentToGenericConstantStr:
                        conditions = []
                        for prevIdent in range(ident):
                            if prevIdent in counterIdentToGenericConstantStr:
                                conditions.append(
                                    "q%d.%s = q%d.%s" %
                                    (ident,
                                     counterIdentToGenericConstantStr[ident],
                                     prevIdent,
                                     counterIdentToGenericConstantStr[prevIdent
                                                                      ]))
                            conditions += ["q%d.c%d = q%d.c%d" %
                                           (prevIdent, i, ident, i)
                                           for (i, x) in separatorSubs
                                           if self.separatorInRelation1And2(
                                               i, prevIdent, ident,
                                               counterIdentToRelations)]
                        condition = "ON %s" % " and ".join(conditions)
                        subqueries.append(
                            "%s %s %s" % (joinType, newSubquery, condition))
                    else:
                        conditions = []
                        for prevIdent in range(ident):
                            conditions += ["q%d.c%d = q%d.c%d" %
                                           (prevIdent, i, ident, i)
                                           for (i, x) in separatorSubs
                                           if self.separatorInRelation1And2(
                                               i, prevIdent, ident,
                                               counterIdentToRelations)]
                        condition = "ON %s" % " and ".join(conditions)
                        subqueries.append(
                            "%s %s %s" % (joinType, newSubquery, condition))

                else:
                    if ident in counterIdentToGenericConstantStr:
                        conditions = []
                        for prevIdent in range(ident):
                            if prevIdent in counterIdentToGenericConstantStr:
                                conditions.append(
                                    "q%d.%s = q%d.%s" %
                                    (ident,
                                     counterIdentToGenericConstantStr[ident],
                                     prevIdent,
                                     counterIdentToGenericConstantStr[prevIdent
                                                                      ]))
                        condition = "ON %s" % " and ".join(conditions)
                        subqueries.append(
                            "%s %s %s" % (joinType, newSubquery, condition))
                    else:
                        subqueries.append(
                            "%s %s ON TRUE" % (joinType, newSubquery))

            else:
                subqueries.append("%s" % (newSubquery))
            previousIdent = ident

        for (separatorReplacement, separatorVarsByComponent) in separatorSubs:
            termIdentWithThisSubstitution = -1
            for i in counters:
                separatorInI = False
                for rel in counterIdentToRelations[i]:
                    if separatorReplacement in rel.getSeparatorReplacementValues(
                    ):
                        separatorInI = True
                if separatorInI:
                    termIdentWithThisSubstitution = i
                    break
            selectAttributes.append(
                "q%d.c%d" %
                (termIdentWithThisSubstitution, separatorReplacement))

        pString = '*'.join(["q%d.pUse" % i for i in counters])
        attString = ', '.join(selectAttributes)
        if attString:
            selectString = '%s, %s' % (attString, pString)
        else:
            selectString = pString
        sql = "\n -- independent join \n select %s as pUse from %s" % (
            selectString, " ".join(subqueries))
        return sql

    def formatSeparatorVariable(self, sep):
        return "sep_var_%s" % str(sep)

    # we have an order on attributes to follow, but some will require complex statements such
    # as CASE/WHEN or COALESCE, which are passed in using
    # attributeToFormattedStringMap
    def getOrderedSelectString(
            self, orderedAttributes, attributeToFormattedStringMap):
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
        tableAliasesTrueOnMissing = set()
        tableAliasesFalseOnMissing = set()
        tableAliasToVariablesMap = {}
        variableToTableAliasMap = {}
        restOfTableAliases = set()
        self.genericIdentifiers = set()

        # assign each child a table alias and fetch its SQL code, then build the maps
        # that say which identifiers/separator vars are used by each child
        for child in self.children:
            currentSubqueryID = algorithm.counter()
            subquerySQL = child.generateSQL_CNF(params)
            tableAlias = "q%d" % currentSubqueryID
            tableAliases.append(tableAlias)
            tableAliasToSubquerySQLMap[tableAlias] = subquerySQL
            tableAliasIsTrueOnMissing[tableAlias] = child.trueOnMissing
            if child.trueOnMissing:
                # we are in an or operator, so if any child is true on missing,
                # missing tuples are true
                self.trueOnMissing = True
                tableAliasesTrueOnMissing.add(tableAlias)
            else:
                tableAliasesFalseOnMissing.add(tableAlias)

            childGenericIdentifiers = child.genericIdentifiers.copy()
            tableAliasToGenericIdentifiersMap[
                tableAlias
            ] = childGenericIdentifiers
            self.genericIdentifiers.update(childGenericIdentifiers)

            for genericIdentifier in childGenericIdentifiers:
                if genericIdentifier in genericIdentifierToTableAliasMap:
                    genericIdentifierToTableAliasMap[
                        genericIdentifier].add(tableAlias)
                else:
                    genericIdentifierToTableAliasMap[
                        genericIdentifier
                    ] = set([tableAlias])
                if genericIdentifier in variableToTableAliasMap:
                    variableToTableAliasMap[genericIdentifier].add(tableAlias)
                else:
                    variableToTableAliasMap[
                        genericIdentifier
                    ] = set([tableAlias])

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
                            formattedSeparator
                        ] = set([tableAlias])
                    if formattedSeparator in variableToTableAliasMap:
                        variableToTableAliasMap[
                            formattedSeparator].add(tableAlias)
                    else:
                        variableToTableAliasMap[
                            formattedSeparator
                        ] = set([tableAlias])
                else:
                    usesAllSeparators = False
            if usesAllSeparators:
                tableAliasesUsingAllSeparators.add(tableAlias)

            tableAliasToVariablesMap[tableAlias] = tableAliasToUsedSeparatorsMap[
                tableAlias].union(childGenericIdentifiers)

        if not tableAliasesUsingAllSeparators:
            raise Exception("No subquery containing all separators!")

        for tableAlias in tableAliases:
            tableAliasToMissingGenericIdentifiersMap[
                tableAlias
            ] = self.genericIdentifiers.difference(
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
                "No subquery containing all subqueries and generic identifiers!")

        # need a fixed order for selected attributes, before building the union
        # queries
        orderedAttributes = []
        for previousSeparatorVariable in self.formattedUsedSeparators:
            orderedAttributes.append(previousSeparatorVariable)
        for genericIdentifier in self.genericIdentifiers:
            orderedAttributes.append(genericIdentifier)
        orderedAttributes.append("pUse")
        orderedAttributes.append("trueOnMissing")

        # use the child subquery sql, except if there are missing generic identifiers:
        # then we need to cross product the child relation with the active domain to fill these
        # in - essentially the difficulty comes from the fact that we are only "pretending" to
        # project out these generic values, so we can't just ignore them as constant as when
        # we have a regular separator variable
        withClauses = []
        for tableAlias in tableAliases:
            if tableAliasToMissingGenericIdentifiersMap[tableAlias]:
                # we need to cross product with the active domain to fill-in
                # the missing generic vars
                aliasForMissingGenericVarsTable = "%s_missing_generic_vars" % tableAlias
                withClauses.append(
                    "%s as (%s)" % (aliasForMissingGenericVarsTable,
                                    tableAliasToSubquerySQLMap[tableAlias]))
                index = 1
                extraDomainSelectVars = []
                extraDomainTables = []
                for missingGenericVariable in tableAliasToMissingGenericIdentifiersMap[
                    tableAlias
                ]:
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
                    "%s as (select %s from %s)" % (tableAlias,
                                                   extraDomainSelectClause,
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
                                "%s.%s = %s.%s" % (tableAlias, variable,
                                                   previousAlias, variable))
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
                    # need to join with this; otherwise, we need to COALESCE() over all potentialJoinAlias
                    # tables from earlier left outer joins, as any of these tables may have
                    # had a NULL value
                    trueOnMissingJoinAlias = None
                    for previousAlias in previousAliases:
                        if variable in tableAliasToVariablesMap[previousAlias]:
                            if tableAliasIsTrueOnMissing[previousAlias]:
                                trueOnMissingJoinAlias = previousAlias
                                break
                            else:
                                falseOnMissingJoinAliases.append(previousAlias)
                    if trueOnMissingJoinAlias:
                        joinConditions.append(
                            "%s.%s = %s.%s" % (tableAlias, variable,
                                               trueOnMissingJoinAlias, variable
                                               ))
                    elif falseOnMissingJoinAliases:
                        falseOnMissingJoinAliasesString = ", ".join(
                            ["%s.%s" % (alias, variable)
                             for alias in falseOnMissingJoinAliases])
                        joinConditions.append(
                            "%s.%s = COALESCE(%s)" % (
                                tableAlias, variable,
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
            # table, we just arbitrarily select one (as they all must be non-null and equal in
            # any result row)
            trueOnMissingTableAlias = None
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
                    ["%s.%s" % (alias, variable)
                     for alias in falseOnMissingTableAliases])
                selectClause.append(
                    "COALESCE(%s) as %s" %
                    (falseOnMissingTableAliasesString, variable))

        if params['useLog']:
            if params['useNull']:
                pUseTemplate = "(1-exp(%%s.pUse))"
            else:
                pUseTemplate = "CASE WHEN %s.pUse != '-Infinity' THEN 1-exp(%s.pUse) ELSE 1 END"
        else:
            pUseTemplate = "(1-%%s.pUse)"
        pSelect = []
        for tableAlias in tableAliases:
            if params['useLog']:
                if params['useNull']:
                    pSelect.append("COALESCE(1-exp(%s.pUse), 1)" % tableAlias)
                else:
                    pSelect.append(
                        "COALESCE(CASE WHEN %s.pUse != '-Infinity' THEN 1-exp(%s.pUse) ELSE 1 END, 1)" %
                        (tableAlias, tableAlias))
            else:
                pSelect.append("COALESCE(1-%s.pUse, 1)" % tableAlias)
        pUseString = "1 - ( %s )" % (' * '.join(pSelect))
        if params['useLog']:
            if params['useNull']:
                selectClause.append(
                    "CASE WHEN %s > 0 THEN ln(%s) ELSE NULL END AS pUse" %
                    (pUseString, pUseString))
            else:
                selectClause.append(
                    "CASE WHEN %s > 0 THEN ln(%s) ELSE '-Infinity' END AS pUse"
                    % (pUseString, pUseString))
        else:
            selectClause.append("%s as pUse" % pUseString)

        fromString = "".join(joinSubqueries)
        selectString = ", ".join(selectClause)
        withString = ",\n".join(withClauses)
        joinSQL = "\n -- independent join \nWITH %s\nselect %s from %s" % (
            withString, selectString, fromString)

        return joinSQL

    def separatorInRelation1And2(
            self, sepId, rel1Id, rel2Id, counterIdentToRelations):
        separatorInR1 = False
        if rel1Id not in counterIdentToRelations or rel2Id not in counterIdentToRelations:
            return False
        for rel in counterIdentToRelations[rel1Id]:
            if sepId in rel.getSeparatorReplacementValues():
                separatorInR1 = True
        separatorInR2 = False
        for rel in counterIdentToRelations[rel2Id]:
            if sepId in rel.getSeparatorReplacementValues():
                separatorInR2 = True
        return separatorInR1 and separatorInR2

    def usesSeparator(self, sep):
        return self.query.usesSeparator(sep)

    def buildTree(self, T, parent=None):
        newId = len(T.nodes()) + 1
        T.add_node(newId, label=self.getLabel())
        for n in self.children:
            T.add_edge(newId, n.buildTree(T, self))
        return newId

    def getLabel(self):
        return "Independent Union\n%s" % self.query.prettyPrintCNF()

    def __repr__(self):
        return "Independent Join (true on missing = %s): %s " % (
            self.trueOnMissing, ", ".join(
                [x.__repr__() for x in self.children]))
