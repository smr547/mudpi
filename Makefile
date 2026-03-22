# MudPi infrastructure Makefile
# Location: repository root (mudpi/)

PYTHON := python3
REGISTRY := docs/reference/network-registry.yaml
GENERATOR := tools/generate-network-docs.py
DIAGRAM_GENERATOR := tools/generate-network-diagram.py
OUTPUT := generated
DIAGRAM_OUTPUT := generated/diagrams

.PHONY: help network diagram all clean validate

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
