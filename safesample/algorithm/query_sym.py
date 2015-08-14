class Variable(object):

    def __init__(self, var, inequality=None):
        self.var = var
        self.inequalityConstraint = inequality

        # for webkb
        self.domainSize = 0

    def __eq__(self, other):
        return self.var == other.var

    def __hash__(self):
        return hash(self.var)

    def __repr__(self):
        # for webkb
        if self.domainSize:
            selfString = "%s (domain: %d)" % (self.var, self.domainSize)
        else:
            selfString = self.var
        if self.inequalityConstraint:
            return "%s (!= constraint)" % selfString
        else:
            return selfString

    def getVar(self):
        return self.var

    def setInequality(self, inequality):
        self.inequalityConstraint = inequality

    def isInequality(self):
        return self.inequalityConstraint is not None

    def getInequalityConstraint(self):
        return self.inequalityConstraint

    # for webkb
    def setDomainSize(self, size):
        self.domainSize = size


class Constant(object):

    def __init__(self, constant):
        self.constant = constant

    def getConstant(self):
        return self.constant


class Constraint(object):

    def __init__(self, constant):
        self.originalConstant = constant

        self.wildcard = False
        self.inequality = False
        self.equality = False
        self.generic = False

        if constant == '*':
            self.wildcard = True
            self.constant = None
        elif constant.isalpha():
            self.generic = True
            self.equality = True
            self.constant = constant
        elif constant[0] == '-' and constant[1:].isalpha():
            self.generic = True
            self.inequality = True
            self.constant = constant[1:]
        elif constant[0] == '-' and constant[1:].isdigit():
            self.inequality = True
            self.constant = int(constant[1:])
        elif constant.isdigit():
            self.equality = True
            self.constant = int(constant)
        else:
            raise Exception('Invalid constraint')

    def getOriginalConstant(self):
        return self.getOriginalConstant

    def getConstant(self):
        return self.constant

    def isWildcard(self):
        return self.wildcard

    def isGeneric(self):
        return self.generic

    def isEquality(self):
        return self.equality

    def isInequality(self):
        return self.inequality

    def __repr__(self):
        return self.getStringFormat()

    def getStringFormat(self):
        if self.wildcard:
            return "*"
        elif self.inequality:
            return 'not%s' % str(self.constant)
        else:
            return str(self.constant)

    def getProver9Format(self):
        if self.generic:
            if self.equality:
                return self.constant.upper()
            else:
                return 'not%s' % self.constant
        elif self.wildcard:
            return 'any'
        else:
            if self.equality:
                return str(self.constant)
            else:
                return 'not%d' % (self.constant)


class SeparatorVariable(object):

    def __init__(self, separator, replacement=''):
        self.separator = separator
        self.replacementConstant = replacement

    def getSeparator(self):
        return self.separator

    def getReplacement(self):
        return self.replacementConstant

    def __repr__(self):
        return "SeparatorVariable: separator: %s replacement constant: %s)" % (
            self.separator, self.replacementConstant)


