# GPS Disciplined Time Server (MudPi)

MudPi operates a **GPS disciplined network time server** for the home network.
This provides a highly accurate and stable time reference for systems on the
Canberra home LAN and connected VPN networks.

The time server uses:

- GPS receiver for absolute time reference
- PPS (Pulse Per Second) signal for high precision timing
- `gpsd` for GPS device management
- `chrony` for NTP time distribution

This configuration allows MudPi to provide **sub‑millisecond time accuracy**
to devices on the network.

---

# Why a GPS Time Server?

Accurate time is critical for many systems including:

- log correlation
- database timestamps
- monitoring systems
- distributed computing
- VPN authentication
- network troubleshooting

Using GPS provides:

- an independent time source
- high stability
- immunity from internet NTP outages

---

# System Architecture

```
GPS Satellites
      │
      │
GPS Receiver
      │
      ├── NMEA data → gpsd
      │
      └── PPS signal → Raspberry Pi GPIO
                        │
                        │
                     chrony
                        │
                        │
                 LAN NTP Clients
```

---

# Hardware

Typical configuration:

| Component | Description |
|----------|-------------|
| GPS receiver | USB GPS module |
| PPS signal | Pulse per second timing signal |
| Raspberry Pi | MudPi host system |
| GPS antenna | external antenna for better reception |

The PPS signal is typically connected to a Raspberry Pi GPIO pin to allow
precise timestamping by the kernel.

---

# Software Components

## gpsd

`gpsd` manages the GPS receiver and provides:

- NMEA position data
- GPS time data
- PPS synchronization

Example service:

```
gpsd.service
```

---

## chrony

`chrony` is used as the NTP server.

Chrony receives:

- coarse time from GPS
- precision timing from PPS

Chrony then distributes accurate time to LAN clients.

Example service:

```
chronyd.service
```

---

# Example chrony Configuration

Example configuration elements:

```
refclock SHM 0 refid GPS precision 1e-1 offset 0.5 delay 0.2
refclock PPS /dev/pps0 refid PPS precision 1e-7
```

Typical behaviour:

- GPS provides absolute time reference
- PPS disciplines the system clock

---

# Accuracy Expectations

Typical performance:

| Source | Accuracy |
|------|------|
| Internet NTP | 10–50 ms |
| GPS (NMEA only) | ~10 ms |
| GPS + PPS | < 1 ms |

The PPS signal allows the Raspberry Pi kernel to timestamp the second boundary
very accurately.

---

# Network Clients

Devices on the LAN can use MudPi as their NTP server.

Example configuration on a client system:

```
server mudpi iburst
```

Or by IP address:

```
server 10.1.1.x iburst
```

---

# Monitoring

Useful commands:

```
chronyc sources
chronyc tracking
gpsmon
cgps
```

These allow verification of:

- GPS lock
- PPS operation
- time synchronization quality

---

# Failure Modes

Possible issues:

| Problem | Cause |
|------|------|
| No GPS lock | antenna location |
| No PPS | wiring issue |
| Time drift | chrony misconfiguration |

---

# Benefits to the Network

The MudPi GPS time server provides:

- consistent timestamps across systems
- reliable logging
- independence from external NTP servers
- high precision time distribution

---

# Operational status

``
smr@mudpi:~/projects/ddns $ chronyc tracking
Reference ID    : CB1DF17F (ntp-mel.mansfield.id.au)
Stratum         : 3
Ref time (UTC)  : Sat Mar 21 01:47:10 2026
System time     : 0.000069484 seconds fast of NTP time
Last offset     : +0.000071844 seconds
RMS offset      : 0.000276195 seconds
Frequency       : 8.493 ppm fast
Residual freq   : +0.008 ppm
Skew            : 0.056 ppm
Root delay      : 0.022104263 seconds
Root dispersion : 0.002634663 seconds
Update interval : 1031.8 seconds
Leap status     : Normal
smr@mudpi:~/projects/ddns $ smr@mudpi:~/projects/ddns $ chronyc sources
MS Name/IP address         Stratum Poll Reach LastRx Last sample               
===============================================================================
#- GPS                           0   4   377    13   +126ms[ +126ms] +/-  200ms
#* PPS                           0   4   377    14    +35ns[  +81ns] +/-   69ns
^- time.pickworth.net            2  10   377   360  -7011us[-7323us] +/-   49ms
^- syd.clearnet.pw               3  10   377   922  -1107us[-1251us] +/-   65ms
^- pauseq4vntp2.datamossa.io     2  10   377   149   +506us[ +183us] +/-   52ms
^- ntp-mel.mansfield.id.au       2  10   377   534   +849us[ +686us] +/-   13ms
smr@mudpi:~/projects/ddns $ chronyc tracking
Reference ID    : 50505300 (PPS)
Stratum         : 1
Ref time (UTC)  : Sat Mar 21 04:31:21 2026
System time     : 0.000000088 seconds slow of NTP time
Last offset     : -0.000000157 seconds
RMS offset      : 0.000185314 seconds
Frequency       : 8.409 ppm fast
Residual freq   : -0.000 ppm
Skew            : 0.011 ppm
Root delay      : 0.000000001 seconds
Root dispersion : 0.000015150 seconds
Update interval : 16.0 seconds
Leap status     : Normal
smr@mudpi:~/projects/ddns $ 

```



# Related Documentation

See also:

- `SERVICES.md`
- `HARDWARE.md`
- `recovery/rebuild-mudpi.md`
