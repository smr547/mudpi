# MudPi infrastructure Makefile
# Location: repository root: mudpi/

SHELL := /bin/bash

PYTHON ?= python3
REGISTRY ?= docs/reference/network-registry.yaml

OUTPUT ?= generated
GEN_ROOT ?= generated/dnsmasq

DNS_GEN ?= tools/generate_dnsmasq.py
DHCP_GEN ?= tools/generate_dhcp_dnsmasq.py
VALIDATOR ?= tools/validate_registry.py
DIAGRAM_GENERATOR ?= tools/generate-network-diagram.py

# Reid / home site
REID_IFACE ?= eth0
REID_CIDR ?= 10.1.1.0/24
REID_RANGE_START ?= 10.1.1.200
REID_RANGE_END ?= 10.1.1.249
REID_ROUTER ?= 10.1.1.1
REID_DNS ?= 10.1.1.3
REID_DOMAIN ?= reid.home.arpa

# Farm / Barking Owl site
FARM_IFACE ?= eth0
FARM_CIDR ?= 192.168.0.0/24
FARM_RANGE_START ?= 192.168.0.230
FARM_RANGE_END ?= 192.168.0.249
FARM_ROUTER ?= 192.168.0.1
FARM_DNS ?= 192.168.0.210
FARM_DOMAIN ?= farm.home.arpa

.PHONY: help
help:
	@echo "MudPi Infrastructure Makefile"
	@echo ""
	@echo "Operational DNS/DHCP workflow:"
	@echo "  make preflight-dnsmasq       Generate and review DNS/DHCP artifacts"
	@echo "  make build-dnsmasq           Generate DNS/DHCP artifacts only"
	@echo "  make deploy-reid-dnsmasq     Deploy Reid/Home dnsmasq configuration"
	@echo "  make deploy-farm-dnsmasq     Deploy Farm/Barking Owl dnsmasq configuration"
	@echo ""
	@echo "Reports:"
	@echo "  make leases-report           Report dnsmasq leases"
	@echo "  make leases-report-verbose   Report dnsmasq leases with client IDs"
	@echo "  make leases-unknown-stubs    Generate YAML stubs for unknown Reid leases"
	@echo "  make farm-leases-unknown-stubs Generate YAML stubs for unknown Farm leases"
	@echo "  make arp-report              Show ARP report"
	@echo "  make unifi-clients           Show UniFi wireless clients"
	@echo "  make network-census          Run live network census"
	@echo ""
	@echo "Other:"
	@echo "  make diagram                 Generate network diagrams"
	@echo "  make clean-dnsmasq           Remove generated dnsmasq artifacts"
	@echo "  make clean                   Remove all generated artifacts"
	@echo ""
	@echo "Temporarily disabled:"
	@echo "  make network"
	@echo "  make validate"
	@echo "  make wg"
	@echo "  make wg-enroll"

.PHONY: dnsmasq build-dnsmasq
dnsmasq: build-dnsmasq

build-dnsmasq:
	@echo "==> Building DNS zone: reid"
	$(PYTHON) $(DNS_GEN) \
	  --registry $(REGISTRY) \
	  --site reid \
	  --domain $(REID_DOMAIN) \
	  --interfaces $(REID_IFACE) \
	  --install-root /etc/dnsmasq.d/generated \
	  --outdir $(GEN_ROOT)/reid

	@echo "==> Building DHCP config: reid"
	$(PYTHON) $(DHCP_GEN) \
	  --registry $(REGISTRY) \
	  --site reid \
	  --outdir $(GEN_ROOT) \
	  --interface $(REID_IFACE) \
	  --cidr $(REID_CIDR) \
	  --range-start $(REID_RANGE_START) \
	  --range-end $(REID_RANGE_END) \
	  --router $(REID_ROUTER) \
	  --dns-server $(REID_DNS) \
	  --domain $(REID_DOMAIN)

	@echo "==> Building DNS zone: farm"
	$(PYTHON) $(DNS_GEN) \
	  --registry $(REGISTRY) \
	  --site farm \
	  --domain $(FARM_DOMAIN) \
	  --interfaces $(FARM_IFACE) \
	  --install-root /etc/dnsmasq.d/generated \
	  --outdir $(GEN_ROOT)/farm

	@echo "==> Building DHCP config: farm"
	$(PYTHON) $(DHCP_GEN) \
	  --registry $(REGISTRY) \
	  --site farm \
	  --outdir $(GEN_ROOT) \
	  --interface $(FARM_IFACE) \
	  --cidr $(FARM_CIDR) \
	  --range-start $(FARM_RANGE_START) \
	  --range-end $(FARM_RANGE_END) \
	  --router $(FARM_ROUTER) \
	  --dns-server $(FARM_DNS) \
	  --domain $(FARM_DOMAIN)

	@echo "==> DNS/DHCP build complete"

.PHONY: preflight preflight-dnsmasq
preflight: preflight-dnsmasq

