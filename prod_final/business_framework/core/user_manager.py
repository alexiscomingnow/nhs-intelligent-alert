"""
用户管理器 - 支持多租户用户和订阅管理

特性：
1. 多租户用户管理
2. 订阅和计费管理
3. 用户档案和偏好
4. 权限和角色管理
5. 使用统计和分析
6. 数据隐私和合规
"""

import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import uuid
import json

logger = logging.getLogger(__name__)

class UserRole(Enum):
    """用户角色"""
    GUEST = "guest"
    USER = "user"
    PREMIUM = "premium"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class SubscriptionTier(Enum):
    """订阅层级"""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class SubscriptionStatus(Enum):
    """订阅状态"""
    ACTIVE = "active"
    TRIAL = "trial"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"

@dataclass
class UserProfile:
    """用户档案"""
    user_id: str
    tenant_id: Optional[str] = None
    
    # 基本信息
    phone_number: Optional[str] = None
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
    # NHS特定信息
    nhs_number: Optional[str] = None  # 加密存储
    postcode: Optional[str] = None
    preferred_hospitals: List[str] = field(default_factory=list)
    medical_specialties: List[str] = field(default_factory=list)
    
    # 偏好设置
    language: str = "en"
    timezone: str = "UTC"
    communication_style: str = "formal"  # formal, casual, urgent
    
    # 个人化数据
    age_group: Optional[str] = None  # 避免存储确切年龄
    mobility: str = "normal"  # normal, limited, wheelchair
    has_private_insurance: bool = False
    
    # 系统信息
    role: UserRole = UserRole.USER
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    is_active: bool = True
    
    # 验证状态
    phone_verified: bool = False
    email_verified: bool = False
    
    # 隐私设置
    data_sharing_consent: bool = False
    marketing_consent: bool = False

