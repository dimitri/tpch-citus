begin;

insert into public.run(name, system, setup, schedule, start, duration, sf)
     select name, system, setup, schedule, start, duration, sf
       from merge.run
  returning id as run_id

\gset
\echo :run_id

insert into public.job(run, name, start, duration, steps)
     select :run_id, name, start, duration, steps
       from merge.job
   order by job.id;

select max(id) - (select max(id) from merge.job) as job_id_diff
  from job

\gset
\echo :job_id_diff

insert into public.query(job, name, duration)
     select job + :job_id_diff, name, duration
       from merge.query;

commit;
