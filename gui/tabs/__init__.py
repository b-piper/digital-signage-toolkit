"""Tab modules for Digital Signage Toolkit GUI."""
from digital_signage_toolkit.gui.tabs.alerts_tab import AlertsTab
from digital_signage_toolkit.gui.tabs.base_tab import BaseTab
from digital_signage_toolkit.gui.tabs.config_tab import ConfigTab
from digital_signage_toolkit.gui.tabs.dashboard_tab import DashboardTab
from digital_signage_toolkit.gui.tabs.disk_cleanup_tab import DiskCleanupTab
from digital_signage_toolkit.gui.tabs.log_viewer_tab import LogViewerTab
from digital_signage_toolkit.gui.tabs.master_setup_tab import MasterSetupTab
from digital_signage_toolkit.gui.tabs.monitoring_tab import MonitoringTab
from digital_signage_toolkit.gui.tabs.os_upgrade_tab import OSUpgradeTab
from digital_signage_toolkit.gui.tabs.restore_tab import RestoreTab
from digital_signage_toolkit.gui.tabs.rise_vision_tab import RiseVisionTab
from digital_signage_toolkit.gui.tabs.scheduler_tab import SchedulerTab
from digital_signage_toolkit.gui.tabs.watchdog_tab import WatchdogTab

__all__ = [
    'BaseTab',
    'DashboardTab',
    'MasterSetupTab',
    'OSUpgradeTab',
    'WatchdogTab',
    'RiseVisionTab',
    'RestoreTab',
    'MonitoringTab',
    'LogViewerTab',
    'SchedulerTab',
    'AlertsTab',
    'ConfigTab',
    'DiskCleanupTab',
]
