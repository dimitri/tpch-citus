# Citus TPC-H tests

The idea is to compare different PostgreSQL Cloud-based offerings. This
repository contains a partial implementation of TPC-H with Direct Loading
support for PostgreSQL and some scripting to orchestrate highly concurrent
tests.

## Running the benchmarks

To run the Citus TPC-H benchmark, follow those steps:

  1. Review the target infrastructure setup: `infra.ini`
  2. Start your target testing infrastructure: `make infra`
  3. Manually start a Citus cluster, and register its DSN in `tpch.ini`
  4. Register the Citus cluster also as PGSQL DSN
  5. Run the tests

The tests themselves consist of several units. We're interested in both the
data loading time and the read-only query performances:

    make -j 4 infra
    make -j 4 SCHEDULE=full benchmark

As we are using `-j4` the four tested system can be tested concurrently
(RDS, Aurora, PgSQL, Citus), thanks to make integrated parallelism.

## Running the benchmarks locally

It's possible to use the TPC-H benchmarks driver with a local PostgreSQL
database, without all the Cloud infrastructure in place. To that end, just
use the `tpch.py` command directly, without using the `Makefile` based
infrastructure management.

Here's an example of doing that:

~~~
$ DSN=postgresql:///tpch ./tpch.py benchmark pgsql --schedule quick
2018-02-12 11:20:22,544 INFO pgsql: starting benchmark sleep_slowly
2018-02-12 11:20:22,554 INFO pgsql: starting schedule initdb
2018-02-12 11:20:22,554 INFO pgsql: initializing the TPC-H schema
2018-02-12 11:20:22,554 INFO pgsql: create initial schema, pgsql variant
psql:./schema/cardinalities.sql:1: NOTICE:  view "cardinalities" does not exist, skipping
2018-02-12 11:20:22,707 INFO pgsql: loading 1 steps of data using 16 CPU: [1]
2018-02-12 11:20:28,836 INFO pgsql: loaded step 1/100 for Scale Factor 1
2018-02-12 11:20:28,838 INFO pgsql: vacuum analyze
2018-02-12 11:20:30,758 INFO pgsql: loaded 1 steps of data in 6.12964s, using 16 CPU
2018-02-12 11:20:30,759 INFO pgsql: install constraints from 'schema/tpch-pkeys.sql'
2018-02-12 11:20:30,912 INFO pgsql: install constraints from 'schema/tpch-index.sql'
2018-02-12 11:20:31,253 INFO pgsql: install constraints from 'schema/tpch-fkeys.sql'
2018-02-12 11:20:31,379 INFO pgsql: imported 1 initial steps in 8.82457s, using 16 CPU
2018-02-12 11:20:31,379 INFO pgsql: starting schedule stream
2018-02-12 11:20:31,379 INFO pgsql: Running TPCH with 16 CPUs for 5s, stream 1 4 6 12
2018-02-12 11:20:32,518 INFO pgsql: 1 query streams executed in 1.13002s
2018-02-12 11:20:34,036 INFO pgsql: 17 query streams executed in 2.64805s
2018-02-12 11:20:35,038 INFO pgsql: 17 query streams executed in 3.64983s
2018-02-12 11:20:36,575 INFO pgsql: 33 query streams executed in 5.1877s
2018-02-12 11:20:38,393 INFO pgsql: executed 49 streams (196 queries) in 6.99254s, using 16 CPU
~~~

To be able to reproduce this locally, you need to firts create a
`tpch-results` database and configure it in the `tpch.ini` file.

## Analysing the Results

The `tpch.py` benchmark driver collects timings as the benchmark runs in a
local PostgreSQL database named `tpch-results`. This database is local to
each loader instance, so an extra step is needed to collect the results
centrally.

Here's the results of running a series of local benchmark as done
previously, where the name of the run as been assigned as `sleep_slowly`:

~~~
tpch-results# select system, schedule, job, duration, count
                from results
               where run = 'sleep_slowly';

 system │ schedule │          job          │    duration     │ count 
