#! /bin/bash

set -x

dbname=$1
system=$2
logdir=$3
run=$4

psql -a -d ${dbname} -f schema/tracking-merge-schema.sql

for table in run job query
do
    copy=${logdir}/${system}.${table}.copy
    psql -a -d ${dbname} -c "copy merge.${table} from stdin" < ${copy}
done

psql -a -d ${dbname} -f schema/tracking-merge-data.sql
psql -a -d ${dbname} -c "drop schema merge cascade"

PAGER=cat psql -a -d ${dbname} <<EOF
  select run, system, count(*)
    from results
   where run='${run}'
group by run, system
EOF

