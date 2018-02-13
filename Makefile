# Setup to be found in ./ec2.ini
RDS         = aws.out/db.rds.json
RDS_LOADER  = aws.out/rds.loader.json

AURORA        = aws.out/db.aurora.json
AURORA_LOADER = aws.out/aurora.loader.json

PGSQL_LOADER  = aws.out/pgsql.loader.json
CITUS_LOADER  = aws.out/citus.loader.json

SCHEDULE ?= full

NAME    = aws.out/name.txt
BNAME   = $(shell cat $(NAME))

LOGFILE = ./tpch.out

INFRA   = ./infra.py --config ./infra.ini
WAIT    = $(INFRA) ec2 wait --json
DSN     = $(INFRA) dsn
PGSQL   = $(shell $(INFRA) pgsql dsn)
CITUS   = $(shell $(INFRA) citus dsn)
RSOPTS  = --exclude-from 'rsync.exclude'
RSYNC   = rsync -e "ssh -o StrictHostKeyChecking=no" -avz $(RSOPTS)

#
# Make commands to help write targets
#
rsync = $(RSYNC) ./ ec2-user@$(shell $(WAIT) $(1)):tpch/
ssh   = ssh -l ec2-user $(shell $(WAIT) $(1))
rmake = $(call ssh,$(1)) "cd tpch && /usr/bin/time -p make DSN=$(shell $(DSN) $(2)) $(4) -f Makefile.loader $(3)"
tpch  = $(call ssh,$(1)) LC_ALL=en_US.utf8 ./tpch/tpch.py $(3) --name $(BNAME) --schedule $(SCHEDULE) --log $(LOGFILE) --dsn $(shell $(DSN) $(2)) --detach

.SILENT: help
help:
	echo "TPC-H benchmark for PostgreSQL and Citus Data"
	echo
	echo "Use make to drive the benchmark, with the following targets:"
	echo
	echo "  help           this help message"
	echo "  infra          create AWS test infrastructure"
	echo "  terminate      destroy AWS test infrastructure"
	echo "  drop           drop TPC-H test tables"
	echo
	echo "  benchmark      bench-citus bench-pgsql bench-rds bench-aurora"
	echo "  bench-citus    run given SCHEDULE on the citus system"
	echo "  bench-pgsql    run given SCHEDULE on the pgsql system"
	echo "  bench-rds      run given SCHEDULE on the rds system"
	echo "  bench-aurora   run given SCHEDULE on the aurora system"
	echo
	echo "  tail-f         see logs from currently running benchmark"
	echo
	echo "  cardinalities  run SELECT count(*) on all the tables"

benchmark: infra $(NAME) bench-rds bench-aurora bench-pgsql bench-citus ;

name: $(NAME) ;

$(NAME):
	./tpch.py name > $@

bench-citus: loader-citus
	$(call tpch,$(CITUS_LOADER),$(CITUS),benchmark citus --kind citus)

bench-pgsql: loader-pgsql
	$(call tpch,$(PGSQL_LOADER),$(PGSQL),benchmark pgsql)

bench-rds: loader-rds rds
	$(call tpch,$(RDS_LOADER),$(RDS),benchmark rds)
	$(call ssh,$(RDS_LOADER)) tail -f $(LOGFILE)

bench-aurora: loader-aurora aurora
	$(call tpch,$(AURORA_LOADER),$(AURORA),benchmark aurora)
	$(call ssh,$(AURORA_LOADER)) tail -f $(LOGFILE)

tail-f: tail-f-citus tail-f-pgsql tail-f-rds tail-f-aurora ;

tail-f-rds:
	$(call ssh,$(RDS_LOADER)) tail -f $(LOGFILE)

tail-f-aurora:
	$(call ssh,$(AURORA_LOADER)) tail -f $(LOGFILE)


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
	-$(INFRA) rds delete --json $(RDS)
	-$(INFRA) aurora delete --json $(AURORA)

terminate-loaders:
	rm -rf $(NAME)
	-$(INFRA) ec2 terminate --json $(RDS_LOADER)
	-$(INFRA) ec2 terminate --json $(AURORA_LOADER)
	-$(INFRA) ec2 terminate --json $(PGSQL_LOADER)
	-$(INFRA) ec2 terminate --json $(CITUS_LOADER)

drop: drop-rds drop-aurora drop-pgsql drop-citus ;

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

.PHONY: infra rds aurora loaders status name
.PHONY: becnhmark bench-rds bench-aurora bench-pgsql bench-citus
.PHONY: shell-rds shell-aurora psql-rds psql-aurora
.PHONY: terminate terminate-loaders
.PHONY: list-zones list-amis pep8 pycodestyle
