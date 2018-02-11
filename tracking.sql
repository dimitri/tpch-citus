--
-- PostgreSQL model to track TPC-H results
--

begin;

create table run
 (
   id        serial not null primary key,
   name      text,
   setup     jsonb,
   start     timestamptz,
   duration  interval,
   sf        integer
 );

create table load
 (
   id        serial not null primary key,
   run       integer not null references run(id),
   name      text,
   steps     integer[],
   sf        int4range,
   start     timestamptz,
   duration  interval
 );

create table stream
 (
   id        serial not null primary key,
   run       integer not null references run(id),
   duration  interval
 );

create table query
 (
   id        bigserial not null primary key,
   stream    integer not null references stream(id),
   name      text not null,
   duration  interval
 );

commit;
