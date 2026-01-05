"""Tab modules for Digital Signage Toolkit GUI."""
from digital_signage_toolkit.gui.tabs.base_tab import BaseTab
from digital_signage_toolkit.gui.tabs.master_setup_tab import MasterSetupTab
from digital_signage_toolkit.gui.tabs.audit_fix_tab import AuditFixTab
from digital_signage_toolkit.gui.tabs.os_upgrade_tab import OSUpgradeTab
from digital_signage_toolkit.gui.tabs.watchdog_tab import WatchdogTab
from digital_signage_toolkit.gui.tabs.restore_tab import RestoreTab
from digital_signage_toolkit.gui.tabs.monitoring_tab import MonitoringTab
from digital_signage_toolkit.gui.tabs.log_viewer_tab import LogViewerTab
from digital_signage_toolkit.gui.tabs.scheduler_tab import SchedulerTab
from digital_signage_toolkit.gui.tabs.alerts_tab import AlertsTab

__all__ = [
    'BaseTab',
    'MasterSetupTab',
    'AuditFixTab',
    'OSUpgradeTab',
    'WatchdogTab',
    'RestoreTab',
    'MonitoringTab',
    'LogViewerTab',
    'SchedulerTab',
    'AlertsTab',
]
