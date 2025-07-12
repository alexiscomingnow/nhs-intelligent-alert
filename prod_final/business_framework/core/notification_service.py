#!/usr/bin/env python3
"""
Notification Service - NHS Alert System
通用通知服务：支持多渠道消息发送、模板管理、用户偏好等
"""

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 消息状态和类型定义
class MessageChannel(Enum):
    """消息渠道"""
    WHATSAPP = "whatsapp"
    SMS = "sms"
    EMAIL = "email"
    PUSH = "push"
    WEBHOOK = "webhook"

class MessagePriority(Enum):
    """消息优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

class MessageStatus(Enum):
    """消息状态"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    CANCELLED = "cancelled"

# 数据类定义
@dataclass
class MessageTemplate:
    """消息模板"""
    id: str
    name: str
    channel: MessageChannel
    body: str = ""
    language: str = "en"
    
    # 模板内容
    subject: Optional[str] = None  # 邮件主题或推送标题
    
    # WhatsApp特定
    whatsapp_template_name: Optional[str] = None
    whatsapp_components: List[Dict[str, Any]] = field(default_factory=list)
    
    # 变量占位符
    variables: List[str] = field(default_factory=list)
    
    # 元数据
    category: str = "general"
    tenant_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class MessageRequest:
    """消息发送请求"""
    recipient: str  # 手机号/邮箱/用户ID
    channel: MessageChannel
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: MessagePriority = MessagePriority.NORMAL
    
    # 内容
    template_id: Optional[str] = None
    subject: Optional[str] = None
    body: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)
    
    # 附加数据
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    actions: List[Dict[str, Any]] = field(default_factory=list)  # 按钮等交互元素
    
    # 调度
    send_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    # 追踪
    tracking_id: Optional[str] = None
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # A/B测试
    ab_test_group: Optional[str] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class MessageResult:
    """消息发送结果"""
    request_id: str
    success: bool
    status: MessageStatus
    channel: MessageChannel
    
    # 外部ID
    external_id: Optional[str] = None  # 第三方服务返回的消息ID
    
    # 错误信息
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    
    # 统计
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

class MessageProvider(ABC):
    """消息提供商抽象基类"""
    
    @abstractmethod
    async def send_message(self, request: MessageRequest) -> MessageResult:
        """发送消息"""
        pass
    
    @abstractmethod
    def get_supported_channels(self) -> List[MessageChannel]:
        """获取支持的渠道"""
        pass
    
    @abstractmethod
    async def get_message_status(self, external_id: str) -> MessageStatus:
        """获取消息状态"""
        pass

