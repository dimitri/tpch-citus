.SILENT: help
help:
	echo "TPC-H benchmark for PostgreSQL and Citus Data"
	echo "Use ./control.py to drive the benchmark"

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

pep8: pycodestyle ;
pycodestyle:
	pycodestyle --ignore E251,E221,W503 *py tpch/{run,infra,control,}/*.py

.PHONY: list-zones list-amis pep8 pycodestyle help
