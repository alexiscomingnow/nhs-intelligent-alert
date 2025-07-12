"""
WhatsApp Configuration Settings
Store all WhatsApp integration configuration here
"""

import os
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class WhatsAppConfig:
    """WhatsApp Configuration Class"""
    
    # API Credentials
    access_token: str = ""
    phone_number_id: str = ""
    verify_token: str = "nhs_webhook_verify_token_2024"
    webhook_url: str = "https://your-domain.com/webhook"
    
    # Business Information
    business_name: str = "NHS Waiting List Alert Service"
    business_phone: str = ""
    
    # API URLs
    graph_api_url: str = "https://graph.facebook.com/v18.0"
    webhook_endpoint: str = "/webhook"
    
    # Message Templates
    welcome_template: str = """
🏥 *NHS Waiting List Alert Service*

Welcome! I'll help you monitor NHS waiting times and get timely alerts.

Let's set up your preferences:
1️⃣ Enter your postcode
2️⃣ Select medical specialties
3️⃣ Set alert preferences
4️⃣ Choose notification frequency

Type *start* to begin setup!
    """
    
    help_template: str = """
📋 *Available Commands:*

🔹 *setup* - Start preference setup
🔹 *status* - Check your current alerts
🔹 *alerts* - View recent notifications
🔹 *update* - Update preferences
🔹 *trends* - View waiting time trends
🔹 *help* - Show this help message
🔹 *stop* - Unsubscribe from alerts

💬 You can also ask natural questions like:
"What's the waiting time for cardiology?"
"Any shorter alternatives near me?"
    """
    
    # Alert Settings
    default_alert_frequency: str = "daily"  # daily, weekly, immediate
    max_daily_messages: int = 5
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "08:00"
    
    # System Settings
    webhook_timeout: int = 30
    api_timeout: int = 15
    retry_attempts: int = 3
    
    @classmethod
    def from_env(cls) -> 'WhatsAppConfig':
        """Load configuration from environment variables"""
        return cls(
            access_token=os.getenv('WHATSAPP_ACCESS_TOKEN', ''),
            phone_number_id=os.getenv('WHATSAPP_PHONE_NUMBER_ID', ''),
            verify_token=os.getenv('WHATSAPP_VERIFY_TOKEN', 'nhs_webhook_verify_token_2024'),
            webhook_url=os.getenv('WHATSAPP_WEBHOOK_URL', 'https://your-domain.com/webhook'),
            business_name=os.getenv('WHATSAPP_BUSINESS_NAME', 'NHS Waiting List Alert Service'),
            business_phone=os.getenv('WHATSAPP_BUSINESS_PHONE', ''),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'access_token': self.access_token,
            'phone_number_id': self.phone_number_id,
            'verify_token': self.verify_token,
            'webhook_url': self.webhook_url,
            'business_name': self.business_name,
            'business_phone': self.business_phone,
            'graph_api_url': self.graph_api_url,
            'webhook_endpoint': self.webhook_endpoint,
            'default_alert_frequency': self.default_alert_frequency,
            'max_daily_messages': self.max_daily_messages,
            'quiet_hours_start': self.quiet_hours_start,
            'quiet_hours_end': self.quiet_hours_end,
            'webhook_timeout': self.webhook_timeout,
            'api_timeout': self.api_timeout,
            'retry_attempts': self.retry_attempts,
        }
    
    def validate(self) -> bool:
        """Validate configuration"""
        required_fields = ['access_token', 'phone_number_id']
        missing_fields = [field for field in required_fields if not getattr(self, field)]
        
        if missing_fields:
            print(f"❌ Missing required WhatsApp configuration: {', '.join(missing_fields)}")
            return False
        
        print("✅ WhatsApp configuration is valid")
        return True

# Default configuration instance
whatsapp_config = WhatsAppConfig.from_env()

# Configuration setup instructions
SETUP_INSTRUCTIONS = """
🔧 WhatsApp Setup Instructions:

1. 📱 Create WhatsApp Business Account:
   - Go to https://business.whatsapp.com/
   - Sign up for WhatsApp Business API
   - Complete business verification

2. 🔑 Get API Credentials:
   - Visit https://developers.facebook.com/
   - Create a new app
   - Add WhatsApp Business API product
   - Get Phone Number ID and Access Token

3. 🌐 Set Environment Variables:
   WHATSAPP_ACCESS_TOKEN=your_access_token_here
   WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id_here
   WHATSAPP_VERIFY_TOKEN=nhs_webhook_verify_token_2024
   WHATSAPP_WEBHOOK_URL=https://your-domain.com/webhook
   WHATSAPP_BUSINESS_NAME=NHS Waiting List Alert Service
   WHATSAPP_BUSINESS_PHONE=+44xxxxxxxxxx

4. 🔗 Configure Webhook:
   - URL: https://your-domain.com/webhook
   - Verify Token: nhs_webhook_verify_token_2024
   - Subscribe to: messages, message_deliveries, message_reads

5. ✅ Test Configuration:
   python test_whatsapp_integration.py

📋 Required Meta Developer Settings:
- App Domain: your-domain.com
- Webhook URL: https://your-domain.com/webhook
- Callback URL: https://your-domain.com/webhook
- Verify Token: nhs_webhook_verify_token_2024

🔒 Security Notes:
- Keep Access Token secure
- Use HTTPS for webhook URL
- Validate all incoming webhooks
- Rate limit API calls
"""

