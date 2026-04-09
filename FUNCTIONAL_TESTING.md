# Functional Testing Guide (Updated)

Use this guide to verify the **Application Features** of the Digital Signage Toolkit.

## 1. System Operations (Fixed in v2.2.5)
**Goal:** Verify the toolkit can control the device.

1.  **Open the App:** Launch "Digital Signage Toolkit" from the desktop.
2.  **Go to "System Operations & Restore" Tab (New Name):**
    *   Click "Clear Rise Vision Cache".
        *   **Verify:** Should say "Success".
    *   Click "Restart Player Service".
        *   **Verify:** It updates the status bar.

## 2. Scheduler (Daily Reboot)
**Goal:** Verify the cron job is created.

1.  **Go to "Scheduler" Tab:**
    *   Set "Daily Reboot" to **enabled** (Time: `04:15`).
    *   Click "Apply Schedule".
2.  **Verify via Terminal:**
    ```bash
    cat /etc/cron.d/dst-schedule
    ```
    *   **Pass Criteria:** File should exist and contain `15 04 * * * root /sbin/reboot`.
    *   *(Note: Previous instructions incorrectly said `dst_reboot`).*

## 3. Alerts (Email)
**Goal:** Verify the toolkit can send emails.

1.  **Go to "Alerts" Tab:**
    *   Enter fake SMTP settings (Host: `test`, User: `test`).
    *   Click "Send Test Email".
    *   **Verify:** Error/Success message appears.

## 4. Installers (TeamViewer / Rise Vision)
**Goal:** Verify the app detects software status.

1.  **Go to "Master Setup" Tab:**
    *   **Verify:** Checkboxes state matches installed software.

## 5. Watchdog (Simulation)
**Goal:** Verify the watchdog service is active.

1.  **Go to "Watchdog" Tab:**
    *   Click "Enable Watchdog".
    *   **Verify:** Status label changes to "Active".
2.  **Verify via Terminal:**
    ```bash
    systemctl status rise-vision-player
    ```
    *   **Pass Criteria:** Should show service status.
    *   *(Note: Previous instructions incorrectly said `cron.d/dst_watchdog`).*
