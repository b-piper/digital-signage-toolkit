# Monitoring & Fleet Management Guide (Zabbix Edition)

This guide explains how to integrate your Digital Signage kiosks with your campus Zabbix infrastructure.

## 1. Deploy Zabbix Agent (System Monitoring)

We use Ansible to deploy the standard `zabbix-agent` to all kiosks. This provides CPU, Disk, Memory, and Network monitoring.

### Prerequisites
- Zabbix Server hostname/IP known.
- Ansible inventory updated (`monitoring/ansible/inventory/hosts.ini`).

### Deployment
1. Edit `monitoring/ansible/playbooks/deploy-zabbix.yml`:
   ```yaml
   vars:
     zabbix_server: "zabbix.southwesterncc.edu" # Update this!
   ```
2. Run the playbook:
   ```bash
   cd monitoring/ansible
   ansible-playbook -i inventory/hosts.ini playbooks/deploy-zabbix.yml
   ```

## 2. Configure HTTP Monitoring (Application Health)

The Digital Signage Toolkit exposes a health endpoint that Zabbix can monitor directly.

- **URL**: `http://<KIOSK_IP>:8080/health`
- **Method**: GET
- **Auth**: Requires `X-Auth-Token` header.

### Zabbix Setup (HTTP Agent)
Create a new **Item** in Zabbix (or a Template):

| Field | Value |
|-------|-------|
| **Name** | Toolkit Health |
| **Type** | HTTP agent |
| **Key** | `dst.health` |
| **URL** | `http://{HOST.IP}:8080/health` |
| **Headers** | `X-Auth-Token: <YOUR_API_TOKEN>` |
| **Type of information** | Text (or Dependent Item for JSON) |

### Trigger Examples
You can use **JSONPath** Preprocessing to create triggers:

1.  **Rise Vision Down**:
    *   Preprocessing: `$.checks.rise_vision.running`
    *   Trigger: `last(/dst.health) = 0` (False)

2.  **Disk Critical**:
    *   Preprocessing: `$.checks.disk.critical`
    *   Trigger: `last(/dst.health) = 1` (True)

---

## Service Management

### Check Health Manually
```bash
curl -H "X-Auth-Token: secret" http://kiosk-ip:8080/health
```

### Auto-Update
Kiosks check for updates daily at 3:00 AM.
Logs: `/var/log/dst-toolkit/auto-update.log`
