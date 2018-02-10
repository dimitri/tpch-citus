# Setup to be found in ./ec2.ini
RDS         = aws.out/db.rds.json
RDS_LOADER  = aws.out/rds.loader.json

AURORA        = aws.out/db.aurora.json
AURORA_LOADER = aws.out/aurora.loader.json

PGSQL_LOADER  = aws.out/pgsql.loader.json
CITUS_LOADER  = aws.out/citus.loader.json

INFRA  = ./infra.py --config ./infra.ini
WAIT   = $(INFRA) ec2 wait --json
DSN    = $(INFRA) dsn
PGSQL  = $(shell $(INFRA) pgsql dsn)
CITUS  = $(shell $(INFRA) citus dsn)
RSYNC  = rsync -e "ssh -o StrictHostKeyChecking=no" -avz --exclude=.git

#
# Make commands to help write targets
#
rsync = $(RSYNC) ./ ec2-user@$(shell $(WAIT) $(1)):tpch/
ssh   = ssh -l ec2-user $(shell $(WAIT) $(1))
rmake = $(call ssh,$(1)) "cd tpch && /usr/bin/time -p make DSN=$(shell $(DSN) $(2)) $(4) -f Makefile.loader $(3)"
tpch  = $(call ssh,$(1)) "cd tpch && DSN=$(shell $(DSN) $(2)) ./tpch.py $(3)"

.SILENT: help
help:
	echo "TPC-H benchmark for PostgreSQL and Citus Data"
	echo
	echo "Use make to drive the benchmark, with the following targets:"
	echo
	echo "  help           this help message"
	echo "  all            infra initdb stream"
	echo "  infra          create AWS test infrastructure"
	echo "  terminate      destroy AWS test infrastructure"
	echo "  drop           drop TPC-H test tables"
	echo
	echo "  stream         stream-citus stream-pgsql stream-rds stream-aurora "
	echo "  stream-citus   run TPC-H query STREAMs on Citus"
	echo "  stream-pgsql   run TPC-H query STREAMs on PostgreSQL"
	echo "  stream-rds     run TPC-H query STREAMs on RDS"
	echo "  stream-aurora  run TPC-H query STREAMs on Aurora"
	echo
	echo "  load           load-citus load-pgsql load-rds load-aurora "
	echo "  load-citus     run load for env. PHASE on Citus"
	echo "  load-psql      run load for env. PHASE on PostgreSQL"
	echo "  load-rds       run load for env. PHASE on RDS"
	echo "  load-aurora    run load for env. PHASE on Aurora"
	echo
	echo "  cardinalities  run SELECT count(*) on all the tables"

all: infra initdb stream ;

stream: stream-rds stream-aurora stream-pgsql stream-citus ;

stream-rds: loader-rds rds
	$(call tpch,$(RDS_LOADER),$(RDS),stream rds)

stream-aurora: loader-aurora aurora
	$(call tpch,$(AURORA_LOADER),$(AURORA),stream aurora)

stream-pgsql:
	$(call tpch,$(PGSQL_LOADER),$(PGSQL),stream pgsql)

stream-citus:
	$(call tpch,$(CITUS_LOADER),$(CITUS),stream pgsql)

infra: rds aurora loaders ;

loaders: loader-rds loader-aurora loader-pgsql loader-citus ;

loader-rds: $(RDS_LOADER)
	$(call rsync,$(RDS_LOADER))
	$(call rmake,$(RDS_LOADER),$(RDS),os tools)

loader-aurora: $(AURORA_LOADER)
	$(call rsync,$(AURORA_LOADER))
	$(call rmake,$(AURORA_LOADER),$(AURORA),os tools)

loader-pgsql: $(PGSQL_LOADER)
	$(call rsync,$(PGSQL_LOADER))
	$(call rmake,$(PGSQL_LOADER),$(PGSQL),os tools)

