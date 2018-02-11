begin;

drop view if exists cardinalities;

drop table
 if exists nation,
           region,
           part,
           supplier,
           partsupp,
           customer,
           orders,
           lineitem
  cascade;

commit;
