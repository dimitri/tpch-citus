begin;

select c.oid::regclass, pg_prewarm(c.oid)
  from pg_class c
       join pg_namespace n
         on n.oid = c.relnamespace
 where n.nspname = 'public'
   and relkind = 'r';

commit;
