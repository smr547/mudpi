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
