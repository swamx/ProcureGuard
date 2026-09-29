PYTHON ?= python
ERP_COMPOSE = docker compose -f infra/erpnext/docker-compose.yml

.PHONY: erp-up erp-down erp-logs erp-rebuild seed reset verify

## Start ERPNext (first start creates the site; takes a few minutes)
erp-up:
	$(ERP_COMPOSE) up -d
	$(ERP_COMPOSE) wait create-site
	$(PYTHON) scripts/erpnext_seed.py wait

## Stop ERPNext, keep data
erp-down:
	$(ERP_COMPOSE) down

erp-logs:
	$(ERP_COMPOSE) logs -f --tail 50

## Delete all ERPNext data, start fresh and seed (clean demo state)
erp-rebuild:
	$(ERP_COMPOSE) down -v
	$(ERP_COMPOSE) up -d
	$(ERP_COMPOSE) wait create-site
	$(PYTHON) scripts/erpnext_seed.py wait
	$(PYTHON) scripts/erpnext_seed.py seed

## Load Nova Industries demo data (idempotent)
seed:
	$(PYTHON) scripts/erpnext_seed.py seed

## Void invoices created by demo runs; keep seeded data
reset:
	$(PYTHON) scripts/erpnext_seed.py reset

## Print the seeded ERPNext state
verify:
	$(PYTHON) scripts/erpnext_seed.py verify
