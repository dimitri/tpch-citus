#! /bin/bash

# Install PostgreSQL on the Amazon Linux / EC2

set -x

if psql -d tpch-results -c 'select version();'
then
    echo "PostgreSQL is installed and running"
    echo
else
    sudo service postgresql96 initdb
    sudo service postgresql96 start
    sudo su - postgres -c "createuser ec2-user"
    sudo su - postgres -c "createdb -O ec2-user tpch-results"
    pg_isready -d tpch-results
fi


