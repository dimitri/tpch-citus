begin;

\echo :run

delete
  from query
 where job in (select job.id
                 from job join run on run.id = job.run
                where run.name = :'run');

delete
  from job
 where run in (select run.id
                 from run
                where run.name = :'run');

delete
  from run
 where name = :'run';

commit;
