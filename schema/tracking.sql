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
   steps     integer[]
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
            row_number() over(partition by run.id order by job.id) as job_number,
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


create or replace view qpm as
     select system,
            job.name,

            case when job.steps is not null
                 then job.steps[array_upper(job.steps, 1)]
             end as sf,

            job.duration,

            case when job.steps is null
                 then avg(query.duration)
             end as qtime,

            count(query.id) as queries,

            round((  count(query.id)
                   / extract(epoch from sum(query.duration))
                   * 60)::numeric,
                  4) as qpm

       from job
                 join run on run.id = job.run
            left join query on query.job = job.id

      where job.steps is not null
         or job.name ~ 'user-stream'

     group by run.id, job.id, query.job
     order by run.id, job.start;


create or replace view query_timings as
     with perc_arrays as (
         select run.system as system,
                job.id as job,
                job.name as jobname,
                sf.sf,
                query.name as query,
                avg(query.duration) as average,
                percentile_cont(array[0.5, 0.9, 0.95, 0.98, 0.99])
                   within group(order by query.duration) as pct
           from query
                join job on query.job = job.id
                join run on job.run = run.id
                left join lateral
                (
                  select steps[array_upper(steps, 1)] as sf
                    from job sf
                   where sf.id < job.id
                     and steps is not null
                order by sf.id desc
                   limit 1
                )
                as sf on true
       group by run.id, sf.sf, job.id, query.name
    )
    select system, sf, jobname, query,
           average,
           pct[1] as median,
           pct[2] as "90%",
           pct[3] as "95%",
           pct[4] as "98%",
           pct[5] as "99%"
      from perc_arrays
     order by system, sf, job, query;


commit;
