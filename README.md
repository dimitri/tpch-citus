# Citus TPC-H tests

The idea is to compare Citus Data with other Cloud Based offering that are
competitor, namely Amazon RDS and Amazon Aurora services.

## Running the benchmarks

First, we need to create the test infrastructure, then we can drive the
testing and record the performance characteristics.

### Infrastructure

We use the `ec2driver.py` script in this repository to spin-off some AWS
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
