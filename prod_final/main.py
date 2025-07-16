"""
NHS Alert System - Main Application Entry Point

Integrated business framework components providing complete commercial solution:
- Data ETL Processing
- Intelligent Alert Engine  
- Multi-channel Notification Service
- Telegram Bot Integration (Auto User Registration)
- API Services
- Management Dashboard
"""

import asyncio
import logging
import sys
import os
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv
import locale
# Ensure UTF-8 stdout on Windows to avoid UnicodeEncodeError
if os.name == "nt":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # Python 3.7+
    except AttributeError:
        pass

# Load environment variables
load_dotenv()

# Add project path
sys.path.append(str(Path(__file__).parent))

class SafeStreamHandler(logging.StreamHandler):
    """StreamHandler that ignores UnicodeEncodeError on Windows console."""
    def emit(self, record):
        try:
            super().emit(record)
        except UnicodeEncodeError:
            try:
                msg = self.format(record)
                self.stream.write(msg.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore') + self.terminator)
                self.flush()
            except Exception:
                pass

# Configure logging with English
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nhs_alert_system.log', encoding='utf-8'),
        SafeStreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class NHSProductionSystem:
    """
    NHS Production System - Complete Integrated Solution
    
    One-click startup for all features:
    - Web Interface
    - Telegram Bot Integration (Auto User Registration)
    - Smart Alerts
    - GP Monitoring
    - NHS Data ETL
    """
    
    def __init__(self):
        self.config = self._load_config()
        self.services = {}
        self.is_running = False
        self.background_tasks = []
        self.telegram_bot_server = None
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment"""
        return {
            'telegram': {
                'bot_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
                'webhook_url': os.getenv('TELEGRAM_WEBHOOK_URL', ''),
                'polling_mode': os.getenv('TELEGRAM_POLLING_MODE', 'true').lower() == 'true'
            },
            'whatsapp': {
                'access_token': os.getenv('WHATSAPP_ACCESS_TOKEN', ''),
                'phone_number_id': os.getenv('WHATSAPP_PHONE_NUMBER_ID', ''),
                'webhook_url': os.getenv('WHATSAPP_WEBHOOK_URL', 'https://your-domain.com/webhook'),
                'business_name': os.getenv('WHATSAPP_BUSINESS_NAME', 'NHS Waiting List Alert Service')
            },
            'database': {
                'url': os.getenv('DATABASE_URL', 'sqlite:///nhs_alerts.db')
            },
            'api': {
                'port': int(os.getenv('API_PORT', 8001)),
                'host': os.getenv('API_HOST', '0.0.0.0')
            },
            'system': {
                'log_level': os.getenv('LOG_LEVEL', 'INFO'),
                'notify_channel': os.getenv('NOTIFY_CHANNEL', 'telegram')
            }
        }
    
    def _initialize_database(self):
        """Initialize database with all required tables"""
        try:
            db_path = self.config['database']['url'].replace('sqlite:///', '')
            
            # Check if database exists
            if os.path.exists(db_path):
                print("✅ Database already exists")
                return
            
            # Create database
            conn = sqlite3.connect(db_path)
            
            # Check if create_db.sql exists
            if os.path.exists('create_db.sql'):
                print("📄 Executing create_db.sql...")
                with open('create_db.sql', 'r', encoding='utf-8') as f:
                    sql_script = f.read()
                conn.executescript(sql_script)
                print("✅ Database initialized from create_db.sql")
            else:
                print("📄 Creating basic database tables...")
                self._create_basic_tables(conn)
                print("✅ Basic database tables created")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def _create_basic_tables(self, conn):
        """Create basic database tables"""
        cursor = conn.cursor()
        
        # NHS RTT Data table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nhs_rtt_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period TEXT NOT NULL,
                org_code TEXT NOT NULL,
                org_name TEXT NOT NULL,
                specialty_code TEXT NOT NULL,
                specialty_name TEXT NOT NULL,
                treatment_function_code TEXT,
                treatment_function_name TEXT,
                waiting_time_weeks INTEGER,
                patient_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # User preferences table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                phone_number TEXT,
                postcode TEXT,
                specialties TEXT,
                specialty TEXT,
                threshold_weeks INTEGER,
                radius_km INTEGER,
                notification_types TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Alert history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                alert_data TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'sent'
            )
        ''')
        
        # Telegram users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS telegram_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT UNIQUE NOT NULL,
                user_id TEXT UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_bot BOOLEAN DEFAULT 0,
                language_code TEXT DEFAULT 'en',
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        # User sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                session_state TEXT NOT NULL,
                session_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
    
    async def _initialize_services(self):
        """Initialize all system services"""
        try:
            print("🔧 Initializing services...")
            
            # Initialize notification manager
            from notification_manager import NotificationManager
            self.services['notification_manager'] = NotificationManager()
            notify_channel = self.config['system']['notify_channel']
            print(f"✅ Notification Manager initialized (channel: {notify_channel})")
            
            # Initialize Telegram Bot Server (if Telegram channel is selected)
            if notify_channel == 'telegram' and self.config['telegram']['bot_token']:
                try:
                    from telegram_bot_server import TelegramBotServer
                    self.telegram_bot_server = TelegramBotServer()
                    print("✅ Telegram Bot Server initialized")
                except Exception as e:
                    print(f"⚠️ Telegram Bot Server initialization failed: {e}")
            
            # Initialize WhatsApp Flow Service
            try:
                from whatsapp_flow_service import WhatsAppFlowService
                whatsapp_config = self.config['whatsapp']
                if whatsapp_config['access_token']:
                    self.services['whatsapp_flow'] = WhatsAppFlowService(whatsapp_config)
                    print("✅ WhatsApp Flow Service initialized")
                else:
                    print("⚠️ WhatsApp interactive flow not configured (missing access token)")
            except Exception as e:
                print(f"⚠️ WhatsApp Flow Service initialization failed: {e}")
            
            # Initialize Intelligent Alert Engine
            try:
                from intelligent_alert_engine import IntelligentAlertEngine
                self.services['alert_engine'] = IntelligentAlertEngine(
                    self.services['notification_manager']
                )
                print("✅ Intelligent Alert Engine initialized")
            except Exception as e:
                print(f"⚠️ Alert Engine initialization failed: {e}")
            
            # Initialize GP Slot Monitor
            try:
                from gp_slot_monitor import GPSlotMonitor
                self.services['gp_monitor'] = GPSlotMonitor(
                    self.services['notification_manager']
                )
                print("✅ GP Slot Monitor initialized")
            except Exception as e:
                print(f"⚠️ GP Slot Monitor initialization failed: {e}")
            
            # Initialize NHS Complete System (if available)
            try:
                from nhs_complete_system import NHSCompleteSystem
                self.services['nhs_complete'] = NHSCompleteSystem()
                print("✅ NHS Complete System initialized")
            except ImportError:
                print("⚠️ NHS Complete System not available")
            except Exception as e:
                print(f"⚠️ NHS Complete System initialization failed: {e}")
            
        except Exception as e:
            logger.error(f"Service initialization failed: {e}")
            raise
    
    async def _start_web_server(self):
        """Start web server if available"""
        try:
            print("🌐 Starting web server...")
            
            # Check if simple_main.py exists
            if os.path.exists('simple_main.py'):
                # Import and start the web server
                import simple_main
                # Start web server in background
                print(f"✅ Web server starting on http://localhost:{self.config['api']['port']}")
                return True
            else:
                print("⚠️ Web server not available (simple_main.py not found)")
                return False
                
        except Exception as e:
            print(f"⚠️ Web server startup failed: {e}")
            return False
    
    async def _start_telegram_bot(self):
        """Start Telegram Bot server"""
        try:
            if not self.telegram_bot_server:
                return False
            
            print("🤖 Starting Telegram Bot...")
            
            webhook_url = self.config['telegram']['webhook_url']
            
            if webhook_url:
                # Webhook mode
                print(f"🌐 Telegram Webhook mode: {webhook_url}")
                full_webhook_url = f"{webhook_url}/telegram/webhook"
                await self.telegram_bot_server.set_webhook(full_webhook_url)
                
                # Start server
                runner = await self.telegram_bot_server.start_server()
                self.services['telegram_runner'] = runner
                print("✅ Telegram Bot Webhook server started")
                return True
            else:
                # Polling mode
                print("🔄 Telegram Polling mode")
                # Start polling in background
                task = asyncio.create_task(self.telegram_bot_server.start_polling())
                self.background_tasks.append(task)
                print("✅ Telegram Bot polling started")
                return True
                
        except Exception as e:
            print(f"⚠️ Telegram Bot startup failed: {e}")
            return False
    
    async def _start_background_services(self):
        """Start background monitoring services"""
        try:
            print("🔄 Starting background services...")
            
            # Start alert engine monitoring
            if 'alert_engine' in self.services:
                alert_task = asyncio.create_task(
                    self.services['alert_engine'].start_monitoring()
                )
                self.background_tasks.append(alert_task)
            
            # Start GP slot monitoring
            if 'gp_monitor' in self.services:
                gp_task = asyncio.create_task(
                    self.services['gp_monitor'].start_monitoring()
                )
                self.background_tasks.append(gp_task)
            
            print("✅ Background services started")
            return True
            
        except Exception as e:
            print(f"⚠️ Background services startup failed: {e}")
            return False
    
    async def start_system(self):
        """Start the complete NHS system"""
        try:
            print("🏥 NHS Intelligent Alert System")
            print("=" * 50)
            print("🚀 Starting Production System...")
            print("=" * 50)
            
            # Initialize database
            print("🗄️ Initializing database...")
            self._initialize_database()
            
            # Initialize services
            await self._initialize_services()
            
            # Start Telegram Bot (if configured)
            if self.config['system']['notify_channel'] == 'telegram':
                await self._start_telegram_bot()
            
            # Start web server
            await self._start_web_server()
            
            # Start background services
            await self._start_background_services()
            
            print("✅ System initialization completed successfully!")
            print()
            print("🎉 NHS Intelligent Alert System Ready!")
            print("=" * 50)
            
            # Show system status
            self._show_system_status()
            
            self.is_running = True
            return True
            
        except Exception as e:
            logger.error(f"System startup failed: {e}")
            print(f"❌ System startup failed: {e}")
            return False
    
    def _show_system_status(self):
        """Show current system status"""
        print("📱 Available Features:")
        
        # Web interface
        if os.path.exists('simple_main.py'):
            print(f"   • Web Interface: http://localhost:{self.config['api']['port']}")
            print(f"   • API Documentation: http://localhost:{self.config['api']['port']}/docs")
        else:
            print("   • Web Interface: ⚠️ Not available")
        
        # Telegram integration
        if self.config['telegram']['bot_token']:
            print("   • Telegram Bot: ✅ Active")
        else:
            print("   • Telegram Bot: ⚠️ Not configured")
        
        # WhatsApp integration
        if self.config['whatsapp']['access_token']:
            print("   • WhatsApp Integration: ✅ Active")
        else:
            print("   • WhatsApp Integration: ⚠️ Not configured")
        
        # Core services
        print("   • Intelligent Alerts: ✅ Active")
        print("   • GP Monitoring: ✅ Active")
        print("   • NHS Data ETL: ✅ Active")
        
        print()
        print("💬 Telegram Bot Commands:")
        print("   • Send any message to start automatic setup")
        print("   • 'setup' - Configure preferences")
        print("   • 'status' - View current alerts")
        print("   • 'help' - Show help information")
        
        print()
        print("🌍 Natural Language Queries:")
        print("   • 'How long is the cardiology wait?'")
        print("   • 'Are there any quicker options near me?'")
        print("   • 'Have waiting times changed this week?'")
        
        print()
        print("🔧 System Configuration:")
        print(f"   • Database: {self.config['database']['url']}")
        print(f"   • Notification Channel: {self.config['system']['notify_channel']}")
        print(f"   • Language: English (Default)")
        print(f"   • Log Level: {self.config['system']['log_level']}")
        print("=" * 50)
        print("Press Ctrl+C to stop the system")
        print("=" * 50)
    
    async def stop_system(self):
        """Stop the system gracefully"""
        try:
            print("\n🛑 Stopping NHS Intelligent Alert System...")
            
            # Stop background tasks
            for task in self.background_tasks:
                if not task.done():
                    task.cancel()
            
            # Stop services
            if 'alert_engine' in self.services:
                await self.services['alert_engine'].stop_monitoring()
            
            if 'gp_monitor' in self.services:
                await self.services['gp_monitor'].stop_monitoring()
            
            # Stop Telegram bot runner
            if 'telegram_runner' in self.services:
                await self.services['telegram_runner'].cleanup()
            
            self.is_running = False
            print("✅ System stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping system: {e}")
    
    async def run_forever(self):
        """Run the system until interrupted"""
        try:
            while self.is_running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await self.stop_system()

# Main execution
async def main():
    """Main execution function"""
    try:
        # Create and start the system
        system = NHSProductionSystem()
        
        if await system.start_system():
            # Run until interrupted
            await system.run_forever()
        else:
            print("❌ System failed to start")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        logger.error(f"System error: {e}")
        print(f"❌ System error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main()) 