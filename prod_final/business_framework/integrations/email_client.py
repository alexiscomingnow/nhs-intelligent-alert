"""
Email客户端 - 支持SMTP和第三方邮件服务

支持的服务：
- SMTP (任何SMTP服务器)
- SendGrid
- AWS SES
- Mailgun
"""

import asyncio
import logging
import aiosmtplib
import aiohttp
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
from datetime import datetime
import base64
import json

from ..core.notification_service import MessageProvider, MessageRequest, MessageResult, MessageChannel, MessageStatus

logger = logging.getLogger(__name__)

class EmailProvider(ABC):
    """邮件提供商抽象基类"""
    
    @abstractmethod
    async def send_email(self, to: List[str], subject: str, body: str, html_body: Optional[str] = None, 
                        from_email: Optional[str] = None, attachments: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """发送邮件"""
        pass

class SMTPProvider(EmailProvider):
    """SMTP邮件提供商"""
    
    def __init__(self, host: str, port: int, username: str, password: str, use_tls: bool = True, from_email: str = ""):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.from_email = from_email
    
    async def send_email(self, to: List[str], subject: str, body: str, html_body: Optional[str] = None,
                        from_email: Optional[str] = None, attachments: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """通过SMTP发送邮件"""
        try:
            # 创建邮件消息
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = from_email or self.from_email
            msg['To'] = ', '.join(to)
            
            # 添加文本内容
            text_part = MIMEText(body, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # 添加HTML内容
            if html_body:
                html_part = MIMEText(html_body, 'html', 'utf-8')
                msg.attach(html_part)
            
            # 添加附件
            if attachments:
                for attachment in attachments:
                    await self._add_attachment(msg, attachment)
            
            # 发送邮件
            smtp_client = aiosmtplib.SMTP(hostname=self.host, port=self.port, use_tls=self.use_tls)
            await smtp_client.connect()
            
            if self.username and self.password:
                await smtp_client.login(self.username, self.password)
            
            await smtp_client.send_message(msg)
            await smtp_client.quit()
            
            return {
                'success': True,
                'message_id': msg.get('Message-ID', 'smtp_' + str(datetime.now().timestamp()))
            }
            
        except Exception as e:
            logger.error(f"SMTP send failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _add_attachment(self, msg: MIMEMultipart, attachment: Dict[str, Any]):
        """添加邮件附件"""
        try:
            part = MIMEBase('application', 'octet-stream')
            
            if 'content' in attachment:
                part.set_payload(attachment['content'])
            elif 'path' in attachment:
                with open(attachment['path'], 'rb') as f:
                    part.set_payload(f.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {attachment.get("filename", "attachment")}'
            )
            
            msg.attach(part)
            
        except Exception as e:
            logger.error(f"Failed to add attachment: {e}")

class SendGridProvider(EmailProvider):
    """SendGrid邮件提供商"""
    
    def __init__(self, api_key: str, from_email: str):
        self.api_key = api_key
        self.from_email = from_email
        self.api_url = "https://api.sendgrid.com/v3/mail/send"
    
    async def send_email(self, to: List[str], subject: str, body: str, html_body: Optional[str] = None,
                        from_email: Optional[str] = None, attachments: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """通过SendGrid发送邮件"""
        try:
            # 构建SendGrid API请求
            payload = {
                "personalizations": [{
                    "to": [{"email": email} for email in to],
                    "subject": subject
                }],
                "from": {"email": from_email or self.from_email},
                "content": [
                    {"type": "text/plain", "value": body}
                ]
            }
            
            # 添加HTML内容
            if html_body:
                payload["content"].append({"type": "text/html", "value": html_body})
            
            # 添加附件
            if attachments:
                payload["attachments"] = []
                for attachment in attachments:
                    sg_attachment = {
                        "content": base64.b64encode(attachment.get('content', b'')).decode(),
                        "filename": attachment.get('filename', 'attachment'),
                        "type": attachment.get('type', 'application/octet-stream')
                    }
                    payload["attachments"].append(sg_attachment)
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload, headers=headers) as response:
                    if response.status == 202:
                        return {
                            'success': True,
                            'message_id': response.headers.get('X-Message-Id', 'sendgrid_' + str(datetime.now().timestamp()))
                        }
                    else:
                        error_text = await response.text()
                        return {
                            'success': False,
                            'error': f"SendGrid error {response.status}: {error_text}"
                        }
            
        except Exception as e:
            logger.error(f"SendGrid send failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

class EmailClient(MessageProvider):
    """
    Email客户端
    
    支持多种邮件服务提供商
    """
    
    def __init__(self, config_manager):
        self.config = config_manager
        
        # 获取邮件配置
        business_config = self.config.get_business_config()
        email_config = business_config.notifications.get('email', {})
        
        self.enabled = email_config.get('enabled', True)
        
        if not self.enabled:
            logger.warning("Email service is disabled")
            return
        
        # 初始化提供商
        self.providers: List[EmailProvider] = []
        self._init_providers(email_config)
        
        # 默认发件人
        self.default_from = email_config.get('from_email', 'noreply@example.com')
        
        # 统计信息
        self.stats = {
            'emails_sent': 0,
            'emails_failed': 0,
            'provider_failures': {}
        }
    
    def _init_providers(self, email_config: Dict[str, Any]):
        """初始化邮件提供商"""
        primary_provider = email_config.get('provider', 'smtp').lower()
        
        # SMTP提供商
        if primary_provider == 'smtp' or 'smtp' in email_config:
            smtp_config = email_config.get('smtp', email_config)
            if all(key in smtp_config for key in ['smtp_host', 'smtp_port']):
                provider = SMTPProvider(
                    host=smtp_config['smtp_host'],
                    port=int(smtp_config['smtp_port']),
                    username=smtp_config.get('smtp_user', ''),
                    password=smtp_config.get('smtp_password', ''),
                    use_tls=smtp_config.get('use_tls', True),
                    from_email=smtp_config.get('from_email', self.default_from)
                )
                self.providers.append(provider)
                logger.info("Initialized SMTP email provider")
        
        # SendGrid提供商
        if primary_provider == 'sendgrid' or 'sendgrid' in email_config:
            sendgrid_config = email_config.get('sendgrid', {})
            if 'api_key' in sendgrid_config:
                provider = SendGridProvider(
                    api_key=sendgrid_config['api_key'],
                    from_email=sendgrid_config.get('from_email', self.default_from)
                )
                self.providers.append(provider)
                logger.info("Initialized SendGrid email provider")
        
        if not self.providers:
            logger.error("No email providers configured")
    
    def get_supported_channels(self) -> List[MessageChannel]:
        """获取支持的消息渠道"""
        return [MessageChannel.EMAIL] if self.enabled else []
    
    async def send_message(self, request: MessageRequest) -> MessageResult:
        """发送邮件消息"""
        if not self.enabled or not self.providers:
            return MessageResult(
                request_id=request.id,
                success=False,
                status=MessageStatus.FAILED,
                channel=MessageChannel.EMAIL,
                error_message="Email service not available"
            )
        
        # 解析收件人
        recipients = [request.recipient] if isinstance(request.recipient, str) else request.recipient
        
        # 生成HTML版本（如果需要）
        html_body = None
        if request.metadata.get('html_template'):
            html_body = self._generate_html_body(request.body, request.metadata.get('html_template'))
        
        # 尝试发送，支持故障转移
        last_error = None
        
        for provider in self.providers:
            try:
                result = await provider.send_email(
                    to=recipients,
                    subject=request.subject or "Notification",
                    body=request.body,
                    html_body=html_body,
                    from_email=request.metadata.get('from_email'),
                    attachments=request.attachments
                )
                
                if result.get('success'):
                    self.stats['emails_sent'] += 1
                    
                    return MessageResult(
                        request_id=request.id,
                        success=True,
                        status=MessageStatus.SENT,
                        channel=MessageChannel.EMAIL,
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
                
                logger.error(f"Email provider {provider_name} failed: {e}")
        
        # 所有提供商都失败
        self.stats['emails_failed'] += 1
        
        return MessageResult(
            request_id=request.id,
            success=False,
            status=MessageStatus.FAILED,
            channel=MessageChannel.EMAIL,
            error_message=f"All email providers failed. Last error: {last_error}"
        )
    
    async def get_message_status(self, external_id: str) -> MessageStatus:
        """获取邮件消息状态"""
        # 大多数邮件服务不提供实时状态查询
        # 状态通常通过webhook回调获得
        return MessageStatus.SENT
    
    def _generate_html_body(self, text_body: str, template: str) -> str:
        """生成HTML邮件内容"""
        # 简单的HTML模板处理
        if template == 'notification':
            html_template = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Notification</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .container {{ max-width: 600px; margin: 0 auto; }}
                    .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; background-color: #f8f9fa; }}
                    .footer {{ padding: 10px; text-align: center; color: #6c757d; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>NHS Alert System</h1>
                    </div>
                    <div class="content">
                        {text_body.replace(chr(10), '<br>')}
                    </div>
                    <div class="footer">
                        <p>This is an automated notification from NHS Alert System.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            return html_template
        else:
            # 简单转换：换行转为<br>
            return text_body.replace('\n', '<br>')
    
    async def send_templated_email(self, to: List[str], template_name: str, variables: Dict[str, Any], 
                                  from_email: Optional[str] = None) -> MessageResult:
        """发送模板邮件"""
        # 这里可以集成更复杂的模板系统
        # 例如Jinja2模板
        
        templates = {
            'welcome': {
                'subject': 'Welcome to NHS Alert System',
                'body': 'Hello {name}, welcome to our service!'
            },
            'alert': {
                'subject': 'NHS Alert: {alert_type}',
                'body': 'Alert: {message}\n\nBest regards,\nNHS Alert Team'
            }
        }
        
        if template_name not in templates:
            return MessageResult(
                request_id="templated_email",
                success=False,
                status=MessageStatus.FAILED,
                channel=MessageChannel.EMAIL,
                error_message=f"Template '{template_name}' not found"
            )
        
        template = templates[template_name]
        
        # 替换变量
        subject = template['subject'].format(**variables)
        body = template['body'].format(**variables)
        
        request = MessageRequest(
            recipient=to[0] if len(to) == 1 else to,
            channel=MessageChannel.EMAIL,
            subject=subject,
            body=body,
            metadata={'from_email': from_email} if from_email else {}
        )
        
        return await self.send_message(request)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            'providers_count': len(self.providers),
            'enabled': self.enabled
        } 