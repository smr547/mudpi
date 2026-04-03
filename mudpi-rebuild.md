# MudPi Rebuild Guide

## Purpose

This document describes how to rebuild the MudPi system from scratch in the event of hardware failure.

It is designed so that Irene or PJ (with basic Linux familiarity) can restore the system to a working state.

---

## Overview

MudPi is designed as a declarative system:

- The source of truth is the Git repository (network-registry.yaml and tools)
- Configuration is generated, not manually created
- The running system (dnsmasq) is a deployment artifact

Rebuild strategy:

Fresh OS → Install packages → Clone repo → Deploy config → Restart services

---

## Prerequisites

- Raspberry Pi (preferably Pi 5 with NVMe, but any compatible Pi will work)
- Network connection (Ethernet preferred)
- Access to Git repository
- Basic Linux terminal access

---

## Step 1 — Install Operating System

1. Install Raspberry Pi OS (Lite) or Debian
2. Boot the system
3. Login via console or SSH

---

## Step 2 — Basic System Setup

Set hostname:

    sudo hostnamectl set-hostname mudpi

Update system:

    sudo apt update
    sudo apt upgrade -y

---

## Step 3 — Install Required Packages

    sudo apt install -y dnsmasq git

---

## Step 4 — Clone Repository

    cd ~
    git clone <YOUR-REPO-URL> mudpi
    cd mudpi

---

## Step 5 — Generate DNS Configuration

    python3 ./tools/generate_dnsmasq.py \
      --registry docs/reference/network-registry.yaml \
      --site reid \
      --outdir generate/dnsmasq

---

## Step 6 — Deploy Configuration

    sudo cp /etc/dnsmasq.conf /etc/dnsmasq.conf.backup 2>/dev/null || true

    sudo cp generate/dnsmasq/hosts.conf /etc/dnsmasq.d/
    sudo cp generate/dnsmasq/aliases.conf /etc/dnsmasq.d/
    sudo cp generate/dnsmasq/reverse.conf /etc/dnsmasq.d/

    sudo cp configs/dnsmasq.conf /etc/dnsmasq.conf

---

## Step 7 — Restart DNS Service

    sudo dnsmasq --test
    sudo systemctl restart dnsmasq
    sudo systemctl enable dnsmasq

---

## Step 8 — Verify Operation

    dig mudpi.reid.home.arpa
    dig shorepi.reid.home.arpa
    dig google.com

---

## Step 9 — Verify Network Role

Ensure MudPi is reachable at:

    10.1.1.3

Test:

    dig @10.1.1.3 google.com

---

## Troubleshooting

Check dnsmasq status:

    systemctl status dnsmasq

Check logs:

    tail -f /var/log/dnsmasq.log

Check listening ports:

    ss -lntup | grep :53

---

## Backup Notes

Critical items:

- Repository (~/mudpi)
- /etc/dnsmasq.conf
- /etc/dnsmasq.d/

Backup command:

    tar czf mudpi-backup.tar.gz \
      /etc/dnsmasq.conf \
      /etc/dnsmasq.d \
      ~/mudpi

---

## Design Principles

- Single source of truth: network-registry.yaml
- Generated configuration only
- Explicit DNS policy (no router dependency)
- Deterministic naming

---

## Summary

Rebuild steps:

1. Install OS  
2. Install dnsmasq + git  
3. Clone repo  
4. Generate config  
5. Restart dnsmasq  

The system should be fully operational within minutes.