# Template messages for different scenarios
MESSAGE_TEMPLATES = {
    'welcome': """
🏥 *NHS Waiting List Alert Service*

Hello! I'm here to help you monitor NHS waiting times and get personalized alerts.

🚀 *Quick Setup:*
Type *start* to begin your 2-minute setup!

📱 *What I can do:*
• Monitor waiting times for your area
• Send intelligent alerts when times change
• Suggest shorter alternatives
• Track GP appointment slots
• Provide weekly trends and insights

Need help? Type *help* anytime!
    """,
    
    'setup_postcode': """
📍 *Step 1: Your Location*

Please enter your postcode (e.g., SW1A 1AA):

This helps me find nearby hospitals and accurate waiting times for your area.
    """,
    
    'setup_specialty': """
🏥 *Step 2: Medical Specialties*

Please select specialties you're interested in:

1️⃣ Cardiology (Heart)
2️⃣ Orthopedics (Bones/Joints)
3️⃣ Ophthalmology (Eyes)
4️⃣ ENT (Ear, Nose, Throat)
5️⃣ Gastroenterology (Digestive)
6️⃣ Neurology (Brain/Nervous System)
7️⃣ Urology (Urinary System)
8️⃣ Dermatology (Skin)
9️⃣ General Surgery
🔟 Other (specify)

Reply with numbers (e.g., 1,3,5) or names
    """,
    
    'setup_preferences': """
⚙️ *Step 3: Alert Preferences*

How often would you like to receive alerts?

1️⃣ *Immediate* - Get notified instantly when waiting times change significantly
2️⃣ *Daily* - Daily summary at 9 AM
3️⃣ *Weekly* - Weekly report every Monday
4️⃣ *Custom* - Set your own schedule

Also, what's the maximum waiting time you find acceptable? (e.g., 12 weeks)

Reply with frequency choice and max weeks (e.g., "2, 12 weeks")
    """,
    
    'setup_complete': """
✅ *Setup Complete!*

🎉 You're all set! Here's what happens next:

📊 *Monitoring:* I'm now tracking waiting times for your selected specialties in your area
🔔 *Alerts:* You'll receive notifications based on your preferences
📈 *Insights:* Get weekly trends and alternative suggestions

📱 *Quick Commands:*
• *status* - Check current waiting times
• *alerts* - View recent notifications
• *trends* - See waiting time trends
• *help* - Full command list

💬 *Natural Chat:* Ask me anything like "What's the cardiology waiting time?" or "Any quicker options near me?"

Welcome to smarter healthcare monitoring! 🏥
    """,
    
    'status_update': """
📊 *Your Current Status*

🏥 *Monitored Specialties:* {specialties}
📍 *Location:* {postcode}
🔔 *Alert Frequency:* {frequency}
⏱️ *Max Acceptable Wait:* {max_wait}

📈 *Recent Activity:*
• Last alert: {last_alert}
• Total alerts sent: {total_alerts}
• Shortest alternative found: {shortest_alt}

Type *update* to change preferences or *trends* to see detailed analytics.
    """,
    
    'error_message': """
❌ *Oops! Something went wrong*

I couldn't process your request right now. Please try again in a few minutes.

If the problem persists, contact our support team.

💡 *Quick fixes:*
• Check your internet connection
• Try typing *help* for available commands
• Restart with *start* command
    """
}

def get_template(template_name: str, **kwargs) -> str:
    """Get a message template with optional formatting"""
    template = MESSAGE_TEMPLATES.get(template_name, MESSAGE_TEMPLATES['error_message'])
    
    try:
        return template.format(**kwargs)
    except KeyError:
        return template

# Export configuration for use in other modules
__all__ = ['WhatsAppConfig', 'whatsapp_config', 'SETUP_INSTRUCTIONS', 'MESSAGE_TEMPLATES', 'get_template'] 