loader-citus: $(CITUS_LOADER)
	$(call rsync,$(CITUS_LOADER))
	$(call rmake,$(CITUS_LOADER),$(CITUS),os tools)

rds: $(RDS) ;
aurora: $(AURORA) ;

terminate: terminate-loaders
	$(INFRA) rds delete --json $(RDS)
	$(INFRA) aurora delete --json $(AURORA)

terminate-loaders:
	$(INFRA) ec2 terminate --json $(RDS_LOADER)
	$(INFRA) ec2 terminate --json $(AURORA_LOADER)
	$(INFRA) ec2 terminate --json $(PGSQL_LOADER)
	$(INFRA) ec2 terminate --json $(CITUS_LOADER)

load: load-rds load-aurora load-pgsql load-citus ;
drop: drop-rds drop-aurora drop-pgsql drop-citus ;

load-rds:
	$(call tpch,$(RDS_LOADER),$(RDS),load rds $(PHASE))

load-aurora:
	$(call tpch,$(AURORA_LOADER),$(AURORA),load aurora $(PHASE))

load-pgsql:
	$(call tpch,$(PGSQL_LOADER),$(PGSQL),load pgsql $(PHASE))

load-citus:
	$(call tpch,$(CITUS_LOADER),$(CITUS),load citus $(PHASE))

drop-rds:
	$(call rmake,$(RDS_LOADER),$(RDS),drop)

drop-pgsql:
	$(MAKE) DSN=$(PGSQL) -f Makefile.loader drop

drop-citus:
	$(MAKE) DSN=$(CITUS) -f Makefile.loader drop

shell-rds:
	$(call ssh,$(RDS_LOADER))

shell-pgsql:
	$(call ssh,$(PGSQL_LOADER))

shell-citus:
	$(call ssh,$(CITUS_LOADER))

shell-aurora:
	$(call ssh,$(AURORA_LOADER))

psql-rds:
	$(call ssh,$(RDS_LOADER)) "psql -d $(shell $(DSN) $(RDS))"

psql-aurora:
	$(call ssh,$(AURORA_LOADER)) "psql -d $(shell $(DSN) $(AURORA))"

cardinalities:
	$(call rmake,$(RDS_LOADER),$(RDS),cardinalities)
	$(call rmake,$(AURORA_LOADER),$(AURORA),cardinalities)
	DSN=$(PGSQL) $(MAKE) -f Makefile.loader cardinalities
	DSN=$(CITUS) $(MAKE) -f Makefile.loader cardinalities

status:
	$(INFRA) ec2 list
	$(INFRA) rds list
	$(INFRA) aurora list

list-zones:
	aws --region $(REGION) ec2 describe-availability-zones | \
	jq '.AvailabilityZones[].ZoneName'

list-amis:
	aws --region $(REGION)                                          \
	    ec2 describe-images --owners amazon                       | \
	jq '.Images[] | select(.Platform != "windows")                  \
                      | select(.ImageType == "machine")                 \
                      | select(.RootDeviceType == "ebs")                \
                      | select(.VirtualizationType == "hvm")            \
                      | {"ImageId": .ImageId, "Description": .Description}'

aws.out/%.loader.json:
	$(INFRA) ec2 run --json $@

aws.out/%.rds.json:
	$(INFRA) rds create --json $@

aws.out/%.aurora.json:
	$(INFRA) aurora create --json $@

pep8: pycodestyle ;
pycodestyle:
	pycodestyle --ignore E251,E221 *py tpch/*py infra/*py

.PHONY: infra rds aurora loaders status
.PHONY: stream stream-rds stream-aurora stream-pgsql stream-citus
.PHONY: load load-rds load-aurora load-pgsql load-citus
.PHONY: shell-rds shell-aurora psql-rds psql-aurora
.PHONY: stream-rds stream-aurora drop drop-rds drop-aurora
.PHONY: terminate terminate-loaders
.PHONY: list-zones list-amis pep8 pycodestyle
