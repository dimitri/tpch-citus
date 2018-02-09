# Setup to be found in ./ec2.ini
RDS         = aws.out/db.rds.json
RDS_LOADER  = aws.out/rds.loader.json

AURORA        = aws.out/db.aurora.json
AURORA_LOADER = aws.out/aurora.loader.json

INFRA  = ./infra.py --config ./infra.ini
WAIT   = $(INFRA) ec2 wait --json
DSN    = $(INFRA) rds wait --json
RSYNC  = rsync -e "ssh -o StrictHostKeyChecking=no" -avz --exclude=.git

#
# Make commands to help write targets
#
rsync = $(RSYNC) ./ ec2-user@$(shell $(WAIT) $(1)):tpch/
ssh   = ssh -l ec2-user $(shell $(WAIT) $(1))
rmake = $(call ssh,$(1)) "cd tpch && /usr/bin/time -p make DSN=$(shell $(DSN) $(2)) $(4) -f Makefile.loader $(3)"
tpch  = $(call ssh,$(1)) "cd tpch && DSN=$(shell $(DSN) $(2)) ./tpch.py $(3)"

all: prepare ;

tpch: tpch-rds tpch-aurora ;

tpch-rds: loader-rds rds
	$(call tpch,$(RDS_LOADER),$(RDS),stream rds)

tpch-aurora: loader-aurora aurora
	$(call tpch,$(AURORA_LOADER),$(AURORA),stream aurora)

prepare: rds aurora loaders ;

loaders: loader-rds loader-aurora ;

loader-rds: $(RDS_LOADER)
	$(call rsync,$(RDS_LOADER))
	$(call rmake,$(RDS_LOADER),$(RDS),os repo)

loader-aurora: $(AURORA_LOADER)
	$(call rsync,$(AURORA_LOADER))
	$(call rmake,$(AURORA_LOADER),$(AURORA),os repo)

rds: $(RDS) ;
aurora: $(AURORA) ;

terminate: terminate-loaders
	$(INFRA) rds delete --json $(RDS)
	$(INFRA) aurora delete --json $(AURORA)

terminate-loaders:
	$(INFRA) ec2 terminate --json $(RDS_LOADER)
	$(INFRA) ec2 terminate --json $(AURORA_LOADER)

load: load-rds load-aurora ;
stream: stream-rds stream-aurora ;
drop: drop-rds drop-aurora ;

load-rds:
	$(call tpch,$(RDS_LOADER),$(RDS),load rds $(PHASE))

load-aurora:
	$(call tpch,$(AURORA_LOADER),$(AURORA),load aurora $(PHASE))

stream-rds:
	$(call rmake,$(RDS_LOADER),$(RDS),stream,STREAM=$(STREAM))

shell-rds:
	$(call ssh,$(RDS_LOADER))

psql-rds:
	$(call ssh,$(RDS_LOADER)) "psql -d $(shell $(DSN) $(RDS))"

drop-rds:
	$(call rmake,$(RDS_LOADER),$(RDS),drop)

stream-aurora:
	$(call rmake,$(AURORA_LOADER),$(AURORA),stream,STREAM=$(STREAM))

shell-aurora:
	$(call ssh,$(AURORA_LOADER))

psql-aurora:
	$(call ssh,$(AURORA_LOADER)) "psql -d $(shell $(DSN) $(AURORA))"

cardinalities:
	$(call rmake,$(RDS_LOADER),$(RDS),cardinalities)
	$(call rmake,$(AURORA_LOADER),$(AURORA),cardinalities)

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

.PHONY: loaders list-zones list-amis status
.PHONY: shell-rds shell-aurora psql-rds psql-aurora
.PHONY: stream-rds stream-aurora drop drop-rds drop-aurora
.PHONY: terminate terminate-loaders
.PHONY: tpch tpch-rds tcph-aurora
.PHONY: load load-phase-1 load-phase-2 load-phase-3
.PHONY: load-rds-phase-1 load-rds-phase-2 load-rds-phase-3
.PHONY: load-aurora-phase-1 load-aurora-phase-2 load-aurora-phase-3
