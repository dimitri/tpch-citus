#! /bin/bash

set -x

pgversion=$1

device=$(ip -o link show | awk -F ': ' '! /lo:/ {print $2}')
cidr=$(ip -o addr show dev ${device}|awk '$3=="inet"{print $4}')
network=$(ipcalc -n ${cidr} | awk '/Network/ {print $2}')

su - postgres -c "createuser tpch"
su - postgres -c "createdb -O tpch tpch"

# TYPE  DATABASE        USER            ADDRESS                 METHOD

tee -a /etc/postgresql/${pgversion}/main/pg_hba.conf <<EOF
# TPCH setup
host tpch tpch ${network} trust
EOF

tee -a /etc/postgresql/${pgversion}/main/postgresql.conf <<EOF
listen_addresses='*'
EOF

/etc/init.d/postgresql restart
