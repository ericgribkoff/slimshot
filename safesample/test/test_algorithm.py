from safesample.algorithm import algorithm, query_exp, query_sym

def test_answer():
    R1 = query_sym.Relation('R', [query_sym.Variable('x1')])
    S1 = query_sym.Relation('S', [query_sym.Variable('x1'), query_sym.Variable('y1')])
    S2 = query_sym.Relation('S', [query_sym.Variable('x2'), query_sym.Variable('y2')])
    com1 = query_exp.Component([R1,S1])
    com2 = query_exp.Component([S2])
    assert com1.containedIn(com2) == True

def test_answer2():
    R1 = query_sym.Relation('R', [query_sym.Variable('x'), query_sym.Variable('y')])
    R2 = query_sym.Relation('R', [query_sym.Variable('y'), query_sym.Variable('z')])
    R3 = query_sym.Relation('R', [query_sym.Variable('u'), query_sym.Variable('v')])
    R4 = query_sym.Relation('R', [query_sym.Variable('w'), query_sym.Variable('t')])
    com1 = query_exp.Component([R1,R2])
    com2 = query_exp.Component([R3,R4])
    assert com1.containedIn(com2) == True

def test_answer3():
    R1 = query_sym.Relation('R', [query_sym.Variable('x'), query_sym.Variable('y')])
    R2 = query_sym.Relation('R', [query_sym.Variable('y'), query_sym.Variable('z')])
    R3 = query_sym.Relation('R', [query_sym.Variable('u'), query_sym.Variable('v')])
    R4 = query_sym.Relation('R', [query_sym.Variable('w'), query_sym.Variable('t')])
    com1 = query_exp.Component([R1,R2])
    com2 = query_exp.Component([R3,R4])
    assert com2.containedIn(com1) == False

def test_conj_containment():
    R = query_sym.Relation('R', [query_sym.Variable('x'), query_sym.Variable('y')])
    S = query_sym.Relation('S', [query_sym.Variable('y'), query_sym.Variable('z')])
    T = query_sym.Relation('T', [query_sym.Variable('z'), query_sym.Variable('w')])
    com1 = query_exp.Component([R,S])
    com2 = query_exp.Component([S,T])
    c1 = query_exp.ConjunctiveQuery(query_exp.decomposeComponent(com1) + query_exp.decomposeComponent(com2))
    c2 = query_exp.ConjunctiveQuery(query_exp.decomposeComponent(com2))
    assert c1.containedIn(c2) == True

def test_conj_containment2():
    R = query_sym.Relation('R', [query_sym.Variable('x'), query_sym.Variable('y')])
    S = query_sym.Relation('S', [query_sym.Variable('y'), query_sym.Variable('z')])
    T = query_sym.Relation('T', [query_sym.Variable('z'), query_sym.Variable('w')])
    com1 = query_exp.Component([R,S])
    com2 = query_exp.Component([S,T])
    c1 = query_exp.ConjunctiveQuery(query_exp.decomposeComponent(com1) + query_exp.decomposeComponent(com2))
    c2 = query_exp.ConjunctiveQuery(query_exp.decomposeComponent(com2))
    assert c2.containedIn(c1) == False

def test_disj_containment():
    R = query_sym.Relation('R', [query_sym.Variable('x'), query_sym.Variable('y')])
    S = query_sym.Relation('S', [query_sym.Variable('y'), query_sym.Variable('z')])
    T = query_sym.Relation('T', [query_sym.Variable('z'), query_sym.Variable('w')])
    com1 = query_exp.Component([R,S])
    com2 = query_exp.Component([S,T])
    d1 = query_exp.DisjunctiveQuery([com1, com2])
    d2 = query_exp.DisjunctiveQuery([com2])
    assert d1.containedIn(d2) == False

def test_disj_containment2():
    R = query_sym.Relation('R', [query_sym.Variable('x'), query_sym.Variable('y')])
    S = query_sym.Relation('S', [query_sym.Variable('y'), query_sym.Variable('z')])
    T = query_sym.Relation('T', [query_sym.Variable('z'), query_sym.Variable('w')])
    com1 = query_exp.Component([R,S])
    com2 = query_exp.Component([S,T])
    d1 = query_exp.DisjunctiveQuery([com1, com2])
    d2 = query_exp.DisjunctiveQuery([com2])
    assert d2.containedIn(d1) == True

