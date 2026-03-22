# MudPi infrastructure Makefile
# Location: repository root (mudpi/)
#
# Provides convenient commands for generating network artifacts
# from docs/reference/network-registry.yaml

PYTHON := python3
REGISTRY := docs/reference/network-registry.yaml
GENERATOR := tools/generate-network-docs.py
OUTPUT := generated

.PHONY: help network clean validate

help:
	@echo "MudPi Infrastructure Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  make network   Generate DNS/DHCP/docs artifacts from YAML registry"
	@echo "  make validate  Run generator with validation reporting"
	@echo "  make clean     Remove generated artifacts"
	@echo ""

network:
	@echo "Generating network documentation and configs..."
	$(PYTHON) $(GENERATOR) --registry $(REGISTRY) --output $(OUTPUT)
	@echo "Done. Files written to $(OUTPUT)/"

validate:
	@echo "Validating network registry..."
	$(PYTHON) $(GENERATOR) --registry $(REGISTRY) --output $(OUTPUT) --fail-on-validation

clean:
	@echo "Removing generated artifacts..."
	rm -rf $(OUTPUT)
	@echo "Clean complete."

# Diagram targets
.PHONY: diagram all

DIAGRAM_GENERATOR := tools/generate-network-diagram.py
DIAGRAM_OUTPUT := generated/diagrams

diagram:
	@echo "Generating network diagram..."
	$(PYTHON) $(DIAGRAM_GENERATOR) --registry $(REGISTRY) --output $(DIAGRAM_OUTPUT)
	@echo "Done. Diagram written to $(DIAGRAM_OUTPUT)/"

all: network diagram
