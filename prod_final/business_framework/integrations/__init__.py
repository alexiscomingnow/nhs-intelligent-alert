"""
外部服务集成模块

提供与第三方服务的集成组件：
- WhatsApp Business Cloud API
- SMS服务 (Twilio等)
- 邮件服务 (SMTP, SendGrid等)
- 支付服务 (Stripe, PayPal等)
- GP Connect API
- NHS APIs
"""

from .whatsapp_client import WhatsAppClient
from .sms_client import SMSClient
from .email_client import EmailClient

__all__ = [
    'WhatsAppClient',
    'SMSClient', 
    'EmailClient'
] 