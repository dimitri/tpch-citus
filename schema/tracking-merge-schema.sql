begin;

create schema merge;

create table merge.run(like public.run);
create table merge.job(like public.job);
create table merge.query(like public.query);

commit;
