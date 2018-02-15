begin;

set local client_min_messages to error;

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
