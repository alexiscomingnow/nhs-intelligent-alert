"""
WhatsApp Business Cloud API 客户端

特性：
1. 消息发送 (文本、模板、媒体)
2. WhatsApp Flow 管理
3. Webhook事件处理
4. 消息状态追踪
5. 用户交互处理
6. 模板消息管理
"""

import asyncio
import logging
import json
import aiohttp
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hmac
import hashlib
import base64

from ..core.notification_service import MessageProvider, MessageRequest, MessageResult, MessageChannel, MessageStatus

logger = logging.getLogger(__name__)

class WhatsAppMessageType(Enum):
    """WhatsApp消息类型"""
    TEXT = "text"
    TEMPLATE = "template"
    INTERACTIVE = "interactive"
    IMAGE = "image"
    DOCUMENT = "document"
    FLOW = "flow"

@dataclass
class WhatsAppTemplate:
    """WhatsApp模板消息"""
    name: str
    language_code: str = "en_US"
    components: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class WhatsAppFlow:
    """WhatsApp Flow配置"""
    id: str
    name: str
    version: str
    screens: List[Dict[str, Any]] = field(default_factory=list)
    data_api_version: str = "3.0"

@dataclass
class WhatsAppInteractiveMessage:
    """WhatsApp交互式消息"""
    type: str  # "button", "list", "flow"
    header: Optional[Dict[str, Any]] = None
    body: Dict[str, str] = field(default_factory=dict)
    footer: Optional[Dict[str, str]] = None
    action: Dict[str, Any] = field(default_factory=dict)

