--
-- PostgreSQL model to track TPC-H results
--

begin;

create table if not exists run
 (
   id        serial not null primary key,
   name      text,
   system    text,
   setup     jsonb,
   start     timestamptz,
   duration  interval,
   sf        integer,

   unique(name, system)
 );

create table if not exists load
 (
   id        serial not null primary key,
   run       integer not null references run(id),
   name      text not null,
   steps     integer[],
   start     timestamptz not null,
   duration  interval not null,
   vacuum_t  interval,

   unique(run, name)
 );

create table if not exists stream
 (
   id        serial not null primary key,
   run       integer not null references run(id),
   name      text not null,
   start     timestamptz,
   duration  interval not null
 );

create table if not exists query
 (
   id        bigserial not null primary key,
   stream    integer not null references stream(id),
   name      text not null,
   duration  interval
 );

commit;
