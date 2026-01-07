# Digital Signage Kiosk Monitoring - Network Configuration Request

**From:** IT Department  
**To:** Network Administration  
**Date:** January 2026  
**Subject:** Network Configuration for Digital Signage Monitoring System

---

## Executive Summary

We are implementing a monitoring and management system for our 20 digital signage kiosks across campus. This document outlines the network configuration needed and addresses security considerations.

**Key Point:** This setup follows security best practices by using **one-way communication** (management → kiosks only), meaning kiosks cannot initiate any connections back to our management network.

---

## Requested Configuration

### 1. DHCP Reservations (Meraki)

**Purpose:** Assign consistent IP addresses to kiosks for reliable monitoring

**Action Required:**
- Create fixed IP assignments for each kiosk in Meraki Dashboard
- Location: Security & SD-WAN → Addressing & VLANs → Fixed IP assignments
- We will provide: Kiosk names and MAC addresses

**Security Impact:** None - this is standard DHCP configuration

---

### 2. Firewall Rules

**Purpose:** Allow management access to kiosks while maintaining network segmentation

#### Required Rules

| # | Source | Destination | Ports | Direction | Purpose |
|---|--------|-------------|-------|-----------|---------|
| 1 | Management VLAN | Kiosk VLAN | TCP 22 | Outbound only | SSH management |
| 2 | Management VLAN | Kiosk VLAN | TCP 8080 | Outbound only | Health monitoring |
| 3 | Management VLAN | Kiosk VLAN | TCP 9100 | Outbound only | Prometheus metrics (future) |

#### Deny Rules (Confirm Existing)

| # | Source | Destination | Ports | Action | Purpose |
|---|--------|-------------|-------|--------|---------|
| 4 | Kiosk VLAN | Management VLAN | ALL | **DENY** | Prevent kiosk→management access |
| 5 | Kiosk VLAN | Other internal VLANs | ALL | **DENY** | Prevent lateral movement |

---

### 3. Future: Monitoring Server (Pending Approval)

If a dedicated monitoring server is approved:

| Requirement | Specification |
|-------------|---------------|
| Operating System | Ubuntu 20.04 LTS or Debian 11 |
| CPU | 2 cores |
| RAM | 4 GB |
| Disk | 50 GB |
| Network | Access to Kiosk VLAN |

**Additional ports to allow from this server:**
- TCP 9090 (Prometheus)
- TCP 3000 (Grafana dashboards)

---

### 4. SMTP Access (Optional)

For email alerting when kiosks go offline:

**Information needed:**
- Internal SMTP relay hostname
- Port (25, 587, or 465)
- Authentication requirements

---

## Security Analysis

### Why This Is Secure

#### 1. One-Way Communication Model

```
┌─────────────────────┐          ┌─────────────────────┐
│  Management VLAN    │          │    Kiosk VLAN       │
│  (Trusted)          │          │    (Restricted)     │
│                     │          │                     │
│   Your PC ──────────────────────────► Kiosk         │
│                     │  SSH, HTTP │                   │
│                     │  (ALLOWED) │                   │
│                     │          │                     │
│   Your PC ◄─────────────────────────X Kiosk         │
│                     │  (BLOCKED) │                   │
└─────────────────────┘          └─────────────────────┘
```

**All connections are initiated FROM the management VLAN TO the kiosks.** Kiosks are passive responders only. They never initiate outbound connections to our internal network.

#### 2. What Each Port Exposes

| Port | Service | Data Exposed | Write Access | Risk Level |
|------|---------|--------------|--------------|------------|
| 22 | SSH | Shell access | Yes (authenticated) | Low with SSH keys |
| 8080 | Health API | System stats only | None | Minimal |
| 9100 | Metrics | CPU/RAM/disk stats | None | Minimal |

**Port 8080 Example Response:**
```json
{
  "healthy": true,
  "hostname": "kiosk-library",
  "disk": {"percent": 45},
  "memory": {"percent": 32}
}
```

No credentials, no PII, no sensitive data - just hardware metrics.

#### 3. Attack Vector Analysis

| Scenario | Can It Happen? | Why/Why Not |
|----------|----------------|-------------|
| Hacked kiosk attacks management network | **No** | Firewall blocks kiosk→management traffic |
| Hacked kiosk accesses other VLANs | **No** | Firewall blocks kiosk→other VLAN traffic |
| Attacker on kiosk VLAN reads health data | **Low risk** | Only sees hostname and hardware stats |
| Attacker bruteforces SSH | **Mitigated** | Using SSH keys (no passwords) + rate limiting |
| Man-in-the-middle on updates | **No** | Updates via HTTPS from GitHub |

#### 4. Compliance Considerations

| Requirement | How We Meet It |
|-------------|----------------|
| Network segmentation | Kiosks on separate VLAN, one-way access only |
| Principle of least privilege | Only necessary ports opened, specific direction |
| Audit logging | All privileged operations logged on kiosks |
| Secure communication | SSH encrypted, HTTPS for updates |
| No student data exposure | Kiosks don't store or transmit student data |

---

## Risk Summary

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Kiosk compromise leading to network breach | **Very Low** | High | One-way firewall rules, VLAN isolation |
| SSH unauthorized access | **Low** | Medium | SSH key authentication, no passwords |
| Health endpoint information disclosure | **Very Low** | Low | No sensitive data exposed |
| Service disruption | **Low** | Low | Monitoring provides early warning |

---

## Comparison to Industry Standards

This configuration follows the same security model used by:

- **Enterprise IoT deployments** - Devices in restricted VLANs, management from trusted network
- **PCI-DSS compliant kiosk systems** - Network segmentation with controlled access
- **Healthcare digital signage** - HIPAA-compliant isolated display networks

---

## Summary

| What We're Asking | Security Impact |
|-------------------|-----------------|
| DHCP reservations | None |
| Management → Kiosk firewall rules (3 ports) | Low - one-way, authenticated access |
| Confirm Kiosk → Management is blocked | Critical - maintains security boundary |

**This setup maintains our existing security posture while enabling remote management.** The kiosk VLAN remains isolated and cannot be used to access the management network or other internal resources.

---

## Questions?

Contact: [Your Name]  
Department: IT  
Extension: [Your Extension]

---

*Document prepared for Southwestern Community College IT Department*