════════╪══════════╪═══════════════════════╪═════════════════╪═══════
 pgsql  │ quick    │ drop tables           │ @ 0.060019 secs │     1
 pgsql  │ quick    │ create tables         │ @ 0.042395 secs │     1
 pgsql  │ quick    │ initdb                │ @ 6.12964 secs  │     1
 pgsql  │ quick    │ schema/tpch-pkeys.sql │ @ 0.144589 secs │     1
 pgsql  │ quick    │ schema/tpch-index.sql │ @ 0.331428 secs │     1
 pgsql  │ quick    │ schema/tpch-fkeys.sql │ @ 0.11635 secs  │     1
 pgsql  │ quick    │ stream                │ @ 6.992539 secs │   196
(7 rows)
~~~

The `tpch.py` driver is meant to be called on a remote machine, the _loader_
node, and the DSN is then passed in the environment by the main `Makefile`.

## Benchmark Schedule and Jobs

This benchmark is based on TPC-H and meant to incrementally reach the Scale
Factor, by implementing the data load in multiple phases. It is possible to
configure several load phases in the file `tpch.ini`, following this
example:

~~~ ini
[scale]
cpu = 16
factor = 300
children = 100

[schedule]
full     = initdb, stream, phase1, stream
quick    = initdb, stream
stream   = stream

[initdb]
type  = load
steps = 1..10

[phase1]
type  = load
steps = 11..30

[phase2]
type  = load
steps = 31..100
cpu   = 2

[stream]
type     = stream
queries  = 1 4 6 12
duration = 5
~~~

With such a setup, the target database size is 300 GB (the TPC-H scale
factor unit is roughly 1GB), and we can load the data using the three phases
arbitrarily named _initdb_, _phase1_ and _phase2_. 

To run the `full` schedule on all systems in parallel, it's possible to run
the following command:

    make -j 4 SCHEDULE=full make benchmark

This command then connects to each of the controller nodes for the tested
systems, and runs the following command there:

    DSN=... ./tpch.py benchmark <system name> --name <name> --schedule full

