
# MudPi GPS Receiver Hardware (Keyestudio GPS Module)

This document describes the **GPS hardware currently used by MudPi** to provide
a **GPS‑disciplined Stratum‑1 time server** using `gpsd`, `chrony`, and a PPS signal.

The module in use is a [Keyestudio GPS receiver](https://www.jaycar.com.au/arduino-compatible-gps-receiver-module/p/XC3710?gad_source=1&gad_campaignid=22870813861&gbraid=0AAAAAD0dvLZNc5rQvJL_N3ayVJnwvp6y0&gclid=Cj0KCQjw4PPNBhD8ARIsAMo-icxP7II-kawaCODF6QPg-1_EA4VS--xJ3d4s77IFzVK411Uow-fnWqMaAvybEALw_wcB) purchased from Jaycar (~AUD $15).
It is currently used as an **unhoused development module** connected directly to
the Raspberry Pi GPIO header.

This document records the wiring so the system can be rebuilt later.

---

# Hardware Overview

Component | Description
---|---
GPS module | Keyestudio GPS module (UART + PPS output)
Host system | Raspberry Pi 5 (MudPi)
Interface | UART + PPS GPIO
Antenna | Temporary patch antenna with metal ground plane (interim)
Future antenna | External SMA GPS antenna (roof installation planned) -- [Ordered from Core Electronics](https://core-electronics.com.au/gps-antenna-external-active-antenna-3-5v-28db-5-meter-sma.html)

The GPS module provides:

* **NMEA serial data** (time, position, satellite status)
* **PPS (Pulse‑Per‑Second)** signal for high precision timing

Chrony uses:

* GPS NMEA for **coarse time**
* PPS for **precise second boundary**

---

# Wiring Overview

The module connects to the Raspberry Pi using **four wires**:

Signal | Purpose
---|---
VCC | Power for GPS module
GND | Ground reference
TX | GPS serial data → Raspberry Pi RX
PPS | Precision timing pulse → GPIO interrupt

---

# Typical Wiring (Keyestudio → Raspberry Pi 5)

Keyestudio Pin | Function | Raspberry Pi GPIO Pin | Pin Number
---|---|---|---
VCC | 5V power | 5V | Pin 2 or 4
GND | Ground | GND | Pin 6
TX | UART transmit (GPS → Pi) | GPIO15 / RXD | Pin 10
PPS | Pulse‑per‑second output | GPIO18 (commonly used) | Pin 12

Only **four wires are required** for a functional GPS+PPS time server.

---

# Wiring Diagram

```
Keyestudio GPS Module                Raspberry Pi 5 GPIO Header

      VCC  ------------------------>  5V (Pin 2)

      GND  ------------------------>  GND (Pin 6)

      TX   ------------------------>  GPIO15 / RXD (Pin 10)

      PPS  ------------------------>  GPIO18 (Pin 12)
```

---

# GPIO Header Reference (Pi 5)

```
Raspberry Pi 40‑pin header (partial)

 (3V3) 1  2 (5V)
 (GPIO2)3  4 (5V)
 (GPIO3)5  6 (GND)
 (GPIO4)7  8 (TXD)
 (GND) 9 10 (RXD)   ← GPS TX connects here
(GPIO17)11 12(GPIO18) ← PPS often connected here
```

---

# Serial Device

When connected via the Pi UART, the GPS typically appears as:

```
/dev/ttyAMA0
```

depending on the Pi configuration.

This device is used by **gpsd**.

---

# PPS Device

When the PPS signal is correctly configured, Linux creates:

```
/dev/pps0
```

This device is used by **chrony** for precision timing.

Verify with:

```bash
ls /dev/pps*
```

---

# Verifying GPS Operation

Check GPS data:

```bash
cgps
```

or

```bash
gpsmon
```

Verify PPS pulses:

```bash
ppstest /dev/pps0
```

---

# Verifying Chrony Synchronisation

```bash
chronyc sources
chronyc tracking
```

Expected result:

```
#* PPS
#+ GPS
```

This indicates:

* PPS is the primary reference clock
* GPS provides time‑of‑day

MudPi then operates as a **Stratum‑1 time server**.

---

# Ground Plane Note

Small patch GPS antennas require a **ground plane** for best performance.

A metal plate placed beneath the antenna dramatically improved satellite lock
during early testing.

This behaviour is expected for many patch antennas.

---

# Future Improvements

Planned improvements include:

* External **SMA active GPS antenna**
* Antenna mounted in **roof space under terracotta tiles**
* Proper enclosure for GPS module
* Short shielded PPS lead to GPIO

---

# Repository Location

This document should be stored at:

```
services/gps-timeserver/hardware-keyestudio-gps.md
```
