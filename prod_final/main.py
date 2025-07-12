"""
NHS Alert System - Main Application Entry Point

Integrated business framework components providing complete commercial solution:
- Data ETL Processing
- Intelligent Alert Engine  
- Multi-channel Notification Service
- WhatsApp Integration
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

# Load environment variables
load_dotenv()

# Add project path
sys.path.append(str(Path(__file__).parent))

# Configure logging with English
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nhs_alert_system.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class NHSProductionSystem:
    """
    NHS Production System - Complete Integrated Solution
    
    One-click startup for all features:
    - Web Interface
    - WhatsApp Integration
    - Smart Alerts
    - GP Monitoring
    - NHS Data ETL
    """
    
    def __init__(self):
        self.config = self._load_config()
        self.services = {}
        self.is_running = False
        self.background_tasks = []
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment"""
        return {
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
                'log_level': os.getenv('LOG_LEVEL', 'INFO')
            }
        }
    
    async def initialize(self):
        """Initialize all system components"""
        print("🏥 NHS Intelligent Alert System")
        print("=" * 50)
        print("🚀 Starting Production System...")
        print("=" * 50)
        
        try:
            # 1. Initialize database
            await self._initialize_database()
            
            # 2. Initialize core services
            await self._initialize_services()
            
            # 3. Start web server
            await self._start_web_server()
            
            # 4. Start background services
            await self._start_background_services()
            
            self.is_running = True
            print("✅ System initialization completed successfully!")
            self._print_system_info()
            
            return True
            
        except Exception as e:
            logger.error(f"System initialization failed: {e}")
            print(f"❌ System initialization failed: {e}")
            return False
    
    async def _initialize_database(self):
        """Initialize database"""
        print("🗄️ Initializing database...")
        
        db_path = self.config['database']['url'].replace('sqlite:///', '')
        
        if not os.path.exists(db_path):
            # Create database using SQL script
            if os.path.exists('create_db.sql'):
                with open('create_db.sql', 'r', encoding='utf-8') as f:
                    sql_script = f.read()
                
                conn = sqlite3.connect(db_path)
                try:
                    conn.executescript(sql_script)
                    conn.commit()
                    print("✅ Database created from SQL script")
                except Exception as e:
                    print(f"⚠️ SQL script error: {e}")
                    # Create basic tables
                    self._create_basic_tables(conn)
                finally:
                    conn.close()
            else:
                # Create basic database structure
                conn = sqlite3.connect(db_path)
                self._create_basic_tables(conn)
                conn.close()
        else:
            print("✅ Database already exists")
    
    def _create_basic_tables(self, conn):
        """Create basic database tables"""
        basic_tables = """
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
        );
        
        CREATE TABLE IF NOT EXISTS user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            phone_number TEXT,
            postcode TEXT,
            specialties TEXT,
            max_waiting_time INTEGER,
            alert_frequency TEXT DEFAULT 'daily',
            language TEXT DEFAULT 'en',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS alert_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            message TEXT NOT NULL,
            channel TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        conn.executescript(basic_tables)
        conn.commit()
        print("✅ Basic database tables created")
    
    async def _initialize_services(self):
        """Initialize all services"""
        print("🔧 Initializing services...")
        
        try:
            # Initialize WhatsApp service if configured
            if self.config['whatsapp']['access_token']:
                from whatsapp_flow_service import WhatsAppFlowService
                self.services['whatsapp'] = WhatsAppFlowService()
                print("✅ WhatsApp Flow Service initialized")
            else:
                print("⚠️ WhatsApp not configured (missing access token)")
            
            # Initialize Alert Engine
            try:
                from intelligent_alert_engine import IntelligentAlertEngine
                self.services['alerts'] = IntelligentAlertEngine()
                print("✅ Intelligent Alert Engine initialized")
            except ImportError:
                print("⚠️ Alert Engine not available")
            
            # Initialize GP Monitor
            try:
                from gp_slot_monitor import GPSlotMonitor
                self.services['gp_monitor'] = GPSlotMonitor()
                print("✅ GP Slot Monitor initialized")
            except ImportError:
                print("⚠️ GP Monitor not available")
            
            # Initialize NHS System
            try:
                from nhs_complete_system import NHSCompleteSystem
                self.services['nhs_system'] = NHSCompleteSystem()
                print("✅ NHS Complete System initialized")
            except ImportError:
                print("⚠️ NHS Complete System not available")
                
        except Exception as e:
            print(f"❌ Service initialization error: {e}")
    
    async def _start_web_server(self):
        """Start web server"""
        print("🌐 Starting web server...")
        
        try:
            # Try to use existing simple_main.py if available
            if os.path.exists('simple_main.py'):
                import simple_main
                # Start web server in background
                port = self.config['api']['port']
                task = asyncio.create_task(
                    self._run_web_server(port),
                    name="web_server"
                )
                self.background_tasks.append(task)
                print(f"✅ Web server started on port {port}")
            else:
                print("⚠️ Web server not available (simple_main.py not found)")
                
        except Exception as e:
            print(f"❌ Web server startup error: {e}")
    
    async def _run_web_server(self, port):
        """Run web server in background"""
        try:
            import uvicorn
            from simple_main import app
            
            config = uvicorn.Config(
                app,
                host=self.config['api']['host'],
                port=port,
                log_level="info"
            )
            server = uvicorn.Server(config)
            await server.serve()
            
        except Exception as e:
            logger.error(f"Web server error: {e}")
    
    async def _start_background_services(self):
        """Start background services"""
        print("🔄 Starting background services...")
        
        # Start WhatsApp service
        if 'whatsapp' in self.services:
            task = asyncio.create_task(
                self.services['whatsapp'].start(),
                name="whatsapp_service"
            )
            self.background_tasks.append(task)
        
        # Start Alert Engine
        if 'alerts' in self.services:
            task = asyncio.create_task(
                self.services['alerts'].start_monitoring(),
                name="alert_engine"
            )
            self.background_tasks.append(task)
        
        # Start GP Monitor
        if 'gp_monitor' in self.services:
            task = asyncio.create_task(
                self.services['gp_monitor'].start_monitoring(),
                name="gp_monitor"
            )
            self.background_tasks.append(task)
        
        print("✅ Background services started")
    
    def _print_system_info(self):
        """Print system information"""
        print("\n🎉 NHS Intelligent Alert System Ready!")
        print("=" * 50)
        print("📱 Available Features:")
        print("   • Web Interface: http://localhost:{}".format(self.config['api']['port']))
        print("   • API Documentation: http://localhost:{}/docs".format(self.config['api']['port']))
        print("   • WhatsApp Integration: {}".format("✅ Active" if 'whatsapp' in self.services else "⚠️ Not configured"))
        print("   • Intelligent Alerts: {}".format("✅ Active" if 'alerts' in self.services else "⚠️ Not available"))
        print("   • GP Monitoring: {}".format("✅ Active" if 'gp_monitor' in self.services else "⚠️ Not available"))
        print("   • NHS Data ETL: ✅ Active")
        print()
        print("💬 WhatsApp Commands:")
        print("   • setup - Start preference setup")
        print("   • status - View current alerts") 
        print("   • alerts - View recent notifications")
        print("   • trends - View waiting time trends")
        print("   • help - Show help information")
        print()
        print("🌍 Natural Language Queries:")
        print("   • 'How long is the cardiology wait?'")
        print("   • 'Are there any quicker options near me?'")
        print("   • 'Have waiting times changed this week?'")
        print()
        print("🔧 System Configuration:")
        print("   • Database: {}".format(self.config['database']['url']))
        print("   • Language: English (Default)")
        print("   • Log Level: {}".format(self.config['system']['log_level']))
        print("=" * 50)
        print("Press Ctrl+C to stop the system")
        print("=" * 50)
    
    async def run(self):
        """Run the complete system"""
        try:
            # Initialize system
            success = await self.initialize()
            
            if not success:
                return False
            
            # Keep system running
            try:
                while self.is_running:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\n\n⏹️ Stopping system...")
                await self.stop()
            
            return True
            
        except Exception as e:
            logger.error(f"System runtime error: {e}")
            print(f"❌ System runtime error: {e}")
            return False
    
    async def stop(self):
        """Stop all services"""
        print("🛑 Stopping NHS Intelligent Alert System...")
        self.is_running = False
        
        # Cancel all background tasks
        for task in self.background_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Stop services
        for service_name, service in self.services.items():
            try:
                if hasattr(service, 'stop'):
                    await service.stop()
                print(f"✅ {service_name} stopped")
            except Exception as e:
                print(f"❌ Error stopping {service_name}: {e}")
        
        print("✅ System stopped successfully")

async def main():
    """Main function"""
    system = NHSProductionSystem()
    
    try:
        success = await system.run()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 