The _system name_ is going to be replaced by each of the systems considered
in this benchmark, currently that's _citus, _pgsql_, _rds_, and _aurora_.
The _name_ of the benchmark is computed once on the controller node (the one
where you're tying the `make` commands) then the same name is used on every
node. That allows to then easily merge all the tracked timings to further
analyze them as part of the same benchmark run and configuration.

Note: the `initdb` job is an hard-coded special job name that does several
extra things.

### Initialiazing the TPC-H database

The _initdb_ job consists of the following actions:

  1. create the schema
  2. install the `cardinalities` view, a simple COUNT wrapper
  3. load the configured steps of data, see next section
  4. install the SQL constraints: primary and foreign keys, and indexes
  5. vacuum analyze the resulting database

It is possible to select a schema variant thanks to the `--kind` option on
the `tpch.py load` command, currently the `pgsql` (default) and `citus` ones
are provided.

### Loading Phase Specifications

The `tpch.ini` file expects a _Load Phase Specification_ for each option in
the `[load]` section. Make sure that the section contains the `initdb`
option, as seen above.

Then, each option is an arbitrary name of a loading phase. Each phase
consists of a set of steps as per the TPC-H specifications. The steps must
be a continuous range.

~~~ ini
[phase1]
type  = load
steps = 11..30
~~~

In this exemple, the `phase1` phase consists of the 20 steps from 11 to 30.

The STEP numbers are used as the `-S` argument to the `dbgen` program. Of
course, for such a setup to make any sense the steps should all be within
the range 1..children, with `children` being an option of the `[scale]`
section in the same `tpch.ini`.

### Concurrency

The load phases and the streams are done concurrently with a Python pool of
processes. The `[scale]` option `cpu` is used to configure how many process
are being started on the coordinator.

With the previous setup where `cpu = 16`, the `phase1` load phase of steps
11 to 30 included in going to be ran on the pool of 16 worker process, one
per CPUs. As soon as a worker process is done with a step, the driver starts
another process load one of the remaining steps, until all the steps are
loaded.

## Streaming Queries Concurrently

The stream testing is limited in time, and we measure how much work could be
done in a specified amount of time by the different systems in competition.

~~~ ini
[stream]
type     = stream
queries  = 1 4 6 12
duration = 600
~~~

In this setup, a STREAM consists of running the TPC-H queries 1, then 4,
then 6, then 12, in this order, one after the other. As many streams as we
have CPU in the `[scale]` section are started concurrently, and as soon as a
stream is done, it is replaced by another one.

Each query execution time is registered, and new streams are started for as
long as `duration` allows. The duration is read as a number of seconds.
After having started new streams during _duration_ seconds, then the process
pool waits until the currently running streams are all done.

Here's a sample output of a query stream ran for 5s on a single CPU:

~~~
$ DSN=postgresql:///tpch ./tpch.py benchmark pgsql --schedule stream
2018-02-12 11:34:36,730 INFO pgsql: starting benchmark solve_sometimes
2018-02-12 11:34:36,739 INFO pgsql: starting schedule stream
2018-02-12 11:34:36,739 INFO pgsql: Running TPCH with 16 CPUs for 5s, stream 1 4 6 12
2018-02-12 11:34:37,830 INFO pgsql: 1 query streams executed in 1.07669s
2018-02-12 11:34:39,396 INFO pgsql: 17 query streams executed in 2.6434s
2018-02-12 11:34:40,400 INFO pgsql: 17 query streams executed in 3.64771s
2018-02-12 11:34:41,901 INFO pgsql: 33 query streams executed in 5.14833s
2018-02-12 11:34:43,581 INFO pgsql: executed 49 streams (196 queries) in 6.81578s, using 16 CPU
~~~

## Usage

The main Makefile targets are listed with `make help`. To test several
systems in parallel, use e.g. `make -j2 stream`.

~~~
$ make help
TPC-H benchmark for PostgreSQL and Citus Data

Use make to drive the benchmark, with the following targets:

  help           this help message
  infra          create AWS test infrastructure
  terminate      destroy AWS test infrastructure
  drop           drop TPC-H test tables

  benchmark      bench-citus bench-pgsql bench-rds bench-aurora
  bench-citus    run given SCHEDULE on the citus system
  bench-pgsql    run given SCHEDULE on the pgsql system
  bench-rds      run given SCHEDULE on the rds system
  bench-aurora   run given SCHEDULE on the aurora system

  tail-f         see logs from currently running benchmark
  fetch-logs     fetch logs in ./logs/YYYYMMDD_name/system.log
  dump-results   dump results in ./logs/YYYYMMDD_name/system.dump
  merge-results  merge the results into the RESULTS_DSN database

  cardinalities  run SELECT count(*) on all the tables
~~~

## Why Makefiles

This implementation uses Python drivers when necessary, and uses Makefiles a
lot. The intend here is to make the benchmark as easy to hack as possible,
and the nice thing about a Makefile is that it's easy to run, test and debug
a single make target.

It's also very easy to adapt the benchmark to different tools, allowing
quick prototypes to be developped and making is easy and cheap to change
one's mind.

Make is a very good glue language, indeed.

## Hacking the benchmarks

First, we need to create the test infrastructure, then we can drive the
testing and record the performance characteristics.

The benchmark uses 3 kinds of services, that needs to be connected either
using SSH or the PostgreSQL protocol directly:

  - a controller node, typically localhost, your usual laptop
  - several loader nodes
  - several database clusters or instances

### The Controller

That's where you type your commands from. The controller mainly uses the
following files:

  - Makefile
  - infra.ini
  - infra.py and the infra Python module

The Makefile is used to automatically start the whole test infrastructure,
and orchestrate the different tests that are run on the loader instances.
The `infra.ini` setup registers AWS configuration parameters (such as the
region, availability zone, VPC, subnets, security groups, keyname) and the
setup of each kind of machine that is going to be used.

When running the benchmark, the infrastructure consists of:

  - a controller node
  - a loader node per database system being benchmarked
  - the database services to test

The `infra.py` file knows how to start EC2 instances, RDS database instances
and Aurora PostgreSQL clusters with a single database instance. To test the
Citus and PostgreSQL core instances, you need to manage the services
manually and then register the Database Source Name (or DSN) used to connect
to the running service.

### The Loader

While the loader is meant to be remotely controlled by the controller, it is
also made easy to interact with directly. The main controller Makefile uses
targets that ssh into the loader and run command there. A typical action
from the controller will use something that looks like the following:

    ssh -l ec2-user DSN=postgresql://.../db make -f Makefile.loader target

The loader mainly uses the following files:

  - Makefile.loader
  - tpch-pg PostgreSQL port of the TPC-H sources (dbgen and qgen)
  - tpch.ini
  - tpch.py and the tpch Python module
  - tracking.sql and a PostgreSQL database where to register the stats

The main entry point of the loader is the `tpch.py` command, which
implements its action by means of calling into the `Makefile.loader` file,
with arguments made available on the command line. A typical command run
from the loader looks like the following:

    DSN=postgresql:///tpch ./tpch.py benchmark pgsql --schedule SCHEDULE

The `tpch.py` tool then reads its `tpch.ini` configuration file that
contains the benchmarking setup and applies it by calling into the
`Makefile.loader` with the right arguments passed in the command line, such
as in the following example:

    make -f Makefile.loader SF=30000 C=300 S=1 load
    make -f Makefile.loader STREAM='1 3 6 12' stream

Such a command is expected to be called from the `tpch.py` command line, not
interactively. The reason why the Python driver exists is so that we can
easily run 16 such commands, with S varying from 1 to 16, on 16 different
CPU cores concurrently. It's fair to consider the `tcpy.py` program as a
concurrent driver for the benchmark suite.

The `DSN` environment variable should be set when calling `tpch.py`. The
Python script does nothing with it, but then `Makefile.loader` is using it
to know how to contact the database system being tested. Setting the DSN is
the job of the main controller scripts.

### The databases

The `infra.py` script knows how to create and terminate both RDS and Aurora
PostgreSQL instances on AWS. The details of the instances are setup using
the following INI syntax:

~~~ ini
[rds]
name = tpch
size = 4500
iops = 10000
class = db.r4.2xlarge
stype = io1
pgversion = 9.6.5

[aurora]
name = tpch
class = db.r4.2xlarge
stype = io1
~~~

It's then possible to retrieve the DSN to be used to connect to a database
created thanks to the infra driver's command:

    $ ./infra.py rds dsn --json aws.out/db.rds.json

This might result in an error, so in order to wait until the service is
available, it's possible to use the `wait` command:

    $ ./infra.py rds dsn --json aws.out/db.rds.json

That's what the main Makefile is using.

## Implementation Notes

### Infrastructure

We use the `infra.py` script in this repository to spin-off some AWS
instances of EC2 virtual machines and RDS databases.

### Getting the numbers

A benchmark consists of the following activities.

First, load the data set:

  1. create the database model
  2. load an initial set of data
  3. add primary keys, foreign keys and extra indexes to the model
  4. vacuum verbose analyze it all

Now that we have a data set, run the queries:

  1. start N+1 concurrent sessions
  2. the first one runs the database update scripts
  3. each other one is doing a stream of TPCH analytical Queries
  4. measure time spent on each query in each session, and to run each stream

Now, enlarge the data set and repeat step 2 before

  1. generate more data with DBGEN

### Scale Factors

The interesting test is going to be with a 30TB database size when
completely loaded, and with the following steps:

  - 100 GB
  - 300 GB
  - 1 TB
  - 3 TB
  - 10 TB
  - 30 TB

Here's how to use DBGEN to achieve that:

  - ./dbgen -s 30000 -C 300 -S 1 -D -n DSN

     This command produces the first 100GB of data for a 30TB Scale Factor
     of a test.

  - ./dbgen -s 30000 -C 300 -U 1 -D -n DSN

    This command produces the set of updates that go with the first 100GB of
    data.

  - DSS_QUERY=../queries/ ./qgen -s 100 1

    This command produces Q1 with parameters adapted to SF=100, and the SQL
    text is found on stdout, ready to be sent to PostgreSQL.

## Notes

Autora claims the following on their main page, [Amazon Aurora Product
Details](https://aws.amazon.com/fr/rds/aurora/details/postgresql-details/)
says:

> The PostgreSQL-compatible edition of Aurora delivers up to 3X the
> throughput of standard PostgreSQL running on the same hardware

Some reading and viewing/listening for background information about Aurora:

  - https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide//AuroraPostgreSQL.BestPractices.html

    TCP keepalives and Admission Resource Control?

  - https://www.toadworld.com/platforms/postgres/b/weblog/archive/2017/06/07/a-first-look-at-amazon-aurora-with-postgresql-compatibility-benefits-and-drawbacks-part-v

    So the 3X throughput actually seems to be obtained when using
    [Sysbench](https://wiki.postgresql.org/wiki/SysBench), a benchmarking
    suite that has been known to be good for MySQL and put PostgreSQL into
    bad lights.

  - https://www.youtube.com/watch?v=xrMbzHdPLKM&feature=youtu.be&t=30m20s

    No checkpoints, no WAL, 4-out-of-6 writes on distributed block storage,
    or something like that.
