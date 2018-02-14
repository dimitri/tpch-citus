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

# LOGFILE is on the (remote) loaders, LOGDIR is local to the controller
LOGFILE = ./tpch.out
LOGDIR  = ./logs/$(shell date "+%Y%m%d")_$(BNAME)

INFRA   = ./infra.py --config ./infra.ini
WAIT    = $(INFRA) ec2 wait --json
DSN     = $(INFRA) dsn
PGSQL   = $(shell $(INFRA) pgsql dsn)
CITUS   = $(shell $(INFRA) citus dsn)
RSOPTS  = --exclude-from 'rsync.exclude'
RSYNC   = rsync -e "ssh -o StrictHostKeyChecking=no" -avz $(RSOPTS)

RESULTS_DSN = postgresql://dim@localhost/tpch-results

#
# Make commands to help write targets
#
rsync = $(RSYNC) ./ ec2-user@$(shell $(WAIT) $(1)):tpch/
ssh   = ssh -l ec2-user $(shell $(WAIT) $(1))
scp   = scp ec2-user@$(shell $(WAIT) $(1)):$(2)
rmake = $(call ssh,$(1)) "cd tpch && make DSN=$(shell $(DSN) $(2)) -f Makefile.loader $(3)"
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
	echo "  fetch-logs     fetch logs in ./logs/YYYYMMDD_name/system.log"
	echo "  dump-results   dump results in ./logs/YYYYMMDD_name/system.dump"
	echo "  merge-results  merge the results into the RESULTS_DSN database"
	echo
	echo "  cardinalities  run SELECT count(*) on all the tables"

benchmark: infra $(NAME) bench-rds bench-aurora bench-pgsql bench-citus ;

name: $(NAME) ;

$(NAME):
	./tpch.py name > $@

bench-citus: loader-citus
	$(call tpch,$(CITUS_LOADER),$(CITUS),benchmark citus --kind citus)
	$(call ssh,$(CITUS_LOADER)) tail -f $(LOGFILE)

bench-pgsql: loader-pgsql
	$(call tpch,$(PGSQL_LOADER),$(PGSQL),benchmark citus-single-node --kind citus)
	$(call ssh,$(PGSQL_LOADER)) tail -f $(LOGFILE)

bench-rds: loader-rds rds
	$(call tpch,$(RDS_LOADER),$(RDS),benchmark rds)
	$(call ssh,$(RDS_LOADER)) tail -f $(LOGFILE)

bench-aurora: loader-aurora aurora
	$(call tpch,$(AURORA_LOADER),$(AURORA),benchmark aurora)
	$(call ssh,$(AURORA_LOADER)) tail -f $(LOGFILE)

tail-f: tail-f-citus tail-f-pgsql tail-f-rds tail-f-aurora ;

tail-f-citus:
	$(call ssh,$(CITUS_LOADER)) tail -f $(LOGFILE)

tail-f-pgsql:
	$(call ssh,$(PGSQL_LOADER)) tail -f $(LOGFILE)

tail-f-rds:
	$(call ssh,$(RDS_LOADER)) tail -f $(LOGFILE)

tail-f-aurora:
	$(call ssh,$(AURORA_LOADER)) tail -f $(LOGFILE)


fetch-logs: fetch-logs-citus fetch-logs-pgsql fetch-logs-rds fetch-logs-aurora ;

fetch-logs-citus:
	mkdir -p $(LOGDIR)
	$(call scp,$(CITUS_LOADER),$(LOGFILE)) $(LOGDIR)/citus.log

fetch-logs-pgsql:
	mkdir -p $(LOGDIR)
	$(call scp,$(PGSQL_LOADER),$(LOGFILE)) $(LOGDIR)/pgsql.log

fetch-logs-rds:
	mkdir -p $(LOGDIR)
	$(call scp,$(RDS_LOADER),$(LOGFILE)) $(LOGDIR)/rds.log

fetch-logs-aurora:
	mkdir -p $(LOGDIR)
	$(call scp,$(AURORA_LOADER),$(LOGFILE)) $(LOGDIR)/aurora.log

dump-results: dump-results-citus dump-results-pgsql dump-results-rds dump-results-aurora ;

dump-results-citus:
	$(call rmake,$(CITUS_LOADER),$(CITUS),dump)
	$(call scp,$(CITUS_LOADER),*.copy) /tmp
	mv /tmp/run.copy $(LOGDIR)/citus.run.copy
	mv /tmp/job.copy $(LOGDIR)/citus.job.copy
	mv /tmp/query.copy $(LOGDIR)/citus.query.copy

dump-results-pgsql:
	$(call rmake,$(PGSQL_LOADER),$(PGSQL),dump)
	$(call scp,$(PGSQL_LOADER),*.copy) /tmp
	mv /tmp/run.copy $(LOGDIR)/pgsql.run.copy
	mv /tmp/job.copy $(LOGDIR)/pgsql.job.copy
	mv /tmp/query.copy $(LOGDIR)/pgsql.query.copy

dump-results-rds:
	$(call rmake,$(RDS_LOADER),$(RDS),dump)
	$(call scp,$(RDS_LOADER),*.copy) /tmp
	mv /tmp/run.copy $(LOGDIR)/rds.run.copy
	mv /tmp/job.copy $(LOGDIR)/rds.job.copy
	mv /tmp/query.copy $(LOGDIR)/rds.query.copy

dump-results-aurora:
	$(call rmake,$(AURORA_LOADER),$(AURORA),dump)
	$(call scp,$(AURORA_LOADER),*.copy) /tmp
	mv /tmp/run.copy $(LOGDIR)/aurora.run.copy
	mv /tmp/job.copy $(LOGDIR)/aurora.job.copy
	mv /tmp/query.copy $(LOGDIR)/aurora.query.copy

merge-results: merge-results-citus merge-results-pgsql merge-results-rds merge-results-aurora ;

merge-results-citus:
	./scripts/merge-results.sh $(RESULTS_DSN) citus $(LOGDIR)

merge-results-pgsql:
	./scripts/merge-results.sh $(RESULTS_DSN) pgsql $(LOGDIR)

merge-results-rds:
	./scripts/merge-results.sh $(RESULTS_DSN) rds $(LOGDIR)

merge-results-aurora:
	./scripts/merge-results.sh $(RESULTS_DSN) aurora $(LOGDIR)


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
.PHONY: fetch-logs dump-results merge-results
.PHONY: fetch-logs-citus fetch-logs-pgsql fetch-logs-rds fetch-logs-aurora
.PHONY: dump-results-citus dump-results-pgsql dump-results-rds dump-results-aurora
.PHONY: merge-results-citus merge-results-pgsql merge-results-rds merge-results-aurora
.PHONY: list-zones list-amis pep8 pycodestyle
