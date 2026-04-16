"""Tab modules for Digital Signage Toolkit GUI."""
from .alerts_tab import AlertsTab
from .base_tab import BaseTab
from .config_tab import ConfigTab
from .dashboard_tab import DashboardTab
from .disk_cleanup_tab import DiskCleanupTab
from .log_viewer_tab import LogViewerTab
from .master_setup_tab import MasterSetupTab
from .monitoring_tab import MonitoringTab
from .os_upgrade_tab import OSUpgradeTab
from .restore_tab import RestoreTab
from .rise_vision_tab import RiseVisionTab
from .scheduler_tab import SchedulerTab
from .watchdog_tab import WatchdogTab
from .fleet_dashboard_tab import FleetDashboardTab
from .network_tab import NetworkTab

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
    'FleetDashboardTab',
    'NetworkTab',
]
