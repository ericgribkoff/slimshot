SafeSample
====

SafeSample evaluates probabilistic queries over tuple-independent
probabilistic databases. See the 2011 book Probabilistic Databases by
Suciu, Olteanu, Re, Koch for an overview of the semantics. This code
accompanies our SlimShot system for Markov Logic Network inference,
described in a technical report available at
http://homes.cs.washington.edu/~eagribko/.

SafeSample allows interactively typing queries, using a datalog-style
syntax. These queries are parsed and translated into query plans,
which are evaluted against the Postgres backend to return the
probability of the query over the distribution described by the
probabilistic database. For safe queries (those that can be computed
in polynomial-time), SafeSample will execute a single query and return
the result. For unsafe queries (those that are #P-hard to compute),
SafeSample combines sampling with exact query evaluation to
efficiently compute an approximate answer.

For comparison purposes, the code also contains implementations of the
Karp-Luby DNF approximation algorithm and a naive Monte Carlo sampler.

The full power of SafeSample is realized for inference over MLN
networks to compute conditional probabilities: Pr(Q | MLN). The
present SafeSample code contains all of the underlying logic for
evaluating the MLN queries, but does not include the full SlimShot
system that handles converting MLNs into probabilistic database
queries and using correlated and importance sampling to estimate Pr(Q
| MLN). The full SlimShot code will be in an upcoming release.


Example Usage
=====

First, you need to have a database created in Postgres. You may reuse
an existing database, or [create a new
one](http://www.postgresql.org/docs/9.1/static/app-createdb.html) for
use with SafeSample.  The default database name is 'sampling', but you
can specify a different name as a command line argument. The following
command creates a new database called 'sampling':

```
createdb sampling
```

Second, initialize the database aggregates necessary for probabilistic
query plan evaluation and import a probabilistic dataset into your new database. There
are several sample datasets in test/test\_data/, including
sampling.sql, which we will use for the examples. You can accomplish
both of these tasks with the following two commands:

```
psql -f sql_aggregates.sql sampling
psql -f test/test_data/sampling.sql sampling
```

Next, start up the interactive query parser:

```
python query_parser.py --db sampling
```

You should see a command line prompt, where you can type the
following:

```
> queryplan plan.png
```

This will save the query execution plan of each subsequent query to
the file plan.png in your current directory.

Now execute an actual query, using the Parser's datalog-like syntax:

```
> R(x),S(x,y)
```

The query plan SQL will be displayed, followed by the answer computed
over the data from constants.sql: 

```
Query probability: 0.986483 (exact)
```

Open the file plan.png to see the query plan displayed as a tree:

<img src="sample_plan.png" width="65%" alt="Query plan">

A Hard Query
----

The example above could be computed exactly in polynomial time, but
the query R(x),S(x,y),T(y) (also known as h0) is #P-hard to compute.
The following command will run SafeSample to estimate the query
probability:

```
> R(x),S(x,y),T(y)
```

To compare the results to the Karp-Luby approximation algorithm or to
a naive Monte Carlo simulation, enable these samplers with the
following commands, then rerun the query:

```
> karpluby
> naive
> R(x),S(x,y),T(y)
```