preflight-dnsmasq: build-dnsmasq
	@mkdir -p $(GEN_ROOT)
	@REPORT="$(GEN_ROOT)/preflight-report.txt"; \
	echo "# dnsmasq preflight validation report" > "$$REPORT"; \
	echo "# registry: $(REGISTRY)" >> "$$REPORT"; \
	echo "# generated: $$(date -Is)" >> "$$REPORT"; \
	echo >> "$$REPORT"; \
	for site in reid farm; do \
	  echo "## $$site" >> "$$REPORT"; \
	  for f in zone.conf hosts.conf aliases.conf reverse.conf authoritative.hosts dhcp.conf warnings.txt warnings_dns.txt warnings_dhcp.txt leases-summary.txt summary.txt; do \
	    if [ -f "$(GEN_ROOT)/$$site/$$f" ]; then \
	      echo "### $$f" >> "$$REPORT"; \
	      cat "$(GEN_ROOT)/$$site/$$f" >> "$$REPORT"; \
	      echo >> "$$REPORT"; \
	    fi; \
	  done; \
	done; \
	echo "Preflight report written to $$REPORT"

	@echo "==> Required artifact checks"
	@test -f $(GEN_ROOT)/reid/zone.conf
	@test -f $(GEN_ROOT)/reid/dhcp.conf
	@test -f $(GEN_ROOT)/farm/zone.conf
	@test -f $(GEN_ROOT)/farm/dhcp.conf

	@echo "==> Concise warning summary"
	@for site in reid farm; do \
	  echo "-- $$site --"; \
	  if [ -f "$(GEN_ROOT)/$$site/warnings_dns.txt" ]; then cat "$(GEN_ROOT)/$$site/warnings_dns.txt"; \
	  elif [ -f "$(GEN_ROOT)/$$site/warnings.txt" ]; then cat "$(GEN_ROOT)/$$site/warnings.txt"; \
	  else echo "No DNS warnings file"; fi; \
	  if [ -f "$(GEN_ROOT)/$$site/warnings_dhcp.txt" ]; then cat "$(GEN_ROOT)/$$site/warnings_dhcp.txt"; \
	  else echo "No DHCP warnings file"; fi; \
	  echo; \
	done

.PHONY: deploy-reid-dnsmasq deploy-farm-dnsmasq
deploy-reid-dnsmasq: preflight-dnsmasq
	@./tools/deploy_mudpi_dns.sh

deploy-farm-dnsmasq: preflight-dnsmasq
	@./tools/deploy_dnsmasq.sh farm

.PHONY: leases-report leases-report-verbose
leases-report:
	@$(PYTHON) tools/report_dnsmasq_leases.py \
	  --registry $(REGISTRY) \
	  --leases /var/lib/misc/dnsmasq.leases

leases-report-verbose:
	@$(PYTHON) tools/report_dnsmasq_leases.py \
	  --registry $(REGISTRY) \
	  --leases /var/lib/misc/dnsmasq.leases \
	  --show-client-id

.PHONY: leases-unknown-stubs farm-leases-unknown-stubs
leases-unknown-stubs:
	@$(PYTHON) tools/report_unknown_dhcp_stubs.py \
	  --registry $(REGISTRY) \
	  --leases /var/lib/misc/dnsmasq.leases \
	  --site reid

farm-leases-unknown-stubs:
	@$(PYTHON) tools/report_unknown_dhcp_stubs.py \
	  --registry $(REGISTRY) \
	  --leases /var/lib/misc/dnsmasq.leases \
	  --site farm

.PHONY: arp-report unifi-clients network-census
arp-report:
	@./tools/arp-report.sh

unifi-clients:
	@./tools/unifi_clients_dns.py

network-census:
	@./tools/network_census.py

.PHONY: diagram
diagram:
	@echo "Generating network diagrams..."
	$(PYTHON) $(DIAGRAM_GENERATOR) --registry $(REGISTRY) --output generated/diagrams
	@echo "Done. Files written to generated/diagrams/"

.PHONY: clean clean-dnsmasq
clean-dnsmasq:
	rm -rf $(GEN_ROOT)/reid $(GEN_ROOT)/farm $(GEN_ROOT)/preflight-report.txt

clean:
	@echo "Removing generated artifacts..."
	rm -rf $(OUTPUT)
	@echo "Clean complete."

# ---------------------------------------------------------------------------
# Temporarily disabled targets.
# These scripts are known to be stale relative to the current registry schema.
# ---------------------------------------------------------------------------

.PHONY: network validate
network:
	@echo "DISABLED: tools/generate-network-docs.py is outdated relative to current YAML schema."
	@false

#
# Registry validation
#

validate:
	python3 $(VALIDATOR)

validate-stats:
	python3 $(VALIDATOR) --stats

validate-sites:
	python3 $(VALIDATOR) --site-report

validate-host:
	@if [ -z "$(HOST)" ]; then \
		echo "Usage: make validate-host HOST=stevenlaptop"; \
		exit 1; \
	fi
	python3 $(VALIDATOR) --explain-host $(HOST)
# ---------------------------------------------------------------------------
# WireGuard is deliberately parked for now.
# ---------------------------------------------------------------------------

.PHONY: wg wg-enroll
wg:
	@echo "DISABLED: WireGuard tooling is work in progress."
	@false

wg-enroll:
	@echo "DISABLED: WireGuard peer enrolment is work in progress."
	@false
