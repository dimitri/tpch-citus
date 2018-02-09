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
  4. Run the tests

The tests themselves consist of several units. We're interested in both the
data loading time and the read-only query performances:

  - load a bunch of data: `make PHASE=initdb load`
  - do a concurrent read test: `make -j4 stream`

You can achieve a simple one-stage test like with with `make`, the default
`all` target runs the targets `infra`, `initdb`, and `stream` in that order.

The concurrent read test here is using `-j4` and thus will run all tests
concurrently (RDS, Aurora, PgSQL, Citus), thanks to make integrated
parallelism.

## Analysing the Results

TODO: collect the results in a PostgreSQL database, then work on some
tooling to show the data.

## Load Phases

This benchmark is based on TPC-H and meant to incrementally reach the Scale
Factor, by implementing the data load in multiple phases. It is possible to
configure the load phases in the file `tpch.ini`, following this example:

~~~ ini
[scale]
cpu = 16
factor = 300
children = 100

[load]
initdb = 1..10
phase1 = 11..30
phase2 = 31..100
~~~

With such a setup, the target database size is 300 GB (the TPC-H scale
factor unit is roughly 1GB), and we can load the data using the three phases
arbitrarily named _initdb_, _phase1_ and _phase2_. To load the _initdb_
phase on all the tested systems, run the following command on the
controller:

    PHASE=initdb make load

This command then connects to each of the controller nodes for the tested
systems, and runs the following command there:

    ./tpch.py DSN=... load <system name> initdb

The name _initdb_ is special here in that `tpch.py` recognize it with a
different meaning as the other arbitrary phase names.

### Initialiazing the TPC-H database

The _initdb_ phase consists of the following actions:

  1. create the schema
  2. install the `cardinalities` view, a simple COUNT wrapper
  3. load the `initdb` phase, see next section
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
[load]
initdb = 1..10
phase1 = 11..30
phase2 = 31..100
~~~

In this exemple, the `initdb` phase consists of the 10 steps from 1 to 10,
the `phase1` phase consists of the 20 steps from 11 to 30 and the `phase2`
step consists of the 70 steps from 31 to 100.

The STEP numbers are used as the `-S` argument to the `dbgen` program. Of
course, for such a setup to make any sense the steps should all be within
the range 1..children, with `children` being an option of the `[scale]`
section in the same `tpch.ini`.

## Concurrency

The load phases and the streams are done concurrently with a Python pool of
processes. The `[scale]` option `cpu` is used to configure how many process
are being started on the coordinator.

With the previous setup where `cpu = 16`, the `initdb` load phase of steps 1
to 10 included in going to be ran on the pool of 16 worker process, keeping
10 of them buzy. The `phase1` phase of steps 11 to 30 included in going to
use the whole 16 CPUs and some of them, as soon as done with a first step,
are going to load a second one, until all the steps are loaded.

## Streaming Queries Concurrently

The stream testing is limited in time, and we measure how much work could be
done in a specified amount of time by the different systems in competition.

~~~ ini
[stream]
queries = 1 4 6 12
duration = 5
~~~

In this setup, a STREAM consists of running the TPC-H queries 1, then 3,
then 6, then 12, in this order, one after the other. As many streams as we
have CPU in the `[scale]` section are started concurrently, and as soon as a
stream is done, it is replaced by another one.

Each query execution time is registered, and new streams are started for as
long as `duration` allows. The duration is read as a number of seconds.
After having started new streams during _duration_ seconds, then the process
pool waits until the currently running streams are all done.

Here's a sample output of a query stream ran for 5s on a single CPU:

~~~
$ DSN=postgresql:///tpch ./tpch.py stream pg
Running TPCH on pg with 1 CPUs for 5s, stream 1 3 6 12
pg: executed 6 streams of 4 queries in 5.1805s, using 1 CPU
~~~

## Usage

The main Makefile targets are listed with `make help`. To test several
systems in parallel, use e.g. `make -j2 stream`.

~~~
$ make help
TPC-H benchmark for PostgreSQL and Citus Data

Use make to drive the benchmark, with the following targets:

  help           this help message
  all            infra initdb stream
  infra          create AWS test infrastructure
  terminate      destroy AWS test infrastructure
  drop           drop TPC-H test tables

  stream         stream-citus stream-pgsql stream-rds stream-aurora 
  stream-citus   run TPC-H query STREAMs on Citus
  stream-pgsql   run TPC-H query STREAMs on PostgreSQL
  stream-rds     run TPC-H query STREAMs on RDS
  stream-aurora  run TPC-H query STREAMs on Aurora

  load           load-citus load-pgsql load-rds load-aurora 
  load-citus     run load for env. PHASE on Citus
  load-psql      run load for env. PHASE on PostgreSQL
  load-rds       run load for env. PHASE on RDS
  load-aurora    run load for env. PHASE on Aurora

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

    DSN=postgresql:///tpch ./tpch.py initdb local

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
