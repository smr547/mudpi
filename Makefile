# MudPi infrastructure Makefile
# Location: repository root (mudpi/)



PYTHON := python3
REGISTRY := docs/reference/network-registry.yaml
# GENERATOR := tools/generate-network-docs.py
DIAGRAM_GENERATOR := tools/generate-network-diagram.py
OUTPUT := generated
DIAGRAM_OUTPUT := generated/diagrams

.PHONY: help network diagram all clean validate


# --- DNS/DHCP generation and preflight ---------------------------------------

PYTHON ?= python3
REGISTRY ?= docs/reference/network-registry.yaml
DNS_GEN ?= tools/generate_dnsmasq.py
DHCP_GEN ?= tools/generate_dhcp_dnsmasq.py
GEN_ROOT ?= generated/dnsmasq

REID_CIDR ?= 10.1.1.0/24
REID_RANGE_START ?= 10.1.1.100
REID_RANGE_END ?= 10.1.1.199
REID_ROUTER ?= 10.1.1.1
REID_DNS ?= 10.1.1.3
REID_DOMAIN ?= reid.home.arpa

FARM_CIDR ?= 192.168.0.0/24
FARM_RANGE_START ?= 192.168.0.100
FARM_RANGE_END ?= 192.168.0.199
FARM_ROUTER ?= 192.168.0.1
FARM_DNS ?= 192.168.0.210
FARM_DOMAIN ?= farm.home.arpa

.PHONY: dnsmasq build-dnsmasq preflight preflight-dnsmasq deploy-reid-dnsmasq deploy-farm-dnsmasq clean-dnsmasq

dnsmasq: build-dnsmasq

build-dnsmasq:
	@echo "==> Building DNS zone: reid"
	$(PYTHON) $(DNS_GEN) \
	  --registry $(REGISTRY) \
	  --site reid \
	  --domain $(REID_DOMAIN) \
	  --interfaces eth0 \
	  --install-root /etc/dnsmasq.d/generated \
	  --outdir $(GEN_ROOT)/reid

	@echo "==> Building DHCP config: reid"
	$(PYTHON) $(DHCP_GEN) \
	  --registry $(REGISTRY) \
	  --site reid \
	  --outdir $(GEN_ROOT) \
	  --interface eth0 \
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
	  --interfaces eth0 \
	  --install-root /etc/dnsmasq.d/generated \
	  --outdir $(GEN_ROOT)/farm

	@echo "==> Building DHCP config: farm"
	$(PYTHON) $(DHCP_GEN) \
	  --registry $(REGISTRY) \
	  --site farm \
	  --outdir $(GEN_ROOT) \
	  --interface eth0 \
	  --cidr $(FARM_CIDR) \
	  --range-start $(FARM_RANGE_START) \
	  --range-end $(FARM_RANGE_END) \
	  --router $(FARM_ROUTER) \
	  --dns-server $(FARM_DNS) \
	  --domain $(FARM_DOMAIN)

	@echo "==> Build complete"

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
	  elif [ -f "$(GEN_ROOT)/$$site/warnings.txt" ] && [ -f "$(GEN_ROOT)/$$site/dhcp.conf" ]; then echo "(DHCP warnings may be sharing warnings.txt)"; \
	  else echo "No DHCP warnings file"; fi; \
	  echo; \
	done

deploy-reid-dnsmasq: preflight-dnsmasq
	@./tools/deploy_mudpi_dns.sh

deploy-farm-dnsmasq: preflight-dnsmasq
	@./tools/deploy_dnsmasq.sh farm

clean-dnsmasq:
	rm -rf $(GEN_ROOT)/reid $(GEN_ROOT)/farm $(GEN_ROOT)/preflight-report.txt

help:
	@echo "MudPi Infrastructure Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  make network   Generate DNS/DHCP/docs artifacts from YAML registry"
	@echo "  make diagram   Generate overview and full network diagrams"
	@echo "  make all       Generate both docs/config artifacts and diagrams"
	@echo "  make validate  Run generator with validation reporting"
	@echo "  make clean     Remove generated artifacts"
	@echo ""

network:
	@echo "Generating network documentation and configs..."
	$(PYTHON) $(GENERATOR) --registry $(REGISTRY) --output $(OUTPUT)
	@echo "Done. Files written to $(OUTPUT)/"

diagram:
	@echo "Generating network diagrams..."
	$(PYTHON) $(DIAGRAM_GENERATOR) --registry $(REGISTRY) --output $(DIAGRAM_OUTPUT)
	@echo "Done. Files written to $(DIAGRAM_OUTPUT)/"

all: network diagram

validate:
	@echo "Validating network registry..."
	$(PYTHON) $(GENERATOR) --registry $(REGISTRY) --output $(OUTPUT) --fail-on-validation

clean:
	@echo "Removing generated artifacts..."
	rm -rf $(OUTPUT)
	@echo "Clean complete."


.PHONY: leases-report

leases-report:
	@python3 tools/report_dnsmasq_leases.py \
	  --registry docs/reference/network-registry.yaml \
	  --leases /var/lib/misc/dnsmasq.leases

.PHONY: leases-report-verbose
leases-report-verbose:
	@python3 tools/report_dnsmasq_leases.py \
	  --registry docs/reference/network-registry.yaml \
	  --leases /var/lib/misc/dnsmasq.leases \
	  --show-client-id

.PHONY: leases-unknown-stubs

leases-unknown-stubs:
	@python3 tools/report_unknown_dhcp_stubs.py \
	  --registry docs/reference/network-registry.yaml \
	  --leases /var/lib/misc/dnsmasq.leases \
	  --site reid

.PHONY: farm-leases-unknown-stubs

farm-leases-unknown-stubs:
	@python3 tools/report_unknown_dhcp_stubs.py \
	  --registry docs/reference/network-registry.yaml \
	  --leases /var/lib/misc/dnsmasq.leases \
	  --site farm