class Relation(object):

    def __init__(
            self,
            name='rel',
            arguments=[],
            signature=[],
            constraints=[],
            deterministic=False,
            sampled=False,
            negated=False):
        self.name = name
        self.arguments = arguments
        self.signature = signature
        self.constraints = constraints

        # map from variable positions to table columns (used with S[1,*](y) to
        # know that y points to the second column of the S table
        if self.constraints:
            self.tableCol = []
            nextCol = 0
            for i, constant in enumerate(self.constraints):
                if not constant or constant < 0:
                    self.tableCol.append(nextCol)
                nextCol += 1
        else:
            self.tableCol = range(len(self.arguments))
        self.deterministic = deterministic
        self.sampled = sampled
        self.negated = negated

    def copy(self):
        return Relation(
            self.name,
            self.arguments[:],
            self.signature[:],
            self.constraints[:],
            self.deterministic,
            self.sampled,
            self.negated)

    def getName(self):
        return self.name

    def getArguments(self):
        return self.arguments

    def getTableColumn(self, argPosition):
        return self.tableCol[argPosition]

    def getSignature(self):
        return self.signature

    def getConstants(self):
        return filter(lambda x: isinstance(x, Constant), self.arguments)

    def getSeparatorReplacements(self):
        return filter(
            lambda x: isinstance(
                x,
                SeparatorVariable),
            self.arguments)

    def getConstraints(self):
        return self.constraints

    def hasConstants(self):
        return any(isinstance(x, Constant) for x in self.arguments)

    def isDeterministic(self):
        return self.deterministic

    def isNegated(self):
        return self.negated

    def isSampled(self):
        return self.sampled

    def getVariables(self):
        return filter(lambda x: isinstance(x, Variable), self.arguments)

    def getVariablesForHomomorphism(self):
        varsForH = []
        for a in self.arguments:
            if isinstance(a, Variable):
                varsForH.append(a.getVar())
            elif isinstance(a, Constant):
                varsForH.append('_c' + a.getConstant())
            elif isinstance(a, SeparatorVariable):
                varsForH.append("_s" + str(a.getReplacement()))
            else:
                varsForH.append("%" + str(a))
        return varsForH

    def getVariablePositions(self):
        self.positions = {}
        for pos, x in enumerate(self.arguments):
            if not isinstance(x, Variable):
                continue
            if x in self.positions:
                self.positions[x].add(pos)
            else:
                self.positions[x] = set([pos])
        return self.positions

    def applySeparator(self, separator, separatorReplacement):
        for i in range(len(self.arguments)):
            if isinstance(
                    self.arguments[i],
                    Variable) and \
                    self.arguments[i].getVar() == separator.getVar():
                self.arguments[i] = SeparatorVariable(
                    separator, separatorReplacement)

    def hasVariables(self):
        return len(self.getVariables()) > 0

    def usesSeparator(self, subId):
        retVal = False
        for a in self.arguments:
            if isinstance(
                    a,
                    SeparatorVariable) and a.getReplacement() == subId:
                retVal = True
                break
        return retVal

    def getUsedSeparators(self):
        seps = set()
        for a in self.arguments:
            if isinstance(a, SeparatorVariable):
                seps.add(a.getReplacement())
        return seps

    def applyH(self, h):
        for (ind, arg) in enumerate(self.arguments):
            if isinstance(arg, Variable) and arg in h:
                self.arguments[ind] = h[arg]

    def isVariable(self, ind):
        return isinstance(self.arguments[ind], Variable)

    def isConstant(self, ind):
        return isinstance(self.arguments[ind], Constant)

    def isSeparatorReplacement(self, ind):
        return isinstance(self.arguments[ind], SeparatorVariable)

    def getSeparatorReplacementValues(self):
        return map(
            lambda x: x.getReplacement(),
            self.getSeparatorReplacements())

    def getConstraintsString(self):
        constantRep = map(formatEqualityConstraints, self.constraints)
        return "[%s]" % ','.join(constantRep)

    def getConstraintsStringProver9(self):
        constantRep = map(formatEqualityConstraintsProver9, self.constraints)
        return ''.join(constantRep)

    def getRelationNameForAdjacency(self):
        if self.constraints:
            return "%s[%s]" % (self.name, self.getConstraintsString())
        else:
            return self.name

    def getNameWithEqualityConstraints(self):
        if self.constraints:
            pred = "%s[%s]" % (self.name, self.getConstraintsString())
        else:
            pred = self.name

        if self.negated:
            pred = '~' + pred

        return pred

    def toProver9(self):
        if self.negated:
            stringRep = '!' + self.name
        else:
            stringRep = self.name
        argumentRep = []
        constantRep = []
        for i in range(len(self.arguments)):
            if self.isVariable(i):
                argumentRep.append(self.arguments[i].getVar())
            elif self.isConstant(i):
                argumentRep.append(str(self.arguments[i].getConstant()))
            elif self.isSeparatorReplacement(i):
                argumentRep.append(
                    "_" + str(self.arguments[i].getReplacement()))
            else:
                argumentRep.append("%" + str(self.arguments[i]))
        if not argumentRep:
            argumentRep = self.getConstraintsStringProver9()
        else:
            argumentRep = ','.join(argumentRep)
        if len(self.constraints):
            constantString = self.getConstraintsStringProver9()
        else:
            constantString = ""
        return "%s%s(%s)" % (stringRep, constantString, argumentRep)

    def __repr__(self):
        stringRep = self.name
        if self.deterministic:
            stringRep = stringRep + '_d'
        if self.negated:
            stringRep = '~' + stringRep
        argumentRep = []
        constantRep = []
        for i in range(len(self.arguments)):
            if self.isVariable(i):
                argumentRep.append(str(self.arguments[i]))
            elif self.isConstant(i):
                argumentRep.append("_c" + str(self.arguments[i].getConstant()))
            elif self.isSeparatorReplacement(i):
                argumentRep.append(
                    "_s" + str(self.arguments[i].getReplacement()))
            else:
                argumentRep.append("%" + str(self.arguments[i]))
        if len(self.constraints):
            constantString = self.getConstraintsString()
        else:
            constantString = ""
        return "%s%s(%s)" % (stringRep, constantString, ','.join(argumentRep))


def formatEqualityConstraints(eq):
    if isinstance(eq, Constraint):
        return eq.getStringFormat()
    elif eq:
        return str(eq)
    else:
        return '*'


def formatEqualityConstraintsProver9(eq):
    if isinstance(eq, Constraint):
        return eq.getProver9Format()
    elif eq == 'c':
        return 'C'
    elif eq == '-c':
        return 'notC'
    elif eq and eq > 0:
        return str(eq)
    elif eq and eq < 0:
        return "not" + str(-1 * eq)
    else:
        return 'any'
