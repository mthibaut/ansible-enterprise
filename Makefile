# Ansible Enterprise Platform - build automation
# src/  = generator, specs, schemas, scripts (committed)
# build/ = generated Ansible runtime (gitignored)

.PHONY: generate validate all clean test

all: generate validate

generate:
	cd src && python3 generate_ansible_enterprise.py

validate:
	cd src && python3 scripts/verify_repo_contracts.py

test:
	cd src && python3 -m unittest discover -s scripts/tests -p "test_*.py" -v

services:
	cd src && python3 scripts/validate_services_schema.py

checkpoints:
	cd src && python3 scripts/verify_checkpoints.py

order:
	cd src && python3 scripts/resolve_service_order.py

clean:
	rm -rf build/ src/.regen-staging src/.regen-staging-verify

help:
	@echo "make generate    - regenerate build/ from src/"
	@echo "make validate    - run all contract checks"
	@echo "make all         - generate + validate"
	@echo "make services    - validate services schema"
	@echo "make checkpoints - validate checkpoint ordering"
	@echo "make order       - print service dependency order"
	@echo "make clean       - remove build/ and staging dirs"
