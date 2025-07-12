"""
配置管理器 - 支持多环境、多租户和动态配置

特性：
1. 环境隔离 (dev/staging/prod)
2. 多租户配置
3. 热加载配置
4. 配置验证和默认值
5. 敏感信息加密存储
"""

import os
import json
import yaml
from typing import Dict, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass, field
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)

@dataclass
class TenantConfig:
    """租户配置数据类"""
    tenant_id: str
    name: str
    domain: str = ""
    branding: Dict[str, Any] = field(default_factory=dict)
    features: Dict[str, bool] = field(default_factory=dict)
    limits: Dict[str, int] = field(default_factory=dict)
    integrations: Dict[str, Dict] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

@dataclass 
class BusinessConfig:
    """业务配置数据类"""
    name: str
    version: str = "1.0.0"
    environment: str = "dev"
    debug: bool = False
    
    # 数据库配置
    database: Dict[str, Any] = field(default_factory=dict)
    
    # 外部API配置
    apis: Dict[str, Dict] = field(default_factory=dict)
    
    # 通知渠道配置
    notifications: Dict[str, Dict] = field(default_factory=dict)
    
    # 业务规则配置
    business_rules: Dict[str, Any] = field(default_factory=dict)
    
    # 监控和日志
    monitoring: Dict[str, Any] = field(default_factory=dict)