class WhatsAppClient(MessageProvider):
    """
    WhatsApp Business Cloud API 客户端
    
    支持：
    - 发送各种类型的消息
    - 管理WhatsApp Flow
    - 处理Webhook事件
    - 模板消息管理
    """
    
    def __init__(self, config_manager):
        self.config = config_manager
        
        # API配置
        business_config = self.config.get_business_config()
        whatsapp_config = business_config.notifications.get('whatsapp', {})
        
        self.api_url = whatsapp_config.get('api_url', 'https://graph.facebook.com/v18.0')
        self.phone_number_id = whatsapp_config.get('phone_number_id')
        self.access_token = whatsapp_config.get('access_token')
        self.webhook_verify_token = whatsapp_config.get('webhook_verify_token')
        
        if not all([self.phone_number_id, self.access_token]):
            raise ValueError("WhatsApp phone_number_id and access_token are required")
        
        # HTTP会话
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Webhook事件处理器
        self.event_handlers: Dict[str, Callable] = {}
        
        # Flow缓存
        self.flows_cache: Dict[str, WhatsAppFlow] = {}
        
        # 统计信息
        self.stats = {
            'messages_sent': 0,
            'messages_delivered': 0,
            'messages_read': 0,
            'webhook_events': 0
        }
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    def get_supported_channels(self) -> List[MessageChannel]:
        """获取支持的消息渠道"""
        return [MessageChannel.WHATSAPP]
    
    async def send_message(self, request: MessageRequest) -> MessageResult:
        """发送WhatsApp消息"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            # 构建消息payload
            payload = await self._build_message_payload(request)
            
            # 发送API请求
            response = await self._send_api_request('messages', payload)
            
            if response.get('messages'):
                message_id = response['messages'][0]['id']
                self.stats['messages_sent'] += 1
                
                return MessageResult(
                    request_id=request.id,
                    success=True,
                    status=MessageStatus.SENT,
                    channel=MessageChannel.WHATSAPP,
                    external_id=message_id,
                    sent_at=datetime.now()
                )
            else:
                return MessageResult(
                    request_id=request.id,
                    success=False,
                    status=MessageStatus.FAILED,
                    channel=MessageChannel.WHATSAPP,
                    error_message="No message ID returned"
                )
        
        except Exception as e:
            logger.error(f"WhatsApp message send failed: {e}")
            return MessageResult(
                request_id=request.id,
                success=False,
                status=MessageStatus.FAILED,
                channel=MessageChannel.WHATSAPP,
                error_message=str(e)
            )
    
    async def _build_message_payload(self, request: MessageRequest) -> Dict[str, Any]:
        """构建消息payload"""
        payload = {
            "messaging_product": "whatsapp",
            "to": self._normalize_phone_number(request.recipient),
            "type": "text"
        }
        
        # 处理模板消息
        if 'whatsapp_template' in request.metadata:
            template_data = request.metadata['whatsapp_template']
            payload.update({
                "type": "template",
                "template": {
                    "name": template_data['name'],
                    "language": {"code": template_data.get('language', 'en_US')},
                    "components": template_data.get('components', [])
                }
            })
        
        # 处理交互式消息
        elif request.actions:
            payload.update({
                "type": "interactive",
                "interactive": self._build_interactive_content(request)
            })
        
        # 处理Flow消息
        elif 'flow_id' in request.metadata:
            payload.update({
                "type": "interactive",
                "interactive": {
                    "type": "flow",
                    "header": {"type": "text", "text": request.subject or "Setup"},
                    "body": {"text": request.body},
                    "action": {
                        "name": "flow",
                        "parameters": {
                            "flow_message_version": "3",
                            "flow_id": request.metadata['flow_id'],
                            "flow_cta": request.metadata.get('flow_cta', 'Start'),
                            "flow_action": "navigate",
                            "flow_action_payload": request.metadata.get('flow_payload', {})
                        }
                    }
                }
            })
        
        # 普通文本消息
        else:
            payload.update({
                "type": "text",
                "text": {"body": request.body}
            })
        
        return payload
    
    def _build_interactive_content(self, request: MessageRequest) -> Dict[str, Any]:
        """构建交互式消息内容"""
        if len(request.actions) <= 3:
            # 按钮消息
            buttons = []
            for i, action in enumerate(request.actions[:3]):
                buttons.append({
                    "type": "reply",
                    "reply": {
                        "id": action.get('id', f"btn_{i}"),
                        "title": action.get('text', f'Option {i+1}')[:20]  # 最多20字符
                    }
                })
            
            return {
                "type": "button",
                "body": {"text": request.body},
                "action": {"buttons": buttons}
            }
        else:
            # 列表消息
            rows = []
            for action in request.actions[:10]:  # 最多10个选项
                rows.append({
                    "id": action.get('id', str(len(rows))),
                    "title": action.get('text', f'Option {len(rows)+1}')[:24],  # 最多24字符
                    "description": action.get('description', '')[:72]  # 最多72字符
                })
            
            return {
                "type": "list",
                "body": {"text": request.body},
                "action": {
                    "button": "Choose Option",
                    "sections": [{
                        "title": "Options",
                        "rows": rows
                    }]
                }
            }
    
    def _normalize_phone_number(self, phone: str) -> str:
        """规范化电话号码格式"""
        # 移除非数字字符
        clean_phone = ''.join(filter(str.isdigit, phone))
        
        # 确保包含国际区号
        if clean_phone.startswith('44'):
            return clean_phone
        elif clean_phone.startswith('0'):
            return '44' + clean_phone[1:]  # 英国号码
        else:
            return '44' + clean_phone  # 假设是英国号码
    
    async def get_message_status(self, external_id: str) -> MessageStatus:
        """获取消息状态"""
        try:
            # WhatsApp不提供直接查询消息状态的API
            # 状态通过webhook更新
            return MessageStatus.SENT
        except Exception as e:
            logger.error(f"Failed to get message status: {e}")
            return MessageStatus.FAILED
    
    async def create_flow(self, flow: WhatsAppFlow) -> str:
        """创建WhatsApp Flow"""
        try:
            payload = {
                "name": flow.name,
                "categories": ["OTHER"],
                "clone_flow_id": None
            }
            
            response = await self._send_api_request('flows', payload, method='POST')
            flow_id = response.get('id')
            
            if flow_id:
                # 更新Flow内容
                await self.update_flow(flow_id, flow)
                self.flows_cache[flow_id] = flow
                logger.info(f"Created WhatsApp Flow: {flow_id}")
                return flow_id
            
        except Exception as e:
            logger.error(f"Failed to create flow: {e}")
            raise
        
        return ""
    
    async def update_flow(self, flow_id: str, flow: WhatsAppFlow) -> bool:
        """更新WhatsApp Flow"""
        try:
            # 构建Flow JSON
            flow_json = {
                "version": flow.version,
                "data_api_version": flow.data_api_version,
                "routing_model": {
                    "INITIAL_SCREEN": flow.screens[0]['id'] if flow.screens else "SCREEN_1"
                },
                "screens": flow.screens
            }
            
            payload = {
                "flow_json": json.dumps(flow_json),
                "preview": {
                    "body": f"Preview of {flow.name}",
                    "header": "Flow Preview"
                }
            }
            
            response = await self._send_api_request(f'flows/{flow_id}', payload, method='POST')
            
            if response.get('success'):
                logger.info(f"Updated WhatsApp Flow: {flow_id}")
                return True
            
        except Exception as e:
            logger.error(f"Failed to update flow {flow_id}: {e}")
        
        return False
    
    async def publish_flow(self, flow_id: str) -> bool:
        """发布WhatsApp Flow"""
        try:
            payload = {"action": "PUBLISH"}
            response = await self._send_api_request(f'flows/{flow_id}', payload, method='POST')
            
            if response.get('success'):
                logger.info(f"Published WhatsApp Flow: {flow_id}")
                return True
            
        except Exception as e:
            logger.error(f"Failed to publish flow {flow_id}: {e}")
        
        return False
    
    async def handle_webhook(self, body: bytes, signature: str) -> Dict[str, Any]:
        """处理WhatsApp Webhook事件"""
        # 验证签名
        if not self._verify_webhook_signature(body, signature):
            raise ValueError("Invalid webhook signature")
        
        try:
            data = json.loads(body.decode('utf-8'))
            self.stats['webhook_events'] += 1
            
            # 处理事件
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    await self._process_webhook_change(change)
            
            return {"status": "ok"}
            
        except Exception as e:
            logger.error(f"Webhook processing failed: {e}")
            raise
    
    async def _process_webhook_change(self, change: Dict[str, Any]):
        """处理webhook变更事件"""
        field = change.get('field')
        value = change.get('value', {})
        
        if field == 'messages':
            # 处理收到的消息
            for message in value.get('messages', []):
                await self._handle_incoming_message(message, value.get('contacts', []))
            
            # 处理消息状态更新
            for status in value.get('statuses', []):
                await self._handle_message_status(status)
        
        elif field == 'message_template_status_update':
            # 处理模板状态更新
            await self._handle_template_status(value)
    
    async def _handle_incoming_message(self, message: Dict[str, Any], contacts: List[Dict[str, Any]]):
        """处理收到的消息"""
        message_id = message.get('id')
        from_number = message.get('from')
        message_type = message.get('type')
        timestamp = message.get('timestamp')
        
        # 获取发送者信息
        sender_name = None
        if contacts:
            sender_name = contacts[0].get('profile', {}).get('name')
        
        # 根据消息类型处理
        if message_type == 'text':
            text_content = message.get('text', {}).get('body', '')
            await self._handle_text_message(from_number, text_content, sender_name)
        
        elif message_type == 'interactive':
            interactive = message.get('interactive', {})
            if interactive.get('type') == 'button_reply':
                button_id = interactive.get('button_reply', {}).get('id')
                await self._handle_button_click(from_number, button_id, sender_name)
            elif interactive.get('type') == 'list_reply':
                list_id = interactive.get('list_reply', {}).get('id')
                await self._handle_list_selection(from_number, list_id, sender_name)
            elif interactive.get('type') == 'nfm_reply':
                # Flow回复
                response_json = interactive.get('nfm_reply', {}).get('response_json')
                if response_json:
                    await self._handle_flow_response(from_number, json.loads(response_json), sender_name)
        
        logger.info(f"Processed incoming message from {from_number}: {message_type}")
    
    async def _handle_message_status(self, status: Dict[str, Any]):
        """处理消息状态更新"""
        message_id = status.get('id')
        recipient_id = status.get('recipient_id')
        status_type = status.get('status')
        timestamp = status.get('timestamp')
        
        # 更新统计
        if status_type == 'delivered':
            self.stats['messages_delivered'] += 1
        elif status_type == 'read':
            self.stats['messages_read'] += 1
        
        # 调用注册的处理器
        if 'message_status' in self.event_handlers:
            await self.event_handlers['message_status'](message_id, status_type, recipient_id)
        
        logger.debug(f"Message {message_id} status: {status_type}")
    
    async def _handle_text_message(self, from_number: str, text: str, sender_name: Optional[str]):
        """处理文本消息"""
        if 'text_message' in self.event_handlers:
            await self.event_handlers['text_message'](from_number, text, sender_name)
    
    async def _handle_button_click(self, from_number: str, button_id: str, sender_name: Optional[str]):
        """处理按钮点击"""
        if 'button_click' in self.event_handlers:
            await self.event_handlers['button_click'](from_number, button_id, sender_name)
    
    async def _handle_list_selection(self, from_number: str, list_id: str, sender_name: Optional[str]):
        """处理列表选择"""
        if 'list_selection' in self.event_handlers:
            await self.event_handlers['list_selection'](from_number, list_id, sender_name)
    
    async def _handle_flow_response(self, from_number: str, response_data: Dict[str, Any], sender_name: Optional[str]):
        """处理Flow响应"""
        if 'flow_response' in self.event_handlers:
            await self.event_handlers['flow_response'](from_number, response_data, sender_name)
    
    async def _handle_template_status(self, status_data: Dict[str, Any]):
        """处理模板状态更新"""
        if 'template_status' in self.event_handlers:
            await self.event_handlers['template_status'](status_data)
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """注册事件处理器"""
        self.event_handlers[event_type] = handler
        logger.info(f"Registered handler for event: {event_type}")
    
    def _verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        """验证webhook签名"""
        if not self.webhook_verify_token:
            return False
        
        expected_signature = hmac.new(
            self.webhook_verify_token.encode('utf-8'),
            body,
            hashlib.sha256
        ).hexdigest()
        
        # WhatsApp使用sha256=前缀
        if signature.startswith('sha256='):
            signature = signature[7:]
        
        return hmac.compare_digest(expected_signature, signature)
    
    async def _send_api_request(self, endpoint: str, payload: Dict[str, Any], method: str = 'POST') -> Dict[str, Any]:
        """发送API请求"""
        url = f"{self.api_url}/{self.phone_number_id}/{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        async with self.session.request(method, url, json=payload, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                logger.error(f"WhatsApp API error {response.status}: {error_text}")
                raise Exception(f"WhatsApp API error: {response.status} - {error_text}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            'cached_flows': len(self.flows_cache),
            'registered_handlers': len(self.event_handlers)
        } 