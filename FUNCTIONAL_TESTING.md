# Functional Testing Guide

Use this guide to verify the **Application Features** of the Digital Signage Toolkit.

## 1. System Operations
**Goal:** Verify the toolkit can control the device.

1.  **Open the App:** Launch "Digital Signage Toolkit" from the desktop.
2.  **Go to "System Restore" Tab:**
    *   Click "Clear Rise Vision Cache".
        *   **Verify:** Should say "Success" (or "Cache cleared" in logs).
    *   Click "Restart Player".
        *   **Verify:** Since you don't have the player, it might say "Failed" or "Service not found", but acts of trying confirm the button works.
3.  **Go to "Power" (Top Right):**
    *   Click "Reboot System".
    *   **Verify:** Does a confirmation dialog appear? (Don't actually reboot unless you want to).

## 2. Scheduler (Daily Reboot)
**Goal:** Verify the cron job is created.

1.  **Go to "Scheduler" Tab:**
    *   Set "Daily Reboot" to **enabled**.
    *   Set time to `04:15` (Something unique).
    *   Click "Apply Schedule".
2.  **Verify via Terminal:**
    ```bash
    cat /etc/cron.d/dst_reboot
    ```
    *   **Pass Criteria:** File should exist and contain `15 04 * * * root ... /sbin/reboot`.

## 3. Alerts (Email)
**Goal:** Verify the toolkit can send emails.

1.  **Go to "Alerts" Tab:**
    *   Enter a **fake SMTP server** to test the error handling, OR real settings if you have them.
        *   Host: `smtp.gmail.com`
        *   Port: `587`
        *   User: `test@example.com`
        *   Pass: `test`
    *   Click "Send Test Email".
    *   **Verify:** It should attempt to connect and show a Success or Error message.
    *   **Check Logs:** Open the "Logs" tab -> "Application Log". You should see "Attempting to send test email..."

## 4. Installers (TeamViewer / Rise Vision)
**Goal:** Verify the app detects software status.

1.  **Go to "Master Setup" Tab:**
    *   Look at the "Software Installation" section.
    *   **Verify:**
        *   The checkboxes for "Install TeamViewer" and "Install Rise Vision" should be **unchecked** (since you don't have them).
        *   This confirms the detection logic is working.

## 5. Watchdog (Simulation)
**Goal:** Verify the watchdog is active.

1.  **Go to "Watchdog" Tab:**
    *   Enable "Active Monitoring".
    *   Set "Check Interval" to 1 minute.
    *   Click "Save Settings".
2.  **Verify via Terminal:**
    ```bash
    cat /etc/cron.d/dst_watchdog
    ```
    *   **Pass Criteria:** File should exist and run every 1 minute.