class ConfigManager:
    """
    通用配置管理器
    
    支持：
    - 多格式配置文件 (JSON, YAML, ENV)
    - 环境变量覆盖
    - 多租户配置
    - 配置验证
    - 敏感信息加密
    - 热重载
    """
    
    def __init__(self, config_path: Optional[str] = None, environment: str = "dev"):
        self.environment = environment
        self.config_path = Path(config_path) if config_path else Path("./config")
        self.config_path.mkdir(exist_ok=True)
        
        # 初始化加密器
        self._init_encryption()
        
        # 加载配置
        self._business_config: Optional[BusinessConfig] = None
        self._tenant_configs: Dict[str, TenantConfig] = {}
        self._config_cache: Dict[str, Any] = {}
        
        self.load_configs()
    
    def _init_encryption(self):
        """初始化配置加密"""
        key_file = self.config_path / ".config_key"
        
        if key_file.exists():
            with open(key_file, 'rb') as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            # 设置文件权限为只读
            os.chmod(key_file, 0o600)
        
        self._cipher = Fernet(key)
    
    def load_configs(self):
        """加载所有配置文件"""
        try:
            # 加载主配置
            self._load_business_config()
            
            # 加载租户配置
            self._load_tenant_configs()
            
            logger.info(f"Loaded configuration for environment: {self.environment}")
            
        except Exception as e:
            logger.error(f"Failed to load configs: {e}")
            raise
    
    def _load_business_config(self):
        """加载业务配置"""
        config_file = self.config_path / f"business.{self.environment}.yaml"
        
        if not config_file.exists():
            # 创建默认配置
            self._create_default_business_config(config_file)
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        # 环境变量覆盖
        config_data = self._apply_env_overrides(config_data)
        
        self._business_config = BusinessConfig(**config_data)
    
    def _load_tenant_configs(self):
        """加载租户配置"""
        tenants_dir = self.config_path / "tenants"
        tenants_dir.mkdir(exist_ok=True)
        
        self._tenant_configs.clear()
        
        for tenant_file in tenants_dir.glob("*.yaml"):
            try:
                with open(tenant_file, 'r', encoding='utf-8') as f:
                    tenant_data = yaml.safe_load(f)
                
                tenant = TenantConfig(**tenant_data)
                self._tenant_configs[tenant.tenant_id] = tenant
                
            except Exception as e:
                logger.error(f"Failed to load tenant config {tenant_file}: {e}")
    
    def _create_default_business_config(self, config_file: Path):
        """创建默认业务配置"""
        default_config = {
            "name": "Business Framework",
            "version": "1.0.0", 
            "environment": self.environment,
            "debug": self.environment == "dev",
            
            "database": {
                "type": "postgresql",
                "host": "${DB_HOST:localhost}",
                "port": "${DB_PORT:5432}",
                "name": "${DB_NAME:business_db}",
                "user": "${DB_USER:postgres}",
                "password": "${DB_PASSWORD:}",
                "pool_size": 10,
                "max_overflow": 20
            },
            
            "apis": {
                "rate_limit": {
                    "requests_per_minute": 100,
                    "burst_limit": 20
                }
            },
            
            "notifications": {
                "whatsapp": {
                    "enabled": True,
                    "api_url": "https://graph.facebook.com/v18.0",
                    "phone_number_id": "${WHATSAPP_PHONE_ID:}",
                    "access_token": "${WHATSAPP_ACCESS_TOKEN:}",
                    "webhook_verify_token": "${WHATSAPP_WEBHOOK_TOKEN:}"
                },
                "sms": {
                    "enabled": False,
                    "provider": "twilio",
                    "api_key": "${SMS_API_KEY:}",
                    "api_secret": "${SMS_API_SECRET:}"
                },
                "email": {
                    "enabled": True,
                    "smtp_host": "${SMTP_HOST:localhost}",
                    "smtp_port": "${SMTP_PORT:587}",
                    "smtp_user": "${SMTP_USER:}",
                    "smtp_password": "${SMTP_PASSWORD:}",
                    "from_email": "${FROM_EMAIL:noreply@example.com}"
                }
            },
            
            "business_rules": {
                "max_alerts_per_user_per_day": 10,
                "alert_cooldown_minutes": 60,
                "default_subscription_tier": "free"
            },
            
            "monitoring": {
                "sentry_dsn": "${SENTRY_DSN:}",
                "log_level": "INFO" if self.environment == "prod" else "DEBUG",
                "metrics_enabled": True
            }
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
    
    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """应用环境变量覆盖"""
        def replace_env_vars(obj):
            if isinstance(obj, dict):
                return {k: replace_env_vars(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_env_vars(item) for item in obj]
            elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
                # 解析环境变量，支持默认值 ${VAR:default}
                var_spec = obj[2:-1]
                if ":" in var_spec:
                    var_name, default_value = var_spec.split(":", 1)
                else:
                    var_name, default_value = var_spec, ""
                
                value = os.getenv(var_name, default_value)
                
                # 尝试转换数据类型
                if value.isdigit():
                    return int(value)
                elif value.lower() in ('true', 'false'):
                    return value.lower() == 'true'
                else:
                    return value
            else:
                return obj
        
        return replace_env_vars(config)
    
    def get_business_config(self) -> BusinessConfig:
        """获取业务配置"""
        if self._business_config is None:
            raise ValueError("Business config not loaded")
        return self._business_config
    
    def get_tenant_config(self, tenant_id: str) -> Optional[TenantConfig]:
        """获取租户配置"""
        return self._tenant_configs.get(tenant_id)
    
    def get_all_tenants(self) -> Dict[str, TenantConfig]:
        """获取所有租户配置"""
        return self._tenant_configs.copy()
    
    def create_tenant(self, tenant_data: Dict[str, Any]) -> TenantConfig:
        """创建新租户"""
        tenant = TenantConfig(**tenant_data)
        
        # 保存到文件
        tenant_file = self.config_path / "tenants" / f"{tenant.tenant_id}.yaml"
        with open(tenant_file, 'w', encoding='utf-8') as f:
            yaml.dump(tenant_data, f, default_flow_style=False, allow_unicode=True)
        
        # 缓存
        self._tenant_configs[tenant.tenant_id] = tenant
        
        return tenant
    
    def update_tenant(self, tenant_id: str, updates: Dict[str, Any]) -> TenantConfig:
        """更新租户配置"""
        if tenant_id not in self._tenant_configs:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        tenant = self._tenant_configs[tenant_id]
        
        # 更新字段
        for key, value in updates.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)
        
        # 保存到文件
        tenant_file = self.config_path / "tenants" / f"{tenant_id}.yaml"
        tenant_dict = {
            "tenant_id": tenant.tenant_id,
            "name": tenant.name,
            "domain": tenant.domain,
            "branding": tenant.branding,
            "features": tenant.features,
            "limits": tenant.limits,
            "integrations": tenant.integrations,
            "created_at": tenant.created_at,
            "updated_at": tenant.updated_at
        }
        
        with open(tenant_file, 'w', encoding='utf-8') as f:
            yaml.dump(tenant_dict, f, default_flow_style=False, allow_unicode=True)
        
        return tenant
    
    def get_config_value(self, key_path: str, tenant_id: Optional[str] = None, default: Any = None) -> Any:
        """
        获取配置值，支持点号路径访问
        
        Args:
            key_path: 配置路径，如 'database.host' 或 'notifications.whatsapp.enabled'
            tenant_id: 租户ID，如果提供则优先使用租户配置
            default: 默认值
        """
        cache_key = f"{tenant_id or 'global'}:{key_path}"
        
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]
        
        # 尝试从租户配置获取
        if tenant_id:
            tenant = self.get_tenant_config(tenant_id)
            if tenant:
                value = self._get_nested_value(tenant.__dict__, key_path)
                if value is not None:
                    self._config_cache[cache_key] = value
                    return value
        
        # 从业务配置获取
        business_config = self.get_business_config()
        value = self._get_nested_value(business_config.__dict__, key_path)
        
        if value is None:
            value = default
        
        self._config_cache[cache_key] = value
        return value
    
    def _get_nested_value(self, obj: Dict[str, Any], key_path: str) -> Any:
        """获取嵌套字典值"""
        keys = key_path.split('.')
        current = obj
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def encrypt_sensitive_value(self, value: str) -> str:
        """加密敏感配置值"""
        return self._cipher.encrypt(value.encode()).decode()
    
    def decrypt_sensitive_value(self, encrypted_value: str) -> str:
        """解密敏感配置值"""
        return self._cipher.decrypt(encrypted_value.encode()).decode()
    
    def reload_configs(self):
        """重新加载配置"""
        self._config_cache.clear()
        self.load_configs()
        logger.info("Configuration reloaded")
    
    def validate_config(self) -> Dict[str, Any]:
        """验证配置完整性"""
        issues = []
        
        try:
            business_config = self.get_business_config()
            
            # 验证数据库配置
            if not business_config.database.get('host'):
                issues.append("Database host not configured")
            
            # 验证通知配置
            notifications = business_config.notifications
            if notifications.get('whatsapp', {}).get('enabled'):
                if not notifications['whatsapp'].get('access_token'):
                    issues.append("WhatsApp access token not configured")
            
            # 验证租户配置
            for tenant_id, tenant in self._tenant_configs.items():
                if not tenant.name:
                    issues.append(f"Tenant {tenant_id} missing name")
            
        except Exception as e:
            issues.append(f"Configuration validation error: {e}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "tenant_count": len(self._tenant_configs)
        } 