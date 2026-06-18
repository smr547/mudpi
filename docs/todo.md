If I were prioritising:

v3.1
Statistics summary
Generated DNS collision detection
v3.2
--explain-host
Site inventory report
v4
Cross-check generated dnsmasq output against registry

That last one is the "Ferrari" version. It validates not just the registry, but the entire:

registry
   ↓
generator
   ↓
dnsmasq configuration

pipeline. For a system that has become your source of truth, that's where I'd eventually like to get to.

Validator v3.5

- DNS alias collisions are site-scoped.
- FQDN collisions remain globally scoped.
- Reverse DNS authorities must resolve to globally unique FQDNs.


Makefile targets for 

- python3 tools/validate_registry_v3_1_full.py --stats
- python3 tools/validate_registry_v3_1_full.py --site-report
- python3 tools/validate_registry_v3_1_full.py --explain-host stevenlaptop