@dataclass
class Subscription:
    """用户订阅"""
    id: str
    user_id: str
    tenant_id: Optional[str] = None
    
    # 订阅信息
    tier: SubscriptionTier = SubscriptionTier.FREE
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    
    # 时间信息
    start_date: datetime = field(default_factory=datetime.now)
    end_date: Optional[datetime] = None
    trial_end_date: Optional[datetime] = None
    
    # 计费信息
    billing_cycle: str = "monthly"  # monthly, yearly
    amount: float = 0.0
    currency: str = "GBP"
    
    # 使用限制
    features: Dict[str, Any] = field(default_factory=dict)
    usage_limits: Dict[str, int] = field(default_factory=dict)
    current_usage: Dict[str, int] = field(default_factory=dict)
    
    # 支付信息
    payment_method_id: Optional[str] = None
    next_billing_date: Optional[datetime] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class UsageEvent:
    """使用事件记录"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    tenant_id: Optional[str] = None
    
    # 事件信息
    event_type: str = ""  # alert_sent, data_query, api_call等
    resource: str = ""
    quantity: int = 1
    
    # 时间戳
    timestamp: datetime = field(default_factory=datetime.now)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

class UserManager:
    """
    用户管理器
    
    功能：
    - 用户注册和认证
    - 档案管理
    - 订阅和计费
    - 使用统计
    - 多租户支持
    """
    
    def __init__(self, database_manager, config_manager):
        self.db = database_manager
        self.config = config_manager
        
        # 用户缓存
        self.users_cache: Dict[str, UserProfile] = {}
        self.subscriptions_cache: Dict[str, Subscription] = {}
        
        # 统计信息
        self.stats = {
            'total_users': 0,
            'active_users': 0,
            'trial_users': 0,
            'premium_users': 0
        }
    
    async def create_user(self, user_data: Dict[str, Any], tenant_id: Optional[str] = None) -> UserProfile:
        """创建新用户"""
        
        # 验证必填字段
        if not user_data.get('phone_number') and not user_data.get('email'):
            raise ValueError("Phone number or email is required")
        
        # 生成用户ID
        user_id = str(uuid.uuid4())
        
        # 创建用户档案
        user_profile = UserProfile(
            user_id=user_id,
            tenant_id=tenant_id,
            **user_data
        )
        
        # 加密敏感信息
        if user_profile.nhs_number:
            user_profile.nhs_number = self._encrypt_sensitive_data(user_profile.nhs_number)
        
        # 保存到数据库
        await self._save_user_to_db(user_profile)
        
        # 创建默认订阅
        subscription = await self.create_subscription(
            user_id=user_id,
            tier=SubscriptionTier.FREE,
            tenant_id=tenant_id
        )
        
        # 更新缓存
        self.users_cache[user_id] = user_profile
        self.subscriptions_cache[user_id] = subscription
        
        # 更新统计
        self.stats['total_users'] += 1
        self.stats['active_users'] += 1
        
        logger.info(f"Created new user: {user_id}")
        return user_profile
    
    async def get_user(self, user_id: str) -> Optional[UserProfile]:
        """获取用户档案"""
        # 检查缓存
        if user_id in self.users_cache:
            return self.users_cache[user_id]
        
        # 从数据库加载
        user = await self._load_user_from_db(user_id)
        if user:
            # 解密敏感信息
            if user.nhs_number:
                user.nhs_number = self._decrypt_sensitive_data(user.nhs_number)
            
            self.users_cache[user_id] = user
        
        return user
    
    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> UserProfile:
        """更新用户档案"""
        user = await self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # 更新字段
        for key, value in updates.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        user.updated_at = datetime.now()
        
        # 加密敏感信息
        if 'nhs_number' in updates and user.nhs_number:
            user.nhs_number = self._encrypt_sensitive_data(user.nhs_number)
        
        # 保存到数据库
        await self._save_user_to_db(user)
        
        # 更新缓存
        self.users_cache[user_id] = user
        
        logger.info(f"Updated user: {user_id}")
        return user
    
    async def create_subscription(self, user_id: str, tier: SubscriptionTier, tenant_id: Optional[str] = None) -> Subscription:
        """创建用户订阅"""
        
        # 获取订阅配置
        tier_config = self._get_tier_config(tier, tenant_id)
        
        subscription = Subscription(
            id=str(uuid.uuid4()),
            user_id=user_id,
            tenant_id=tenant_id,
            tier=tier,
            features=tier_config.get('features', {}),
            usage_limits=tier_config.get('limits', {}),
            amount=tier_config.get('price', 0.0),
            billing_cycle=tier_config.get('billing_cycle', 'monthly')
        )
        
        # 设置试用期
        if tier != SubscriptionTier.FREE and tier_config.get('trial_days', 0) > 0:
            subscription.status = SubscriptionStatus.TRIAL
            subscription.trial_end_date = datetime.now() + timedelta(days=tier_config['trial_days'])
        
        # 保存到数据库
        await self._save_subscription_to_db(subscription)
        
        # 更新缓存
        self.subscriptions_cache[user_id] = subscription
        
        logger.info(f"Created subscription: {subscription.id} for user {user_id}")
        return subscription
    
    async def get_user_subscription(self, user_id: str) -> Optional[Subscription]:
        """获取用户订阅"""
        # 检查缓存
        if user_id in self.subscriptions_cache:
            return self.subscriptions_cache[user_id]
        
        # 从数据库加载
        subscription = await self._load_subscription_from_db(user_id)
        if subscription:
            self.subscriptions_cache[user_id] = subscription
        
        return subscription
    
    async def upgrade_subscription(self, user_id: str, new_tier: SubscriptionTier) -> Subscription:
        """升级用户订阅"""
        subscription = await self.get_user_subscription(user_id)
        if not subscription:
            raise ValueError(f"No subscription found for user {user_id}")
        
        # 获取新层级配置
        tier_config = self._get_tier_config(new_tier, subscription.tenant_id)
        
        # 更新订阅
        subscription.tier = new_tier
        subscription.features = tier_config.get('features', {})
        subscription.usage_limits = tier_config.get('limits', {})
        subscription.amount = tier_config.get('price', 0.0)
        subscription.billing_cycle = tier_config.get('billing_cycle', 'monthly')
        subscription.updated_at = datetime.now()
        
        # 重置使用量（可选）
        subscription.current_usage = {}
        
        # 保存到数据库
        await self._save_subscription_to_db(subscription)
        
        # 更新缓存
        self.subscriptions_cache[user_id] = subscription
        
        logger.info(f"Upgraded subscription for user {user_id} to {new_tier}")
        return subscription
    
    async def record_usage(self, user_id: str, event_type: str, resource: str = "", quantity: int = 1, metadata: Optional[Dict] = None) -> bool:
        """记录用户使用事件"""
        
        subscription = await self.get_user_subscription(user_id)
        if not subscription:
            return False
        
        # 检查使用限制
        limit_key = f"{event_type}_{resource}" if resource else event_type
        usage_limit = subscription.usage_limits.get(limit_key, float('inf'))
        current_usage = subscription.current_usage.get(limit_key, 0)
        
        if current_usage + quantity > usage_limit:
            logger.warning(f"Usage limit exceeded for user {user_id}: {limit_key}")
            return False
        
        # 记录使用事件
        usage_event = UsageEvent(
            user_id=user_id,
            tenant_id=subscription.tenant_id,
            event_type=event_type,
            resource=resource,
            quantity=quantity,
            metadata=metadata or {}
        )
        
        await self._save_usage_event_to_db(usage_event)
        
        # 更新当前使用量
        subscription.current_usage[limit_key] = current_usage + quantity
        await self._save_subscription_to_db(subscription)
        
        return True
    
    async def check_feature_access(self, user_id: str, feature: str) -> bool:
        """检查用户是否可以访问特定功能"""
        subscription = await self.get_user_subscription(user_id)
        if not subscription:
            return False
        
        return subscription.features.get(feature, False)
    
    async def get_user_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """获取用户使用分析"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 从数据库查询使用事件
        usage_events = await self._load_usage_events_from_db(user_id, start_date, end_date)
        
        # 统计分析
        analytics = {
            'total_events': len(usage_events),
            'event_types': {},
            'daily_usage': {},
            'most_used_features': []
        }
        
        for event in usage_events:
            # 按类型统计
            if event.event_type not in analytics['event_types']:
                analytics['event_types'][event.event_type] = 0
            analytics['event_types'][event.event_type] += event.quantity
            
            # 按日期统计
            date_key = event.timestamp.strftime('%Y-%m-%d')
            if date_key not in analytics['daily_usage']:
                analytics['daily_usage'][date_key] = 0
            analytics['daily_usage'][date_key] += event.quantity
        
        # 最常用功能
        analytics['most_used_features'] = sorted(
            analytics['event_types'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return analytics
    
    async def find_users_by_criteria(self, criteria: Dict[str, Any], tenant_id: Optional[str] = None) -> List[UserProfile]:
        """根据条件查找用户"""
        # 这里应该实现数据库查询逻辑
        # 支持按地区、专科、订阅层级等条件筛选
        return await self._search_users_in_db(criteria, tenant_id)
    
    def _get_tier_config(self, tier: SubscriptionTier, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """获取订阅层级配置"""
        # 从配置管理器获取定价和功能配置
        base_config = {
            SubscriptionTier.FREE: {
                'price': 0.0,
                'trial_days': 0,
                'features': {
                    'basic_alerts': True,
                    'hospital_comparison': False,
                    'priority_support': False,
                    'custom_thresholds': False
                },
                'limits': {
                    'alerts_per_day': 3,
                    'api_calls_per_month': 100
                }
            },
            SubscriptionTier.BASIC: {
                'price': 1.99,
                'trial_days': 7,
                'features': {
                    'basic_alerts': True,
                    'hospital_comparison': True,
                    'priority_support': False,
                    'custom_thresholds': True
                },
                'limits': {
                    'alerts_per_day': 10,
                    'api_calls_per_month': 1000
                }
            },
            SubscriptionTier.PREMIUM: {
                'price': 9.99,
                'trial_days': 14,
                'features': {
                    'basic_alerts': True,
                    'hospital_comparison': True,
                    'priority_support': True,
                    'custom_thresholds': True,
                    'private_hospital_recommendations': True
                },
                'limits': {
                    'alerts_per_day': 50,
                    'api_calls_per_month': 10000
                }
            }
        }
        
        config = base_config.get(tier, base_config[SubscriptionTier.FREE])
        
        # 租户特定配置覆盖
        if tenant_id:
            tenant_config = self.config.get_config_value(f'pricing.{tenant_id}.{tier.value}', tenant_id=tenant_id)
            if tenant_config:
                config.update(tenant_config)
        
        return config
    
    def _encrypt_sensitive_data(self, data: str) -> str:
        """加密敏感数据"""
        return self.config.encrypt_sensitive_value(data)
    
    def _decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """解密敏感数据"""
        return self.config.decrypt_sensitive_value(encrypted_data)
    
    async def _save_user_to_db(self, user: UserProfile):
        """保存用户到数据库"""
        # 实现数据库保存逻辑
        pass
    
    async def _load_user_from_db(self, user_id: str) -> Optional[UserProfile]:
        """从数据库加载用户"""
        # 实现数据库查询逻辑
        return None
    
    async def _save_subscription_to_db(self, subscription: Subscription):
        """保存订阅到数据库"""
        # 实现数据库保存逻辑
        pass
    
    async def _load_subscription_from_db(self, user_id: str) -> Optional[Subscription]:
        """从数据库加载订阅"""
        # 实现数据库查询逻辑
        return None
    
    async def _save_usage_event_to_db(self, event: UsageEvent):
        """保存使用事件到数据库"""
        # 实现数据库保存逻辑
        pass
    
    async def _load_usage_events_from_db(self, user_id: str, start_date: datetime, end_date: datetime) -> List[UsageEvent]:
        """从数据库加载使用事件"""
        # 实现数据库查询逻辑
        return []
    
    async def _search_users_in_db(self, criteria: Dict[str, Any], tenant_id: Optional[str] = None) -> List[UserProfile]:
        """在数据库中搜索用户"""
        # 实现数据库搜索逻辑
        return []
    
    def get_stats(self) -> Dict[str, Any]:
        """获取用户统计信息"""
        return {
            **self.stats,
            'cached_users': len(self.users_cache),
            'cached_subscriptions': len(self.subscriptions_cache)
        } 