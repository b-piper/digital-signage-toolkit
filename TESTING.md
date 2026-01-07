# Digital Signage Toolkit - comprehensive Test Plan

Use this guide to validate the Digital Signage Toolkit v2.2.1+ on a test device (e.g., Ubuntu VM).

## 1. Installation & Setup

**Goal:** Verify a clean installation works and sets up all components.

1.  **Run Installer:**
    ```bash
    curl -sSL https://raw.githubusercontent.com/b-piper/digital-signage-toolkit/main/install-remote.sh | sudo bash
    ```
    *   **Pass Criteria:** Script completes without errors.
    *   **Check:** `dpkg -l dst-toolkit` shows version `2.2.1` (or latest).

2.  **Verify Files:**
    ```bash
    ls -l /opt/dst-toolkit/
    ```
    *   **Pass Criteria:** `main.py`, `venv/`, `scripts/`, `VERSION` exist.

3.  **Verify Icon:**
    *   Check your Application Launcher (Super/Windows key -> type "Digital").
    *   **Pass Criteria:** "Digital Signage Toolkit" appears with the blue SCC logo.

---

## 2. Service Health & API

**Goal:** Verify the background monitor and health endpoint are running.

1.  **Check Service Status:**
    (Note: The main `dst-toolkit` GUI must be running for the health server to start, OR you can run it headless)
    ```bash
    # Run headless if not using GUI
    sudo /opt/dst-toolkit/venv/bin/python /opt/dst-toolkit/main.py --no-gui &
    ```
    *   **Check:** `pgrep -f "main.py"` should show a PID.

2.  **Test Health Endpoint:**
    ```bash
    curl http://localhost:8080/health
    ```
    *   **Pass Criteria:** returns JSON with `"healthy": true`.

3.  **Test Metrics Endpoint:**
    ```bash
    curl http://localhost:8080/metrics
    ```
    *   **Pass Criteria:** returns plain text Prometheus metrics (e.g., `dst_memory_usage_percent`).

---

## 3. Auto-Update System

**Goal:** Ensure the daily update mechanism is active.

1.  **Check Systemd Timer:**
    ```bash
    systemctl status dst-auto-update.timer
    ```
    *   **Pass Criteria:** Status is `active (waiting)` and mentions `Trigger: [Date] 03:00:00`.

2.  **Manual Update Test:**
    ```bash
    sudo /opt/dst-toolkit/scripts/auto-update.sh
    ```
    *   **Pass Criteria:** Script runs, checks GitHub, reports "You are already on the latest version" (or updates if needed), and exits cleanly. log file `/var/log/dst-toolkit/auto-update.log` is updated.

---

## 4. Headless Management Commands

**Goal:** Verify CLI tools used for remote management.

1.  **Check Status:**
    ```bash
    dst-toolkit --status
    ```
    *   **Pass Criteria:** Returns JSON with system info (hostname, disk, internet, etc.).

2.  **Test Heal:**
    ```bash
    dst-toolkit --heal
    ```
    *   **Pass Criteria:** Returns success message, clears cache (if Rise Vision installed), logs to `/var/log/dst-toolkit/application.log`.

3.  **Screenshot (Mock):**
    ```bash
    dst-toolkit --screenshot /tmp/test.png
    ```
    *   **Pass Criteria:** Generates `/tmp/test.png` (might be black/empty if no display, but command should succeed).

---

## 5. Fleet Monitoring (Simulated)

**Goal:** Test the fleet monitoring script from a "manager" perspective.

1.  **Run Fleet Check:**
    ```bash
    # You might need to edit /opt/dst-toolkit/scripts/check-fleet.sh first to add 'localhost:127.0.0.1' to KIOSKS array for testing
    /opt/dst-toolkit/scripts/check-fleet.sh
    ```
    *   **Pass Criteria:** Shows a status table with your local machine listed as "OK".

---

## 6. Security Verification

**Goal:** Confirm only expected ports are open.

1.  **Check Listening Ports:**
    ```bash
    sudo ss -tulnp
    ```
    *   **Pass Criteria:**
        *   Port `8080` (python/main.py) is LISTEN.
        *   Port `22` (sshd) is LISTEN.
        *   (Optional) Port `9100` (node_exporter) if installed.
        *   No other unexpected ports exposed externally.
