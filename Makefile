# Setup to be found in ./ec2.ini
RDS         = aws.out/db.rds.json
RDS_LOADER  = aws.out/rds.loader.json

AURORA        = aws.out/db.aurora.json
AURORA_LOADER = aws.out/aurora.loader.json

# Parameters that you can set from the outside.
CPU      ?= 16
DURATION ?= 600
S        ?= 2
STREAM   ?= '1 3 6 12'

DRIVER = ./ec2driver.py --config ./ec2.ini
WAIT   = $(DRIVER) ec2 wait --json
DSN    = $(DRIVER) rds wait --json
RSYNC  = rsync -e "ssh -o StrictHostKeyChecking=no" -avz --exclude=.git
TPCH_O = $(CPU) $(DURATION)

#
# Make commands to help write targets
#
rsync = $(RSYNC) ./ ec2-user@$(shell $(WAIT) $(1)):tpch/
ssh   = ssh -l ec2-user $(shell $(WAIT) $(1))
rmake = $(call ssh,$(1)) "cd tpch && /usr/bin/time -p make DSN=$(shell $(DSN) $(2)) $(4) -f Makefile.loader $(3)"
tpch  = $(call ssh,$(1)) "cd tpch && DSN=$(shell $(DSN) $(2)) ./tpch.py $(3)"

all: prepare init ;

tpch: tpch-rds tpch-aurora ;

tpch-rds: loader-rds rds
	$(call tpch,$(RDS_LOADER),$(RDS),stream rds $(STREAM) $(TPCH_O))

tpch-aurora: loader-aurora aurora
	$(call tpch,$(AURORA_LOADER),$(AURORA),stream aurora $(STREAM) $(TPCH_O))

prepare: rds aurora loaders ;

loaders: loader-rds loader-aurora ;

loader-rds: $(RDS_LOADER)
	$(call rsync,$(RDS_LOADER))

loader-aurora: $(AURORA_LOADER)
	$(call rsync,$(AURORA_LOADER))

rds: $(RDS) ;
aurora: $(AURORA) ;

terminate: terminate-loaders
	$(DRIVER) rds delete --json $(RDS)
	$(DRIVER) aurora delete --json $(AURORA)

terminate-loaders:
	$(DRIVER) ec2 terminate --json $(RDS_LOADER)
	$(DRIVER) ec2 terminate --json $(AURORA_LOADER)

init: init-rds init-aurora ;
load: load-rds load-aurora ;
stream: stream-rds stream-aurora ;
drop: drop-rds drop-aurora ;

init-rds: loader-rds
	$(call rmake,$(RDS_LOADER),$(RDS),os repo)
	$(call rmake,$(RDS_LOADER),$(RDS),init)

load-rds-phase-1: loader-rds
	$(call tpch,$(RDS_LOADER),$(RDS),load rds 2..10 $(CPU))

load-rds-phase-2: loader-rds
	$(call tpch,$(RDS_LOADER),$(RDS),load rds 11..30 $(CPU))

load-rds-phase-3: loader-rds
	$(call tpch,$(RDS_LOADER),$(RDS),load rds 31..100 $(CPU))

stream-rds:
	$(call rmake,$(RDS_LOADER),$(RDS),stream,STREAM=$(STREAM))

shell-rds:
	$(call ssh,$(RDS_LOADER))

psql-rds:
	$(call ssh,$(RDS_LOADER)) "psql -d $(shell $(DSN) $(RDS))"

drop-rds:
	$(call rmake,$(RDS_LOADER),$(RDS),drop)

init-aurora:
	$(call rmake,$(AURORA_LOADER),$(AURORA),os repo)
	$(call rmake,$(AURORA_LOADER),$(AURORA),init)

load-aurora-phase-1: loader-aurora
	$(call tpch,$(AURORA_LOADER),$(AURORA),load aurora 2..10 $(CPU))

load-aurora-phase-2: loader-aurora
	$(call tpch,$(AURORA_LOADER),$(AURORA),load aurora 11..30 $(CPU))

load-aurora-phase-3: loader-aurora
	$(call tpch,$(AURORA_LOADER),$(AURORA),load aurora 31..100 $(CPU))

stream-aurora:
	$(call rmake,$(AURORA_LOADER),$(AURORA),stream,STREAM=$(STREAM))

shell-aurora:
	$(call ssh,$(AURORA_LOADER))

psql-aurora:
	$(call ssh,$(AURORA_LOADER)) "psql -d $(shell $(DSN) $(AURORA))"

drop-aurora:
	$(call rmake,$(AURORA_LOADER),$(AURORA),drop)

cardinalities:
	$(call rmake,$(RDS_LOADER),$(RDS),cardinalities)
	$(call rmake,$(AURORA_LOADER),$(AURORA),cardinalities)

status:
	$(DRIVER) ec2 list
	$(DRIVER) rds list
	$(DRIVER) aurora list

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
	$(DRIVER) ec2 run --json $@

aws.out/%.rds.json:
	$(DRIVER) rds create --json $@

aws.out/%.aurora.json:
	$(DRIVER) aurora create --json $@

.PHONY: loaders list-zones list-amis status
.PHONY: init init-rds init-aurora load
.PHONY: shell-rds shell-aurora psql-rds psql-aurora
.PHONY: stream-rds stream-aurora drop drop-rds drop-aurora
.PHONY: terminate terminate-loaders
.PHONY: tpch tpch-rds tcph-aurora
.PHONY: load-rds-phase-1 load-rds-phase-2 load-rds-phase-3
.PHONY: load-aurora-phase-1 load-aurora-phase-2 load-aurora-phase-3
