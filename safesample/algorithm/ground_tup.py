import algorithm


class GroundTuple(object):
    # ground tuples are leaf nodes
    nodes = []

    def __init__(self, query, disjunctiveQuery, groundTuple, init=True):
        self.query = query
        self.disjunctiveQuery = disjunctiveQuery
        self.groundTuple = groundTuple
        self.genericConstantStr = None
        self.isSampled = False

        self.genericIdentifiers = set()
        # True means that missing tuples in the output count as True
        self.trueOnMissing = False

        if init:
            # this call must be last for initialization purposes
            self.getSafeQueryPlan()

    def getSafeQueryPlan(self):
        pass

    def hasGenericConstant(self):
        return self.genericConstantStr is not None

    def getGenericConstantStr(self):
        return self.genericConstantStr

    def generateSQL_DNF(self, separatorSubs=None):
        if separatorSubs is None:
            separatorSubs = []
        rel = self.disjunctiveQuery.getComponents()[0].getRelations()[0]
        signature = rel.getSignature()
        relSym = rel.getName()

        if len(self.disjunctiveQuery.getComponents()) > 1:
            # the component must equal x v ~x
            alwaysTrue = True
        else:
            alwaysTrue = False

        if rel.isSampled():
            pColumn = "p"
            self.isSampled = True
        else:
            pColumn = "p"

        if rel.isNegated():
            pColumn = "(1 - %s)" % pColumn

        if alwaysTrue:
            pColumn = "1"

        selectAttributes = []
        relArgs = rel.getArguments()

        if rel.getConstraints():
            # may have some equality constraints and some variable arguments
            # (None or not equals x)
            tablePos = 0
            argPos = 0
            for constant in rel.getConstraints():
                if (not constant or
                        (type(constant) == int and constant < 0)
                        or constant == '-c'):
                    selectAttributes.append(
                        "%s.v%d as c%d" %
                        (relSym, tablePos, relArgs[argPos].getReplacement()))
                    argPos += 1
                tablePos += 1
        else:
            for i in range(len(relArgs)):
                if rel.isVariable(i):
                    raise Exception("A ground tuple can't have variables!")
                elif rel.isConstant(i):
                    raise Exception("A ground tuple can't have constants!")
                else:
                    selectAttributes.append(
                        "%s.v%d as c%d" %
                        (relSym, i, relArgs[i].getReplacement()))

        whereConditions = []
        extraSelectAttribute = ""
        whereExtraTableStr = ""
        for i, constant in enumerate(rel.getConstraints()):
            if constant == 'c':
                extraSelectAttribute = "A.v0 as cTemplate"
                self.genericConstantStr = "cTemplate"
                whereExtraTableStr = ", A"
                # necessary for S[c,-c](x), e.g.
                whereConditions.append("%s.v%d = A.v0" % (relSym, i))
            elif constant == '-c':
                extraSelectAttribute = "A.v0 as cTemplate"
                self.genericConstantStr = "cTemplate"
                whereExtraTableStr = ", A"
                whereConditions.append("%s.v%d != A.v0" % (relSym, i))
            elif not constant:
                continue
            elif constant > 0:
                whereConditions.append("%s.v%d = %d" % (relSym, i, constant))
            else:
                whereConditions.append(
                    "%s.v%d != %d" % (relSym, i, -1 * constant))

        if len(extraSelectAttribute):
            selectAttributes.append(extraSelectAttribute)

        if len(whereConditions):
            whereClause = ' where ' + (' and ' . join(whereConditions))
        else:
            whereClause = ''

        # no variables in original atom, just constants w/ equality
        if rel.isSampled() and not len(relArgs):
            selectClauseBase = "%s as pUse" % pColumn
            if len(selectAttributes):
                selectClause = "%s, %s" % (
                    ', '.join(selectAttributes), selectClauseBase)
            else:
                selectClause = selectClauseBase
        else:
            if len(selectAttributes):
                selectClause = "%s, %s as pUse" % (
                    ', '.join(selectAttributes), pColumn)
            else:
                selectClause = "%s as pUse" % pColumn

        sql = "\n -- ground tuple \n select %s from %s %s %s" % \
            (selectClause, relSym, whereExtraTableStr, whereClause)
        return sql

    # depending on parameters, the generated SQL may denote 0 with NULL
    # or -Infinity
    def getZeroGivenParams(self, params):
        if params['useLog']:
            if params['useNull']:
                return "NULL"
            else:
                return "'-Infinity'"
        else:
            return "0"

    def getOneGivenParams(self, params):
        if params['useLog']:
            return "0"  # logarithm of one is zero
        else:
            return "1"

    def generateSQL_CNF(self, params):
        rel = self.disjunctiveQuery.getComponents()[0].getRelations()[0]
        signature = rel.getSignature()

        # we are looking at the dual CNF formula, so flip negation
        positiveAtom = rel.isNegated()

        if not positiveAtom:
            self.trueOnMissing = True

        if len(self.disjunctiveQuery.getComponents()) > 1:
            # the component must equal x v ~x, and is therefore always true
            if positiveAtom:
                pColumn = self.getOneGivenParams(params)
            else:
                pColumn = self.getZeroGivenParams(params)
        else:
            if rel.isSampled():
                if params['missingTuples']:
                    pColumn = "pSample"
                    relSym = "%sNot" % rel.getName()
                else:
                    pColumn = "p"
                    relSym = rel.getName()
            else:
                pColumn = "p"
                relSym = rel.getName()

            if not positiveAtom:
                pColumn = "1-%s" % pColumn

            if params['useLog']:
                pColumn = "CASE WHEN %s > 0 THEN ln(%s) ELSE %s END" % (
                    pColumn, pColumn, self.getZeroGivenParams(params))

        # build up the SELECT part of the query
        selectAttributes = []
        # some or all of the arguments of the relation have (in)equality
        # constraints
        if rel.getConstraints():
            argumentIndex = 0
            for tableColumn, constraint in enumerate(rel.getConstraints()):
                # if it is a non-generic equality constraint, e.g., =5,
                # don't include in select clause otherwise, include it here
                if constraint.isWildcard() or constraint.isInequality():
                    selectAttributes.append("%s.v%d as sep_var_%s" % (
                        relSym, tableColumn,
                        str(
                            rel.getArguments()[argumentIndex].getReplacement()
                        )))
                    argumentIndex += 1
                elif constraint.isEquality() and constraint.isGeneric():
                    genericConstantsStr = "sep_var_generic_%s" % (
                        constraint.getConstant())
                    self.genericIdentifiers.add(genericConstantsStr)
                    selectAttributes.append(
                        "%s.v%d as %s" %
                        (relSym, tableColumn, genericConstantsStr))
        else:  # no constraints, just variables (now separator variables)
            for i in range(len(rel.getArguments())):
                if rel.isVariable(i):
                    raise Exception("A ground tuple can't have variables!")
                elif rel.isConstant(i):
                    raise Exception("A ground tuple can't have constants!")
                else:
                    selectAttributes.append("%s.v%d as sep_var_%s" % (
                        relSym, i,
                        str(rel.getArguments()[i].getReplacement())))
        selectAttributes.append("%s as pUse" % pColumn)
        selectClause = ', '.join(selectAttributes)

        # build up the WHERE part of the query
        whereConditions = []
        for tableColumn, constraint in enumerate(rel.getConstraints()):
            if constraint.isEquality() and not constraint.isGeneric():
                whereConditions.append(
                    "%s.v%d = %d" %
                    (relSym, tableColumn, constraint.getConstant()))
            elif constraint.isInequality() and not constraint.isGeneric():
                whereConditions.append(
                    "%s.v%d != %d" %
                    (relSym, tableColumn, constraint.getConstant()))
        if len(whereConditions):
            whereClause = 'where ' + (' and ' . join(whereConditions))
        else:
            whereClause = ''

        sql = "\n -- ground tuple \n select %s from %s %s" % \
            (selectClause, relSym, whereClause)
        return sql

    def usesSeparator(self, sep):
        rel = self.disjunctiveQuery.getComponents()[0].getRelations()[0]
        return rel.usesSeparator(sep)

    def buildTree(self, T, parent=None):
        newId = len(T.nodes()) + 1
        T.add_node(newId, label=self.getLabel())
        return newId

    def getLabel(self):
        return self.__repr__()

    def __repr__(self):
        return "Ground Tuple: %s" % (self.groundTuple)
