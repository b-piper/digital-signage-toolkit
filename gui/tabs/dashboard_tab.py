"""Dashboard tab for Digital Signage Toolkit."""
import os
import shutil
import subprocess
from datetime import datetime

from digital_signage_toolkit.gui.tabs.base_tab import BaseTab
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class DashboardTab(BaseTab):
    """Dashboard landing page with device state detection and at-a-glance status."""

    def __init__(self, main_window):
        super().__init__(main_window)
        self.setup_ui()
        self.refresh_status()

    def setup_ui(self):
        """Set up the Dashboard UI."""
        # Welcome / Identity Section
        identity_group = QGroupBox("Kiosk Identity")
        identity_layout = QVBoxLayout()
        self.identity_label = QLabel("Detecting...")
        self.identity_label.setStyleSheet(
            "font-family: monospace; padding: 12px; color: #e0e0e0; "
            "background-color: #27272a; border: 1px solid #3f3f46; border-radius: 6px;"
        )
        identity_layout.addWidget(self.identity_label)
        identity_group.setLayout(identity_layout)
        self.layout.addWidget(identity_group)

        # Status Cards Grid
        cards_group = QGroupBox("System Status")
        self.cards_layout = QGridLayout()
        self.cards_layout.setSpacing(12)

        # Create status cards
        self.rise_card = self._create_status_card("Rise Vision", "⏳", "Checking...", 0, 0)
        self.watchdog_card = self._create_status_card("Watchdog", "⏳", "Checking...", 0, 1)
        self.teamviewer_card = self._create_status_card("TeamViewer", "⏳", "Checking...", 0, 2)
        self.disk_card = self._create_status_card("Disk Usage", "⏳", "Checking...", 1, 0)
        self.memory_card = self._create_status_card("Memory", "⏳", "Checking...", 1, 1)
        self.version_card = self._create_status_card("Toolkit Version", "⏳", "Checking...", 1, 2)

        cards_group.setLayout(self.cards_layout)
        self.layout.addWidget(cards_group)

        # Quick Actions
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QHBoxLayout()

        self.setup_btn = QPushButton("🚀 Run Master Setup")
        self.setup_btn.setToolTip("Navigate to Master Setup to provision this machine")
        self.setup_btn.clicked.connect(lambda: self._navigate_to("Master Setup"))
        actions_layout.addWidget(self.setup_btn)

        self.monitor_btn = QPushButton("📈 Open Monitoring")
        self.monitor_btn.setToolTip("Navigate to live monitoring")
        self.monitor_btn.clicked.connect(lambda: self._navigate_to("Monitoring"))
        actions_layout.addWidget(self.monitor_btn)

        refresh_btn = QPushButton("🔄 Refresh Status")
        refresh_btn.clicked.connect(self.refresh_status)
        actions_layout.addWidget(refresh_btn)

        actions_group.setLayout(actions_layout)
        self.layout.addWidget(actions_group)

        # Recommendation Banner
        self.recommendation_frame = QFrame()
        self.recommendation_frame.setStyleSheet(
            "background-color: #1e3a5f; border: 1px solid #2563eb; "
            "border-radius: 8px; padding: 16px;"
        )
        rec_layout = QVBoxLayout(self.recommendation_frame)
        self.recommendation_label = QLabel("")
        self.recommendation_label.setWordWrap(True)
        self.recommendation_label.setStyleSheet("color: #93c5fd; font-size: 13px; border: none;")
        rec_layout.addWidget(self.recommendation_label)
        self.layout.addWidget(self.recommendation_frame)

        self.layout.addStretch()

    def _create_status_card(self, title, icon, status_text, row, col):
        """Create a status indicator card."""
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background-color: #27272a; border: 1px solid #3f3f46; "
            "border-radius: 8px; padding: 12px; }"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(4)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #a1a1aa; font-size: 11px; border: none;")
        card_layout.addWidget(title_lbl)

        status_lbl = QLabel(f"{icon} {status_text}")
        status_lbl.setStyleSheet("color: #f4f4f5; font-size: 14px; font-weight: bold; border: none;")
        status_lbl.setObjectName(f"card_status_{title.lower().replace(' ', '_')}")
        card_layout.addWidget(status_lbl)

        self.cards_layout.addWidget(card, row, col)
        return status_lbl

    def _update_card(self, card_label, icon, text, color="#f4f4f5"):
        """Update a status card."""
        card_label.setText(f"{icon} {text}")
        card_label.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold; border: none;")

    def refresh_status(self):
        """Refresh all status indicators."""
        self.set_status("Refreshing dashboard...", "working")

        # Identity
        hostname = self._get_hostname()
        ip_info = self.system_ops.get_active_interface()
        uptime = self.system_ops.get_uptime()
        version = self._get_version()

        identity_text = (
            f"<span style='color:#a1a1aa'>Hostname:</span> <b style='color:#f4f4f5'>{hostname}</b><br>"
            f"<span style='color:#a1a1aa'>IP Address:</span> {ip_info.get('ip', 'Unknown')} "
            f"({ip_info.get('interface', 'Unknown')})<br>"
            f"<span style='color:#a1a1aa'>Uptime:</span> {uptime}<br>"
            f"<span style='color:#a1a1aa'>Version:</span> {version}"
        )
        self.identity_label.setText(identity_text)

        # Status checks
        rise_installed = self._check_rise_vision_installed()
        rise_running = self._check_rise_vision_running()
        watchdog_active = self._check_watchdog_active()
        tv_installed = self._check_teamviewer_installed()
        hostname_set = self._check_hostname_set(hostname)

        # Rise Vision card
        if rise_running:
            self._update_card(self.rise_card, "✅", "Running", "#22c55e")
        elif rise_installed:
            self._update_card(self.rise_card, "⚠️", "Installed (stopped)", "#eab308")
        else:
            self._update_card(self.rise_card, "❌", "Not Installed", "#ef4444")

        # Watchdog card
        if watchdog_active:
            self._update_card(self.watchdog_card, "✅", "Active", "#22c55e")
        else:
            self._update_card(self.watchdog_card, "⏸️", "Inactive", "#a1a1aa")

        # TeamViewer card
        if tv_installed:
            self._update_card(self.teamviewer_card, "✅", "Installed", "#22c55e")
        else:
            self._update_card(self.teamviewer_card, "❌", "Not Installed", "#ef4444")

        # Disk card
        try:
            disk = self.hardware_monitor.get_disk_usage()
            pct = disk.get('percent', 0)
            color = "#ef4444" if pct > 90 else "#eab308" if pct > 80 else "#22c55e"
            self._update_card(self.disk_card, "💾", f"{pct:.0f}% used", color)
        except Exception:
            self._update_card(self.disk_card, "❓", "Unknown", "#a1a1aa")

        # Memory card
        try:
            mem = self.hardware_monitor.get_memory_usage()
            pct = mem.get('percent', 0)
            color = "#ef4444" if pct > 95 else "#eab308" if pct > 85 else "#22c55e"
            self._update_card(self.memory_card, "🧠", f"{pct:.0f}% used", color)
        except Exception:
            self._update_card(self.memory_card, "❓", "Unknown", "#a1a1aa")

        # Version card
        self._update_card(self.version_card, "📦", version or "Unknown", "#a1a1aa")

        # Generate recommendation
        self._update_recommendation(rise_installed, rise_running, watchdog_active, tv_installed, hostname_set)

        self.set_status("Dashboard updated", "success")

    def _update_recommendation(self, rise_installed, rise_running, watchdog_active, tv_installed, hostname_set):
        """Update the recommendation banner based on device state."""
        if not rise_installed or not tv_installed or not hostname_set:
            # Fresh machine — needs setup
            missing = []
            if not hostname_set:
                missing.append("hostname is still the default")
            if not rise_installed:
                missing.append("Rise Vision is not installed")
            if not tv_installed:
                missing.append("TeamViewer is not installed")

            self.recommendation_label.setText(
                f"🔧 <b>This machine needs initial setup.</b><br><br>"
                f"Detected issues: {', '.join(missing)}.<br>"
                f"Use <b>Master Setup</b> to provision this kiosk in one click."
            )
            self.recommendation_frame.setStyleSheet(
                "background-color: #422006; border: 1px solid #f59e0b; "
                "border-radius: 8px; padding: 16px;"
            )
            self.recommendation_label.setStyleSheet("color: #fcd34d; font-size: 13px; border: none;")
            self.setup_btn.setStyleSheet("background-color: #f59e0b; color: #18181b; font-weight: bold;")
        elif not rise_running or not watchdog_active:
            # Configured but needs attention
            issues = []
            if not rise_running:
                issues.append("Rise Vision is not running")
            if not watchdog_active:
                issues.append("Watchdog is inactive")
            self.recommendation_label.setText(
                f"⚠️ <b>This kiosk needs attention.</b><br><br>"
                f"Issues: {', '.join(issues)}.<br>"
                f"Check <b>Watchdog</b> and <b>Rise Vision</b> tabs to resolve."
            )
            self.recommendation_frame.setStyleSheet(
                "background-color: #1e3a5f; border: 1px solid #2563eb; "
                "border-radius: 8px; padding: 16px;"
            )
            self.recommendation_label.setStyleSheet("color: #93c5fd; font-size: 13px; border: none;")
            self.setup_btn.setStyleSheet("")
        else:
            # Everything healthy
            self.recommendation_label.setText(
                "✅ <b>This kiosk is healthy and fully operational.</b><br><br>"
                "All services are running. Use the <b>Monitoring</b> tab for live metrics."
            )
            self.recommendation_frame.setStyleSheet(
                "background-color: #052e16; border: 1px solid #22c55e; "
                "border-radius: 8px; padding: 16px;"
            )
            self.recommendation_label.setStyleSheet("color: #86efac; font-size: 13px; border: none;")
            self.setup_btn.setStyleSheet("")

    def _navigate_to(self, tab_name):
        """Navigate to a named tab via the sidebar."""
        nav_list = self.main_window.nav_list
        for i in range(nav_list.count()):
            item = nav_list.item(i)
            if item and item.text() == tab_name:
                nav_list.setCurrentRow(i)
                return

    # --- Detection Helpers ---

    def _get_hostname(self):
        try:
            return subprocess.getoutput('hostname').strip()
        except Exception:
            return 'unknown'

    def _get_version(self):
        try:
            version_file = '/opt/dst-toolkit/VERSION'
            if os.path.exists(version_file):
                with open(version_file) as f:
                    return f.read().strip()
        except Exception:
            pass
        return self.config.get('version', '2.4.4')

    def _check_rise_vision_installed(self):
        """Check if Rise Vision Player files exist."""
        try:
            home = self.config.get_real_user_home()
            player_dir = os.path.join(home, 'rvplayer')
            return os.path.isdir(player_dir)
        except Exception:
            return False

    def _check_rise_vision_running(self):
        """Check if Rise Vision Player process is running."""
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'Rise Vision'],
                capture_output=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def _check_watchdog_active(self):
        """Check if the watchdog systemd service is active."""
        try:
            status = self.watchdog_manager.get_service_status()
            return status.get('active', False) and status.get('enabled', False)
        except Exception:
            return False

    def _check_teamviewer_installed(self):
        """Check if TeamViewer is installed."""
        return shutil.which('teamviewer') is not None

    def _check_hostname_set(self, hostname):
        """Check if hostname has been changed from default."""
        defaults = ['ubuntu', 'localhost', 'changeme', 'rise']
        return hostname.lower() not in defaults and len(hostname) > 1