def test_disj_containment3():
    S2 = query_sym.Relation('S2', [query_sym.Variable('x'), '_'])
    S3 = query_sym.Relation('S3', [query_sym.Variable('x'), '_'])
    T = query_sym.Relation('T', [query_sym.Variable('_')])
    com1 = query_exp.Component([S2,S3])
    com2 = query_exp.Component([T])
    com3 = query_exp.Component([S3])
    d1 = query_exp.DisjunctiveQuery([com1, com2])
    d2 = query_exp.DisjunctiveQuery([com3])
    assert d2.containedIn(d1) == False
    assert d1.containedIn(d2) == False

def test_dnf_containment():
    R = query_sym.Relation('R', [query_sym.Variable('x'), query_sym.Variable('y')])
    S = query_sym.Relation('S', [query_sym.Variable('y'), query_sym.Variable('z')])
    T = query_sym.Relation('T', [query_sym.Variable('z'), query_sym.Variable('w')])
    com1 = query_exp.Component([R])
    com2 = query_exp.Component([S])
    com3 = query_exp.Component([T])
    c1 = query_exp.ConjunctiveQuery(query_exp.decomposeComponent(com1))
    c2 = query_exp.ConjunctiveQuery(query_exp.decomposeComponent(com2))
    c3 = query_exp.ConjunctiveQuery(query_exp.decomposeComponent(com3))
    query_exp.DNF1 = query_exp.DNF([c1,c2,c3])
    query_exp.DNF2 = query_exp.DNF([c1,c2])
    assert query_exp.DNF1.containedIn(query_exp.DNF2) == False

def test_dnf_containment2():
    R = query_sym.Relation('R', [query_sym.Variable('x'), query_sym.Variable('y')])
    S = query_sym.Relation('S', [query_sym.Variable('y'), query_sym.Variable('z')])
    T = query_sym.Relation('T', [query_sym.Variable('z'), query_sym.Variable('w')])
    com1 = query_exp.Component([R])
    com2 = query_exp.Component([S])
    com3 = query_exp.Component([T])
    c1 = query_exp.ConjunctiveQuery(query_exp.decomposeComponent(com1))
    c2 = query_exp.ConjunctiveQuery(query_exp.decomposeComponent(com2))
    c3 = query_exp.ConjunctiveQuery(query_exp.decomposeComponent(com3))
    query_exp.DNF1 = query_exp.DNF([c1,c2,c3])
    query_exp.DNF2 = query_exp.DNF([c1,c2])
    assert query_exp.DNF2.containedIn(query_exp.DNF1) == True

def test_cnf_containment():
    R = query_sym.Relation('R', [query_sym.Variable('x'), query_sym.Variable('y')])
    S = query_sym.Relation('S', [query_sym.Variable('y'), query_sym.Variable('z')])
    T = query_sym.Relation('T', [query_sym.Variable('z'), query_sym.Variable('w')])
    com1 = query_exp.Component([R])
    com2 = query_exp.Component([S])
    com3 = query_exp.Component([T])
    d1 = query_exp.DisjunctiveQuery([com1])
    d2 = query_exp.DisjunctiveQuery([com2])
    d3 = query_exp.DisjunctiveQuery([com3])
    query_exp.CNF1 = query_exp.CNF([d1,d2,d3])
    query_exp.CNF2 = query_exp.CNF([d1,d2])
    assert query_exp.CNF1.containedIn(query_exp.CNF2) == True

def test_cnf_containment2():
    R = query_sym.Relation('R', [query_sym.Variable('x'), query_sym.Variable('y')])
    S = query_sym.Relation('S', [query_sym.Variable('y'), query_sym.Variable('z')])
    T = query_sym.Relation('T', [query_sym.Variable('z'), query_sym.Variable('w')])
    com1 = query_exp.Component([R])
    com2 = query_exp.Component([S])
    com3 = query_exp.Component([T])
    d1 = query_exp.DisjunctiveQuery([com1])
    d2 = query_exp.DisjunctiveQuery([com2])
    d3 = query_exp.DisjunctiveQuery([com3])
    query_exp.CNF1 = query_exp.CNF([d1,d2,d3])
    query_exp.CNF2 = query_exp.CNF([d1,d2])
    assert query_exp.CNF2.containedIn(query_exp.CNF1) == False

def test_comp_minimization():
    R1 = query_sym.Relation('R', [query_sym.Variable('y'), query_sym.Variable('x')])
    R2 = query_sym.Relation('R', [query_sym.Variable('z'), query_sym.Variable('x')])
    R3 = query_sym.Relation('R', [query_sym.Variable('w'), query_sym.Variable('x')])
    R4 = query_sym.Relation('R', [query_sym.Variable('x'), query_sym.Variable('u')])
    com1 = query_exp.Component([R1,R2,R3,R4])
    com2 = query_exp.Component([R1,R4])
    assert com1.minimize().containedIn(com2) == True
    assert com2.containedIn(com1.minimize()) == True

