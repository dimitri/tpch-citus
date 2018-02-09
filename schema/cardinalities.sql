drop view if exists cardinalities;

create view cardinalities as
 select
  (select count(*) from customer)  as customer,
  (select count(*) from lineitem)  as lineitems,
  (select count(*) from orders)    as orders,
  (select count(*) from part)      as part,
  (select count(*) from partsupp)  as partsupp,
  (select count(*) from supplier)  as supplier,
  (select count(*) from nation)    as nation,
  (select count(*) from region)    as region;
  