class UserPreferences:
    """用户通知偏好"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.channels: Dict[MessageChannel, bool] = {
            MessageChannel.WHATSAPP: True,
            MessageChannel.SMS: True,
            MessageChannel.EMAIL: True,
            MessageChannel.PUSH: True
        }
        self.quiet_hours: Dict[str, str] = {
            "start": "22:00",
            "end": "08:00"
        }
        self.frequency_limits: Dict[str, int] = {
            "daily_max": 10,
            "hourly_max": 3
        }
        self.languages: List[str] = ["en"]
        self.timezone: str = "UTC"

class NotificationService:
    """
    通用通知服务
    
    功能：
    - 多渠道消息发送
    - 消息模板管理
    - 发送队列和调度
    - 用户偏好管理
    - 发送统计和分析
    """
    
    def __init__(self, config_manager, database_manager):
        self.config = config_manager
        self.db = database_manager
        
        # 消息提供商
        self.providers: Dict[MessageChannel, MessageProvider] = {}
        
        # 消息队列
        self.message_queue: List[MessageRequest] = []
        self.processing_queue = asyncio.Queue()
        
        # 模板缓存
        self.templates_cache: Dict[str, MessageTemplate] = {}
        
        # 用户偏好缓存
        self.user_preferences: Dict[str, UserPreferences] = {}
        
        # 发送统计
        self.stats = {
            'messages_sent': defaultdict(int),
            'messages_failed': defaultdict(int),
            'delivery_rates': defaultdict(list),
            'response_times': defaultdict(list)
        }
        
        # 启动后台处理器
        self._start_background_processor()
    
    def register_provider(self, provider: MessageProvider):
        """注册消息提供商"""
        for channel in provider.get_supported_channels():
            self.providers[channel] = provider
            logger.info(f"Registered provider for channel: {channel}")
    
    async def send_message(self, request: MessageRequest) -> MessageResult:
        """发送单条消息"""
        # 验证请求
        if not self._validate_request(request):
            return MessageResult(
                request_id=request.id,
                success=False,
                status=MessageStatus.FAILED,
                channel=request.channel,
                error_message="Invalid request parameters"
            )
        
        # 检查用户偏好
        if request.user_id:
            preferences = await self._get_user_preferences(request.user_id)
            if not self._check_user_preferences(request, preferences):
                return MessageResult(
                    request_id=request.id,
                    success=False,
                    status=MessageStatus.CANCELLED,
                    channel=request.channel,
                    error_message="Cancelled due to user preferences"
                )
        
        # 处理模板
        if request.template_id:
            request = await self._apply_template(request)
        
        # 立即发送或加入队列
        if request.send_at and request.send_at > datetime.now():
            await self._schedule_message(request)
            return MessageResult(
                request_id=request.id,
                success=True,
                status=MessageStatus.PENDING,
                channel=request.channel
            )
        else:
            return await self._send_message_now(request)
    
    async def send_bulk_messages(self, requests: List[MessageRequest]) -> List[MessageResult]:
        """批量发送消息"""
        results = []
        
        # 分批处理
        batch_size = self.config.get_config_value('notifications.batch_size', default=50)
        
        for i in range(0, len(requests), batch_size):
            batch = requests[i:i + batch_size]
            
            # 并发发送
            tasks = [self.send_message(request) for request in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    # 处理异常
                    results.append(MessageResult(
                        request_id="unknown",
                        success=False,
                        status=MessageStatus.FAILED,
                        channel=MessageChannel.WHATSAPP,  # 默认值
                        error_message=str(result)
                    ))
                else:
                    results.append(result)
        
        return results
    
    async def create_template(self, template: MessageTemplate) -> MessageTemplate:
        """创建消息模板"""
        # 保存到数据库
        await self._save_template_to_db(template)
        
        # 更新缓存
        self.templates_cache[template.id] = template
        
        logger.info(f"Created template: {template.id}")
        return template
    
    async def get_template(self, template_id: str) -> Optional[MessageTemplate]:
        """获取消息模板"""
        # 先检查缓存
        if template_id in self.templates_cache:
            return self.templates_cache[template_id]
        
        # 从数据库加载
        template = await self._load_template_from_db(template_id)
        if template:
            self.templates_cache[template_id] = template
        
        return template
    
    async def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> UserPreferences:
        """更新用户偏好"""
        # 获取现有偏好或创建新的
        if user_id in self.user_preferences:
            user_prefs = self.user_preferences[user_id]
        else:
            user_prefs = UserPreferences(user_id)
        
        # 更新偏好
        for key, value in preferences.items():
            if hasattr(user_prefs, key):
                setattr(user_prefs, key, value)
        
        # 保存到数据库
        await self._save_user_preferences(user_prefs)
        
        # 更新缓存
        self.user_preferences[user_id] = user_prefs
        
        logger.info(f"Updated preferences for user: {user_id}")
        return user_prefs
    
    # 私有方法
    async def _send_message_now(self, request: MessageRequest) -> MessageResult:
        """立即发送消息"""
        start_time = datetime.now()
        
        try:
            # 获取提供商
            provider = self.providers.get(request.channel)
            if not provider:
                return MessageResult(
                    request_id=request.id,
                    success=False,
                    status=MessageStatus.FAILED,
                    channel=request.channel,
                    error_message=f"No provider available for channel: {request.channel}"
                )
            
            # 发送消息
            result = await provider.send_message(request)
            
            # 更新统计
            self._update_stats(request.channel, result, start_time)
            
            # 保存记录
            await self._save_message_record(request, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send message {request.id}: {e}")
            
            result = MessageResult(
                request_id=request.id,
                success=False,
                status=MessageStatus.FAILED,
                channel=request.channel,
                error_message=str(e)
            )
            
            # 更新统计
            self._update_stats(request.channel, result, start_time)
            
            return result
    
    async def _apply_template(self, request: MessageRequest) -> MessageRequest:
        """应用消息模板"""
        template = await self.get_template(request.template_id)
        if not template:
            logger.warning(f"Template not found: {request.template_id}")
            return request
        
        # 替换变量
        body = template.body
        subject = template.subject
        
        for var_name, var_value in request.variables.items():
            placeholder = f"{{{{{var_name}}}}}"
            if body:
                body = body.replace(placeholder, str(var_value))
            if subject:
                subject = subject.replace(placeholder, str(var_value))
        
        # 更新请求
        request.body = body or request.body
        request.subject = subject or request.subject
        
        # WhatsApp特定处理
        if template.channel == MessageChannel.WHATSAPP and template.whatsapp_components:
            request.metadata['whatsapp_components'] = template.whatsapp_components
        
        return request
    
    def _validate_request(self, request: MessageRequest) -> bool:
        """验证消息请求"""
        # 基本验证
        if not request.recipient:
            return False
        
        if not request.body and not request.template_id:
            return False
        
        # 渠道特定验证
        if request.channel == MessageChannel.EMAIL and '@' not in request.recipient:
            return False
        
        return True
    
    async def _get_user_preferences(self, user_id: str) -> UserPreferences:
        """获取用户偏好"""
        # 先检查缓存
        if user_id in self.user_preferences:
            return self.user_preferences[user_id]
        
        # 从数据库加载
        prefs = await self._load_user_preferences_from_db(user_id)
        if not prefs:
            prefs = UserPreferences(user_id)
        
        # 更新缓存
        self.user_preferences[user_id] = prefs
        
        return prefs
    
    def _check_user_preferences(self, request: MessageRequest, preferences: UserPreferences) -> bool:
        """检查用户偏好"""
        # 检查渠道是否启用
        if not preferences.channels.get(request.channel, True):
            return False
        
        # 检查安静时间
        if self._is_quiet_hours(preferences):
            return False
        
        # 检查频率限制
        if self._exceeds_frequency_limits(request.user_id, preferences):
            return False
        
        return True
    
    def _is_quiet_hours(self, preferences: UserPreferences) -> bool:
        """检查是否在安静时间"""
        # 简化实现 - 实际应该考虑时区
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        start_time = preferences.quiet_hours.get("start", "22:00")
        end_time = preferences.quiet_hours.get("end", "08:00")
        
        # 简单比较 - 实际应该处理跨天情况
        if start_time <= current_time or current_time <= end_time:
            return True
        
        return False
    
    def _exceeds_frequency_limits(self, user_id: str, preferences: UserPreferences) -> bool:
        """检查是否超过频率限制"""
        # 简化实现 - 实际应该查询数据库获取发送历史
        # 这里返回False表示未超过限制
        return False
    
    async def _schedule_message(self, request: MessageRequest):
        """调度消息"""
        # 简化实现 - 实际应该使用任务队列
        self.message_queue.append(request)
    
    def _start_background_processor(self):
        """启动后台处理器"""
        asyncio.create_task(self._background_processor())
    
    async def _background_processor(self):
        """后台消息处理器"""
        while True:
            try:
                # 处理调度消息
                now = datetime.now()
                messages_to_send = []
                
                for i, request in enumerate(self.message_queue):
                    if request.send_at and request.send_at <= now:
                        messages_to_send.append(request)
                
                # 移除已处理的消息
                for request in messages_to_send:
                    self.message_queue.remove(request)
                    await self.send_message(request)
                
                # 等待一分钟再次检查
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Background processor error: {e}")
                await asyncio.sleep(60)
    
    def _update_stats(self, channel: MessageChannel, result: MessageResult, start_time: datetime):
        """更新发送统计"""
        response_time = (datetime.now() - start_time).total_seconds() * 1000  # ms
        
        if result.success:
            self.stats['messages_sent'][channel] += 1
        else:
            self.stats['messages_failed'][channel] += 1
        
        self.stats['response_times'][channel].append(response_time)
        
        # 保留最近100条记录
        if len(self.stats['response_times'][channel]) > 100:
            self.stats['response_times'][channel] = self.stats['response_times'][channel][-100:]
    
    # 数据库操作方法（简化实现）
    async def _save_template_to_db(self, template: MessageTemplate):
        """保存模板到数据库"""
        # 实际实现应该连接数据库
        pass
    
    async def _load_template_from_db(self, template_id: str) -> Optional[MessageTemplate]:
        """从数据库加载模板"""
        # 实际实现应该查询数据库
        return None
    
    async def _save_user_preferences(self, preferences: UserPreferences):
        """保存用户偏好到数据库"""
        # 实际实现应该连接数据库
        pass
    
    async def _load_user_preferences_from_db(self, user_id: str) -> Optional[UserPreferences]:
        """从数据库加载用户偏好"""
        # 实际实现应该查询数据库
        return None
    
    async def _save_message_record(self, request: MessageRequest, result: MessageResult):
        """保存消息记录"""
        # 实际实现应该保存到数据库
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """获取发送统计"""
        stats = {}
        
        for channel in MessageChannel:
            sent = self.stats['messages_sent'].get(channel, 0)
            failed = self.stats['messages_failed'].get(channel, 0)
            total = sent + failed
            
            response_times = self.stats['response_times'].get(channel, [])
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            stats[channel.value] = {
                'sent': sent,
                'failed': failed,
                'total': total,
                'success_rate': (sent / total * 100) if total > 0 else 0,
                'avg_response_time_ms': round(avg_response_time, 2)
            }
        
        return stats 