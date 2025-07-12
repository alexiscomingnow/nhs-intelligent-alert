"""
Business Framework - 通用商业化解决方案框架

这个框架提供了可复用的组件，支持多种数据驱动的商业应用场景：
- 数据ETL和处理
- 智能提醒和通知
- 用户管理和订阅
- 多渠道消息发送
- 白标和多租户支持
- API服务和管理后台

架构设计原则：
1. 模块化 - 每个组件独立，可单独使用
2. 可配置 - 通过配置文件适配不同业务场景
3. 可扩展 - 插件式架构支持自定义扩展
4. 可复用 - 核心逻辑与具体业务解耦
"""

__version__ = "1.0.0"
__author__ = "NHS Alert Team"

# 核心组件导入
from .core import (
    DataProcessor,
    AlertEngine,
    NotificationService,
    UserManager,
    ConfigManager
)

from .integrations import (
    WhatsAppClient,
    SMSClient,
    EmailClient
)

from .api import (
    APIGateway,
    WebhookHandler,
    AdminPanel
)

__all__ = [
    'DataProcessor',
    'AlertEngine', 
    'NotificationService',
    'UserManager',
    'ConfigManager',
    'WhatsAppClient',
    'SMSClient',
    'EmailClient',
    'APIGateway',
    'WebhookHandler',
    'AdminPanel'
] 