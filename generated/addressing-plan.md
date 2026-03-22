# Addressing Plan

Generated from `docs/reference/network-registry.yaml`.

## Standard host-role numbering

| Role | Host ID |
| --- | --- |
| Gateway | .1 |
| Primary infrastructure node | .10 |
| Secondary / application host | .20 |
| Utility host | .30 |
| Reserved appliances / sensors | .50–.69 |
| Dynamic DHCP pool | .100–.199 |
| Temporary / manual | .200–.239 |
| Administrative reserve | .240–.254 |

## Address assignment policy

| Device Class | Policy |
| --- | --- |
| Infrastructure hosts | static-on-host |
| Appliances / sensors | dhcp-reservation |
| Mobile clients | dhcp-dynamic |

## Site subnet summary

| Site | Zone | CIDR | Gateway/Hub | DNS Server | DHCP Authority | Search Domain |
| --- | --- | --- | --- | --- | --- | --- |
| reid | reid.home.arpa | 10.1.1.0/24 | 10.1.1.1 | 10.1.1.10 | mudpi | reid.home.arpa |
| barkingowl | barkingowl.home.arpa | 192.168.0.0/24 | 192.168.0.1 | 192.168.0.10 | shedpi | barkingowl.home.arpa |
| trilogy | trilogy.home.arpa | 192.168.98.0/24 | 192.168.98.1 | 192.168.98.10 | boatdns | trilogy.home.arpa |
| testboat | testboat.home.arpa | 192.168.97.0/24 | 192.168.97.1 | 192.168.97.10 | labdns | testboat.home.arpa |
| vpn | vpn.home.arpa | 10.8.1.0/24 | 10.8.1.1 | 10.8.1.1 | — | — |
