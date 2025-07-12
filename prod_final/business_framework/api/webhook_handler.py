"""
Webhook处理器 - 处理外部服务回调

支持的Webhook：
1. WhatsApp Business API
2. SMS服务状态回调
3. 支付服务回调
4. GP Connect API事件
"""

import asyncio
import logging
import json
import hmac
import hashlib
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from fastapi import Request, HTTPException
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class WebhookEvent:
    """Webhook事件数据"""
    source: str  # whatsapp, sms, payment, etc.
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime
    signature: Optional[str] = None
    verified: bool = False

class WebhookHandler:
    """
    Webhook处理器
    
    功能：
    - 验证Webhook签名
    - 路由不同类型的事件
    - 异步事件处理
    - 错误重试机制
    """
    
    def __init__(self, config_manager, notification_service, patient_service):
        self.config = config_manager
        self.notification_service = notification_service
        self.patient_service = patient_service
        
        # 事件处理器注册表
        self.event_handlers: Dict[str, Dict[str, Callable]] = {
            'whatsapp': {},
            'sms': {},
            'payment': {},
            'gp_connect': {}
        }
        
        # 事件队列
        self.event_queue = asyncio.Queue()
        
        # 统计信息
        self.stats = {
            'events_received': 0,
            'events_processed': 0,
            'events_failed': 0,
            'signature_failures': 0
        }
        
        # 注册默认处理器
        self._register_default_handlers()
        
        # 启动事件处理器
        asyncio.create_task(self._process_events())
    
    def _register_default_handlers(self):
        """注册默认事件处理器"""
        
        # WhatsApp事件处理器
        self.register_handler('whatsapp', 'message', self._handle_whatsapp_message)
        self.register_handler('whatsapp', 'message_status', self._handle_whatsapp_status)
        self.register_handler('whatsapp', 'flow_response', self._handle_whatsapp_flow)
        
        # SMS事件处理器
        self.register_handler('sms', 'delivery_status', self._handle_sms_status)
        
        # 支付事件处理器
        self.register_handler('payment', 'payment_succeeded', self._handle_payment_success)
        self.register_handler('payment', 'payment_failed', self._handle_payment_failure)
    
    def register_handler(self, source: str, event_type: str, handler: Callable):
        """注册事件处理器"""
        if source not in self.event_handlers:
            self.event_handlers[source] = {}
        
        self.event_handlers[source][event_type] = handler
        logger.info(f"Registered handler for {source}.{event_type}")
    
    async def handle_webhook(self, source: str, request: Request) -> Dict[str, Any]:
        """处理Webhook请求"""
        try:
            # 获取请求数据
            body = await request.body()
            headers = dict(request.headers)
            
            # 验证签名
            signature = headers.get('x-hub-signature-256') or headers.get('x-signature')
            if not await self._verify_signature(source, body, signature):
                self.stats['signature_failures'] += 1
                raise HTTPException(status_code=401, detail="Invalid signature")
            
            # 解析数据
            try:
                data = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON")
            
            # 创建事件
            event = await self._create_webhook_event(source, data, signature)
            
            # 添加到处理队列
            await self.event_queue.put(event)
            
            self.stats['events_received'] += 1
            
            # 返回成功响应
            return {"status": "received", "event_id": f"{source}_{datetime.now().timestamp()}"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Webhook handling error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def _verify_signature(self, source: str, body: bytes, signature: Optional[str]) -> bool:
        """验证Webhook签名"""
        if not signature:
            # 某些测试环境可能不需要签名验证
            if self.config.get_business_config().debug:
                return True
            return False
        
        # 获取对应的密钥
        business_config = self.config.get_business_config()
        
        if source == 'whatsapp':
            secret = business_config.notifications.get('whatsapp', {}).get('webhook_verify_token')
        elif source == 'sms':
            secret = business_config.notifications.get('sms', {}).get('webhook_secret')
        elif source == 'payment':
            secret = business_config.apis.get('payment_webhook_secret')
        else:
            logger.warning(f"No secret configured for source: {source}")
            return False
        
        if not secret:
            return False
        
        # 计算期望的签名
        if signature.startswith('sha256='):
            expected_signature = 'sha256=' + hmac.new(
                secret.encode('utf-8'),
                body,
                hashlib.sha256
            ).hexdigest()
        else:
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                body,
                hashlib.sha256
            ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    async def _create_webhook_event(self, source: str, data: Dict[str, Any], signature: Optional[str]) -> WebhookEvent:
        """创建Webhook事件"""
        # 根据数据源确定事件类型
        event_type = 'unknown'
        
        if source == 'whatsapp':
            if 'messages' in data.get('entry', [{}])[0].get('changes', [{}])[0].get('value', {}):
                event_type = 'message'
            elif 'statuses' in data.get('entry', [{}])[0].get('changes', [{}])[0].get('value', {}):
                event_type = 'message_status'
        
        elif source == 'sms':
            if 'MessageStatus' in data:
                event_type = 'delivery_status'
        
        elif source == 'payment':
            event_type = data.get('type', 'unknown')
        
        return WebhookEvent(
            source=source,
            event_type=event_type,
            data=data,
            timestamp=datetime.now(),
            signature=signature,
            verified=True
        )
    
    async def _process_events(self):
        """处理事件队列"""
        while True:
            try:
                # 获取事件
                event = await self.event_queue.get()
                
                # 查找处理器
                if event.source in self.event_handlers:
                    if event.event_type in self.event_handlers[event.source]:
                        handler = self.event_handlers[event.source][event.event_type]
                        
                        try:
                            await handler(event)
                            self.stats['events_processed'] += 1
                        except Exception as e:
                            logger.error(f"Event processing failed: {e}")
                            self.stats['events_failed'] += 1
                    else:
                        logger.warning(f"No handler for {event.source}.{event.event_type}")
                else:
                    logger.warning(f"No handlers for source: {event.source}")
                
                # 标记任务完成
                self.event_queue.task_done()
                
            except Exception as e:
                logger.error(f"Event processing loop error: {e}")
                await asyncio.sleep(1)
    
    async def _handle_whatsapp_message(self, event: WebhookEvent):
        """处理WhatsApp消息事件"""
        data = event.data
        
        for entry in data.get('entry', []):
            for change in entry.get('changes', []):
                value = change.get('value', {})
                
                # 处理收到的消息
                for message in value.get('messages', []):
                    await self._process_incoming_whatsapp_message(message, value.get('contacts', []))
    
    async def _process_incoming_whatsapp_message(self, message: Dict[str, Any], contacts: List[Dict[str, Any]]):
        """处理收到的WhatsApp消息"""
        from_number = message.get('from')
        message_type = message.get('type')
        message_id = message.get('id')
        
        logger.info(f"Received WhatsApp message from {from_number}: {message_type}")
        
        # 获取发送者信息
        sender_name = None
        if contacts:
            sender_name = contacts[0].get('profile', {}).get('name')
        
        try:
            # 查找对应的患者
            patient = await self._find_patient_by_phone(from_number)
            
            if message_type == 'text':
                text_content = message.get('text', {}).get('body', '')
                await self._handle_patient_text_message(patient, text_content, from_number)
            
            elif message_type == 'interactive':
                interactive = message.get('interactive', {})
                
                if interactive.get('type') == 'button_reply':
                    button_id = interactive.get('button_reply', {}).get('id')
                    await self._handle_patient_button_click(patient, button_id, from_number)
                
                elif interactive.get('type') == 'list_reply':
                    list_id = interactive.get('list_reply', {}).get('id')
                    await self._handle_patient_list_selection(patient, list_id, from_number)
                
                elif interactive.get('type') == 'nfm_reply':
                    # WhatsApp Flow回复
                    response_json = interactive.get('nfm_reply', {}).get('response_json')
                    if response_json:
                        flow_data = json.loads(response_json)
                        await self._handle_patient_flow_response(patient, flow_data, from_number)
            
        except Exception as e:
            logger.error(f"Error processing WhatsApp message {message_id}: {e}")
    
    async def _handle_whatsapp_status(self, event: WebhookEvent):
        """处理WhatsApp消息状态事件"""
        data = event.data
        
        for entry in data.get('entry', []):
            for change in entry.get('changes', []):
                value = change.get('value', {})
                
                # 处理状态更新
                for status in value.get('statuses', []):
                    message_id = status.get('id')
                    recipient_id = status.get('recipient_id')
                    status_type = status.get('status')
                    
                    logger.debug(f"WhatsApp message {message_id} status: {status_type}")
                    
                    # 这里可以更新消息发送记录的状态
                    # await self.notification_service.update_message_status(message_id, status_type)
    
    async def _handle_whatsapp_flow(self, event: WebhookEvent):
        """处理WhatsApp Flow响应"""
        # Flow响应通常在interactive消息中处理
        pass
    
    async def _handle_sms_status(self, event: WebhookEvent):
        """处理SMS状态事件"""
        data = event.data
        
        message_id = data.get('MessageSid') or data.get('id')
        status = data.get('MessageStatus') or data.get('status')
        
        if message_id and status:
            logger.debug(f"SMS message {message_id} status: {status}")
            # 更新消息状态
            # await self.notification_service.update_message_status(message_id, status)
    
    async def _handle_payment_success(self, event: WebhookEvent):
        """处理支付成功事件"""
        data = event.data
        
        # 获取支付信息
        payment_intent = data.get('data', {}).get('object', {})
        customer_id = payment_intent.get('customer')
        amount = payment_intent.get('amount')
        
        logger.info(f"Payment succeeded: {customer_id}, amount: {amount}")
        
        # 升级用户订阅
        if customer_id:
            # 根据支付金额确定订阅层级
            from ..core.user_manager import SubscriptionTier
            
            if amount >= 999:  # £9.99
                tier = SubscriptionTier.PREMIUM
            else:
                tier = SubscriptionTier.BASIC
            
            try:
                # 查找用户并升级订阅
                # user = await self._find_user_by_customer_id(customer_id)
                # if user:
                #     await self.user_manager.upgrade_subscription(user.user_id, tier)
                pass
            except Exception as e:
                logger.error(f"Failed to upgrade subscription: {e}")
    
    async def _handle_payment_failure(self, event: WebhookEvent):
        """处理支付失败事件"""
        data = event.data
        
        payment_intent = data.get('data', {}).get('object', {})
        customer_id = payment_intent.get('customer')
        failure_reason = payment_intent.get('last_payment_error', {}).get('message')
        
        logger.warning(f"Payment failed: {customer_id}, reason: {failure_reason}")
        
        # 可以发送支付失败通知给用户
    
    async def _find_patient_by_phone(self, phone_number: str) -> Optional[Any]:
        """根据电话号码查找患者"""
        # 标准化电话号码
        clean_phone = ''.join(filter(str.isdigit, phone_number))
        
        # 这里应该实现数据库查询逻辑
        # 查找phone_number字段匹配的患者
        
        # 模拟返回
        return None
    
    async def _handle_patient_text_message(self, patient: Optional[Any], text: str, from_number: str):
        """处理患者文本消息"""
        if not patient:
            # 新用户，发送欢迎消息
            await self._send_welcome_message(from_number)
            return
        
        # 解析用户意图
        intent = self._parse_user_intent(text)
        
        if intent == 'get_status':
            # 用户询问状态
            await self._send_waiting_time_update(patient.user_id, from_number)
        elif intent == 'update_preferences':
            # 用户想更新偏好
            await self._send_preferences_flow(from_number)
        else:
            # 通用回复
            await self._send_help_message(from_number)
    
    async def _handle_patient_button_click(self, patient: Optional[Any], button_id: str, from_number: str):
        """处理患者按钮点击"""
        if button_id == 'check_status':
            if patient:
                await self._send_waiting_time_update(patient.user_id, from_number)
        elif button_id == 'update_preferences':
            await self._send_preferences_flow(from_number)
        elif button_id == 'unsubscribe':
            if patient:
                await self._handle_unsubscribe(patient.user_id, from_number)
    
    async def _handle_patient_list_selection(self, patient: Optional[Any], list_id: str, from_number: str):
        """处理患者列表选择"""
        # 根据列表选择ID处理不同的选项
        pass
    
    async def _handle_patient_flow_response(self, patient: Optional[Any], flow_data: Dict[str, Any], from_number: str):
        """处理患者Flow响应"""
        flow_token = flow_data.get('flow_token')
        screen_data = flow_data.get('screen_data', {})
        
        if flow_token == 'patient_setup':
            # 患者设置Flow
            await self._process_patient_setup(screen_data, from_number)
        elif flow_token == 'preferences_update':
            # 偏好更新Flow
            if patient:
                await self._process_preferences_update(patient.user_id, screen_data)
    
    async def _send_welcome_message(self, phone_number: str):
        """发送欢迎消息"""
        from ..core.notification_service import MessageRequest, MessageChannel
        
        request = MessageRequest(
            recipient=phone_number,
            channel=MessageChannel.WHATSAPP,
            body="欢迎使用NHS等候时间提醒服务！请点击下面的按钮开始设置。",
            actions=[
                {"id": "setup", "text": "开始设置"},
                {"id": "help", "text": "帮助"}
            ]
        )
        
        await self.notification_service.send_message(request)
    
    async def _send_waiting_time_update(self, patient_id: str, phone_number: str):
        """发送等候时间更新"""
        # 获取患者的最新提醒
        alerts = await self.patient_service.process_patient_alerts(patient_id)
        
        if alerts:
            latest_alert = alerts[0]
            message = f"📋 等候时间更新\n\n{latest_alert['message']}"
        else:
            message = "✅ 您的等候时间暂无重要更新。"
        
        from ..core.notification_service import MessageRequest, MessageChannel
        
        request = MessageRequest(
            recipient=phone_number,
            channel=MessageChannel.WHATSAPP,
            body=message
        )
        
        await self.notification_service.send_message(request)
    
    def _parse_user_intent(self, text: str) -> str:
        """解析用户意图"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['status', '状态', 'update', '更新', 'waiting', '等候']):
            return 'get_status'
        elif any(word in text_lower for word in ['preferences', '偏好', 'settings', '设置']):
            return 'update_preferences'
        elif any(word in text_lower for word in ['help', '帮助', 'support', '支持']):
            return 'help'
        else:
            return 'unknown'
    
    async def _send_preferences_flow(self, phone_number: str):
        """发送偏好设置Flow"""
        # 这里应该发送WhatsApp Flow来收集用户偏好
        pass
    
    async def _send_help_message(self, phone_number: str):
        """发送帮助消息"""
        help_text = """
🏥 NHS等候时间提醒服务

可用命令：
• 发送 "状态" 查看等候时间更新
• 发送 "设置" 更新您的偏好
• 发送 "帮助" 查看此消息

您也可以使用下面的按钮：
        """
        
        from ..core.notification_service import MessageRequest, MessageChannel
        
        request = MessageRequest(
            recipient=phone_number,
            channel=MessageChannel.WHATSAPP,
            body=help_text,
            actions=[
                {"id": "check_status", "text": "查看状态"},
                {"id": "update_preferences", "text": "更新设置"}
            ]
        )
        
        await self.notification_service.send_message(request)
    
    async def _process_patient_setup(self, screen_data: Dict[str, Any], phone_number: str):
        """处理患者设置数据"""
        try:
            # 从Flow数据创建患者档案
            patient_data = {
                'phone_number': phone_number,
                'postcode': screen_data.get('postcode'),
                'medical_specialties': screen_data.get('specialties', []),
                'preferred_travel_distance': int(screen_data.get('travel_distance', 50))
            }
            
            patient = await self.patient_service.create_patient(patient_data)
            
            # 发送确认消息
            from ..core.notification_service import MessageRequest, MessageChannel
            
            request = MessageRequest(
                recipient=phone_number,
                channel=MessageChannel.WHATSAPP,
                body="✅ 您的档案已成功创建！我们会在有等候时间更新时通知您。"
            )
            
            await self.notification_service.send_message(request)
            
        except Exception as e:
            logger.error(f"Failed to process patient setup: {e}")
    
    async def _process_preferences_update(self, patient_id: str, screen_data: Dict[str, Any]):
        """处理偏好更新"""
        try:
            updates = {}
            
            if 'travel_distance' in screen_data:
                updates['preferred_travel_distance'] = int(screen_data['travel_distance'])
            
            if 'max_wait_weeks' in screen_data:
                updates['max_acceptable_wait_weeks'] = int(screen_data['max_wait_weeks'])
            
            if 'specialties' in screen_data:
                updates['medical_specialties'] = screen_data['specialties']
            
            await self.patient_service.update_patient_preferences(patient_id, updates)
            
        except Exception as e:
            logger.error(f"Failed to update patient preferences: {e}")
    
    async def _handle_unsubscribe(self, patient_id: str, phone_number: str):
        """处理退订请求"""
        # 停用所有订阅
        subscriptions = await self.patient_service.get_patient_subscriptions(patient_id)
        
        for subscription in subscriptions:
            await self.patient_service.update_subscription(
                subscription.id,
                {'enabled': False}
            )
        
        # 发送确认消息
        from ..core.notification_service import MessageRequest, MessageChannel
        
        request = MessageRequest(
            recipient=phone_number,
            channel=MessageChannel.WHATSAPP,
            body="您已成功退订所有提醒。如需重新订阅，请发送'设置'。"
        )
        
        await self.notification_service.send_message(request)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取Webhook统计信息"""
        return {
            **self.stats,
            'queue_size': self.event_queue.qsize(),
            'registered_handlers': sum(len(handlers) for handlers in self.event_handlers.values())
        } 