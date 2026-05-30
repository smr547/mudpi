#!/bin/bash

sudo arp-scan --localnet 2>/dev/null   | awk '$1 ~ /^10\.1\.1\.[0-9]+$/ {print $1}'   | sort -Vu   | while read -r ip; do       name=$(dig @127.0.0.1 +short -x "$ip");       printf "%-15s %s\n" "$ip" "${name:-NO-PTR}";     done
