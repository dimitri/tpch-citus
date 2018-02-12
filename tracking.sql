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
   schedule  text,
   start     timestamptz,
   duration  interval,
   sf        integer,

   unique(name, system)
 );

create table if not exists job
 (
   id        serial not null primary key,
   run       integer not null references run(id),
   name      text not null,
   start     timestamptz not null,
   duration  interval,
   vacuum_t  interval,
   steps     integer[],

   unique(run, name)
 );

create table if not exists query
 (
   id        bigserial not null primary key,
   job       integer not null references job(id),
   name      text not null,
   duration  interval
 );

create or replace view results
    as
     select run.name as run,
            run.system as system,
            run.schedule as schedule,
            job.name as job,
            job.start,
            job.duration,
            case when job.steps is not null
                 then
                 format('%s..%s',
                        job.steps[array_lower(job.steps, 1)],
                        job.steps[array_upper(job.steps, 1)])
             end as steps,
            count(*)
       from job
                 join run on run.id = job.run
            left join query on query.job = job.id
   group by run.id, job.id
   order by run.id, job.start;

commit;
