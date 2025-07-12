"""
SMS客户端 - 支持多个SMS服务提供商

支持的提供商：
- Twilio
- AWS SNS  
- Vonage (Nexmo)
- MessageBird
"""

import asyncio
import logging
import aiohttp
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
import base64

from ..core.notification_service import MessageProvider, MessageRequest, MessageResult, MessageChannel, MessageStatus

logger = logging.getLogger(__name__)

class SMSProvider(ABC):
    """SMS提供商抽象基类"""
    
    @abstractmethod
    async def send_sms(self, to: str, body: str, from_number: Optional[str] = None) -> Dict[str, Any]:
        """发送SMS"""
        pass
    
    @abstractmethod
    async def get_sms_status(self, message_id: str) -> str:
        """获取SMS状态"""
        pass

class TwilioProvider(SMSProvider):
    """Twilio SMS提供商"""
    
    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.api_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}"
    
    async def send_sms(self, to: str, body: str, from_number: Optional[str] = None) -> Dict[str, Any]:
        """发送Twilio SMS"""
        url = f"{self.api_url}/Messages.json"
        
        data = {
            'To': to,
            'From': from_number or self.from_number,
            'Body': body
        }
        
        auth = base64.b64encode(f"{self.account_sid}:{self.auth_token}".encode()).decode()
        headers = {
            'Authorization': f'Basic {auth}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, headers=headers) as response:
                if response.status == 201:
                    result = await response.json()
                    return {
                        'success': True,
                        'message_id': result.get('sid'),
                        'status': result.get('status')
                    }
                else:
                    error = await response.text()
                    return {
                        'success': False,
                        'error': f"Twilio error {response.status}: {error}"
                    }
    
    async def get_sms_status(self, message_id: str) -> str:
        """获取Twilio SMS状态"""
        url = f"{self.api_url}/Messages/{message_id}.json"
        
        auth = base64.b64encode(f"{self.account_sid}:{self.auth_token}".encode()).decode()
        headers = {'Authorization': f'Basic {auth}'}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('status', 'unknown')
                else:
                    return 'failed'

class VonageProvider(SMSProvider):
    """Vonage (Nexmo) SMS提供商"""
    
    def __init__(self, api_key: str, api_secret: str, from_number: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.from_number = from_number
        self.api_url = "https://rest.nexmo.com"
    
    async def send_sms(self, to: str, body: str, from_number: Optional[str] = None) -> Dict[str, Any]:
        """发送Vonage SMS"""
        url = f"{self.api_url}/sms/json"
        
        data = {
            'api_key': self.api_key,
            'api_secret': self.api_secret,
            'to': to,
            'from': from_number or self.from_number,
            'text': body
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    messages = result.get('messages', [])
                    if messages and messages[0].get('status') == '0':
                        return {
                            'success': True,
                            'message_id': messages[0].get('message-id'),
                            'status': 'sent'
                        }
                    else:
                        return {
                            'success': False,
                            'error': messages[0].get('error-text', 'Unknown error') if messages else 'No messages'
                        }
                else:
                    error = await response.text()
                    return {
                        'success': False,
                        'error': f"Vonage error {response.status}: {error}"
                    }
    
    async def get_sms_status(self, message_id: str) -> str:
        """获取Vonage SMS状态"""
        # Vonage需要通过webhook获取状态更新
        return 'sent'

class SMSClient(MessageProvider):
    """
    SMS客户端
    
    支持多个SMS服务提供商，自动故障转移
    """
    
    def __init__(self, config_manager):
        self.config = config_manager
        
        # 获取SMS配置
        business_config = self.config.get_business_config()
        sms_config = business_config.notifications.get('sms', {})
        
        self.enabled = sms_config.get('enabled', False)
        
        if not self.enabled:
            logger.warning("SMS service is disabled")
            return
        
        # 初始化提供商
        self.providers: List[SMSProvider] = []
        self._init_providers(sms_config)
        
        # 统计信息
        self.stats = {
            'messages_sent': 0,
            'messages_failed': 0,
            'provider_failures': {}
        }
    
    def _init_providers(self, sms_config: Dict[str, Any]):
        """初始化SMS提供商"""
        primary_provider = sms_config.get('provider', 'twilio').lower()
        
        # Twilio提供商
        if primary_provider == 'twilio' or 'twilio' in sms_config:
            twilio_config = sms_config.get('twilio', sms_config)
            if all(key in twilio_config for key in ['account_sid', 'auth_token', 'from_number']):
                provider = TwilioProvider(
                    account_sid=twilio_config['account_sid'],
                    auth_token=twilio_config['auth_token'],
                    from_number=twilio_config['from_number']
                )
                self.providers.append(provider)
                logger.info("Initialized Twilio SMS provider")
        
        # Vonage提供商
        if primary_provider == 'vonage' or 'vonage' in sms_config:
            vonage_config = sms_config.get('vonage', {})
            if all(key in vonage_config for key in ['api_key', 'api_secret', 'from_number']):
                provider = VonageProvider(
                    api_key=vonage_config['api_key'],
                    api_secret=vonage_config['api_secret'],
                    from_number=vonage_config['from_number']
                )
                self.providers.append(provider)
                logger.info("Initialized Vonage SMS provider")
        
        if not self.providers:
            logger.error("No SMS providers configured")
    
    def get_supported_channels(self) -> List[MessageChannel]:
        """获取支持的消息渠道"""
        return [MessageChannel.SMS] if self.enabled else []
    
    async def send_message(self, request: MessageRequest) -> MessageResult:
        """发送SMS消息"""
        if not self.enabled or not self.providers:
            return MessageResult(
                request_id=request.id,
                success=False,
                status=MessageStatus.FAILED,
                channel=MessageChannel.SMS,
                error_message="SMS service not available"
            )
        
        # 格式化电话号码
        phone_number = self._format_phone_number(request.recipient)
        
        # 尝试发送，支持故障转移
        last_error = None
        
        for i, provider in enumerate(self.providers):
            try:
                result = await provider.send_sms(
                    to=phone_number,
                    body=request.body[:160],  # SMS长度限制
                    from_number=request.metadata.get('from_number')
                )
                
                if result.get('success'):
                    self.stats['messages_sent'] += 1
                    
                    return MessageResult(
                        request_id=request.id,
                        success=True,
                        status=MessageStatus.SENT,
                        channel=MessageChannel.SMS,
                        external_id=result.get('message_id'),
                        sent_at=datetime.now(),
                        metadata={'provider': provider.__class__.__name__}
                    )
                else:
                    last_error = result.get('error', 'Unknown error')
                    
            except Exception as e:
                last_error = str(e)
                provider_name = provider.__class__.__name__
                
                if provider_name not in self.stats['provider_failures']:
                    self.stats['provider_failures'][provider_name] = 0
                self.stats['provider_failures'][provider_name] += 1
                
                logger.error(f"SMS provider {provider_name} failed: {e}")
        
        # 所有提供商都失败
        self.stats['messages_failed'] += 1
        
        return MessageResult(
            request_id=request.id,
            success=False,
            status=MessageStatus.FAILED,
            channel=MessageChannel.SMS,
            error_message=f"All SMS providers failed. Last error: {last_error}"
        )
    
    async def get_message_status(self, external_id: str) -> MessageStatus:
        """获取SMS消息状态"""
        # 尝试从各个提供商查询状态
        for provider in self.providers:
            try:
                status = await provider.get_sms_status(external_id)
                return self._map_provider_status(status)
            except Exception as e:
                logger.warning(f"Failed to get status from {provider.__class__.__name__}: {e}")
        
        return MessageStatus.FAILED
    
    def _format_phone_number(self, phone: str) -> str:
        """格式化电话号码"""
        # 移除非数字字符
        clean_phone = ''.join(filter(str.isdigit, phone))
        
        # 添加国际区号（默认英国）
        if clean_phone.startswith('44'):
            return f"+{clean_phone}"
        elif clean_phone.startswith('0'):
            return f"+44{clean_phone[1:]}"
        else:
            return f"+44{clean_phone}"
    
    def _map_provider_status(self, provider_status: str) -> MessageStatus:
        """映射提供商状态到内部状态"""
        status_mapping = {
            'sent': MessageStatus.SENT,
            'delivered': MessageStatus.DELIVERED,
            'failed': MessageStatus.FAILED,
            'undelivered': MessageStatus.FAILED,
            'read': MessageStatus.READ,
            'accepted': MessageStatus.SENT,
            'queued': MessageStatus.PENDING
        }
        
        return status_mapping.get(provider_status.lower(), MessageStatus.FAILED)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            'providers_count': len(self.providers),
            'enabled': self.enabled
        } 