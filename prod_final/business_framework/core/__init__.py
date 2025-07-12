"""
核心业务组件模块

提供通用的业务逻辑组件，可适配多种商业场景：
- 数据处理器 (DataProcessor)
- 警报引擎 (AlertEngine) 
- 通知服务 (NotificationService)
- 用户管理 (UserManager)
- 配置管理 (ConfigManager)
"""

from .data_processor import DataProcessor
from .alert_engine import AlertEngine  
from .notification_service import NotificationService
from .user_manager import UserManager
from .config_manager import ConfigManager

__all__ = [
    'DataProcessor',
    'AlertEngine',
    'NotificationService', 
    'UserManager',
    'ConfigManager'
] 