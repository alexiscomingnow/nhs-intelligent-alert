#!/usr/bin/env python3
"""
Telegram Bot Server - NHS Alert System
优化版自动化Telegram Bot服务器，采用编号命令系统
"""

import os
import json
import logging
import asyncio
import sqlite3
import aiohttp
from typing import Dict, Any, Optional, List
from datetime import datetime
from aiohttp import web, ClientSession, ClientTimeout
from telegram_driver import TelegramDriver
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TelegramBotServer:
    """
    优化版Telegram Bot服务器 - 简洁直观的用户交互系统
    
    特点：
    1. 编号命令系统，简化用户操作
    2. 智能欢迎消息，突出价值主张
    3. 自动获取和存储Chat ID
    4. 完整的用户偏好设置流程
    """
    
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set.")
        
        self.driver = TelegramDriver()
        self.db_path = os.getenv('DATABASE_URL', 'sqlite:///nhs_alerts.db').replace('sqlite:///', '')
        
        # Bot API URLs
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.webhook_url = f"{self.base_url}/setWebhook"
        self.get_updates_url = f"{self.base_url}/getUpdates"
        
        # Server config
        self.host = os.getenv('API_HOST', '0.0.0.0')
        self.port = int(os.getenv('API_PORT', 8001))
        self.webhook_path = "/telegram/webhook"
        
        # Initialize database
        self._init_database()
        
        logger.info(f"Telegram Bot Server initialized - Token: {self.token[:10]}...")

    def _init_database(self):
        """初始化数据库表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建Telegram用户表
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
            
            # 创建用户会话表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    session_state TEXT NOT NULL,
                    session_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (chat_id) REFERENCES telegram_users (chat_id)
                )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization error: {e}")

    # ------------------------------------------------------------------
    # Webhook处理
    # ------------------------------------------------------------------
    async def webhook_handler(self, request):
        """处理Telegram webhook请求"""
        try:
            data = await request.json()
            
            if 'message' in data:
                await self._process_message(data['message'])
            elif 'callback_query' in data:
                await self._process_callback_query(data['callback_query'])
            
            return web.Response(status=200)
            
        except Exception as e:
            logger.error(f"Webhook handler error: {e}")
            return web.Response(status=500)

    async def _process_message(self, message: Dict[str, Any]):
        """处理消息"""
        try:
            chat_id = str(message['chat']['id'])
            user_info = message['from']
            
            # 自动注册用户
            await self._auto_register_user(chat_id, user_info)
            
            # 处理文本消息
            if 'text' in message:
                text = message['text']
                user_name = user_info.get('first_name', '')
                
                # 使用优化的driver处理消息
                success = self.driver.process_user_message(chat_id, text, user_name)
                
                if not success:
                    await self._send_error_message(chat_id)
            
            # 更新用户活动时间
            await self._update_user_activity(chat_id)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def _process_callback_query(self, callback_query: Dict[str, Any]):
        """处理回调查询"""
        try:
            chat_id = str(callback_query['message']['chat']['id'])
            data = callback_query['data']
            
            # 处理回调数据
            await self._handle_callback_data(chat_id, data)
            
        except Exception as e:
            logger.error(f"Error processing callback query: {e}")

    async def _auto_register_user(self, chat_id: str, user_info: Dict[str, Any]):
        """自动注册用户"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查用户是否已存在
            cursor.execute("SELECT id FROM telegram_users WHERE chat_id = ?", (chat_id,))
            existing_user = cursor.fetchone()
            
            if not existing_user:
                # 注册新用户
                cursor.execute('''
                    INSERT INTO telegram_users 
                    (chat_id, user_id, username, first_name, last_name, is_bot, language_code)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    chat_id,
                    str(user_info.get('id', '')),
                    user_info.get('username', ''),
                    user_info.get('first_name', ''),
                    user_info.get('last_name', ''),
                    user_info.get('is_bot', False),
                    user_info.get('language_code', 'en')
                ))
                
                conn.commit()
                logger.info(f"New user registered: {chat_id}")
                
                # 发送欢迎消息
                first_name = user_info.get('first_name', '')
                self.driver._send_welcome_message(chat_id, first_name)
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error auto-registering user: {e}")

    async def _handle_callback_data(self, chat_id: str, data: str):
        """处理回调数据"""
        try:
            # 解析回调数据并处理
            if data.startswith('menu_'):
                option = data.replace('menu_', '')
                self.driver._handle_numbered_command(chat_id, int(option))
            
        except Exception as e:
            logger.error(f"Error handling callback data: {e}")

    async def _update_user_activity(self, chat_id: str):
        """更新用户活动时间"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE telegram_users 
                SET last_activity = CURRENT_TIMESTAMP 
                WHERE chat_id = ?
            ''', (chat_id,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating user activity: {e}")

    async def _send_message(self, chat_id: str, text: str, parse_mode: str = None):
        """发送消息"""
        try:
            success = self.driver._send_telegram_message(chat_id, text, parse_mode)
            if not success:
                logger.error(f"Failed to send message to {chat_id}")
        except Exception as e:
            logger.error(f"Error sending message: {e}")

    async def _send_error_message(self, chat_id: str):
        """发送错误消息"""
        error_text = """
❌ *出现了一些问题*

请稍后再试，或者：

*1* - 返回主菜单
*help* - 查看帮助信息

如果问题持续，请联系技术支持。
        """
        
        await self._send_message(chat_id, error_text, parse_mode='Markdown')

    # ------------------------------------------------------------------
    # 服务器启动和管理
    # ------------------------------------------------------------------
    async def start_server(self):
        """启动服务器"""
        app = web.Application()
        app.router.add_post(self.webhook_path, self.webhook_handler)
        
        # 健康检查端点
        app.router.add_get('/health', self._health_check)
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        logger.info(f"Telegram Bot Server started on {self.host}:{self.port}")
        
        # 设置webhook
        webhook_url = f"https://your-domain.com{self.webhook_path}"
        await self.set_webhook(webhook_url)

    async def _health_check(self, request):
        """健康检查"""
        return web.json_response({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service': 'telegram-bot-server'
        })

    async def set_webhook(self, webhook_url: str):
        """设置webhook"""
        try:
            async with ClientSession() as session:
                data = {'url': webhook_url}
                async with session.post(self.webhook_url, json=data) as response:
                    if response.status == 200:
                        logger.info(f"Webhook set successfully: {webhook_url}")
                    else:
                        logger.error(f"Failed to set webhook: {response.status}")
        except Exception as e:
            logger.error(f"Error setting webhook: {e}")

    async def start_polling(self):
        """启动轮询模式 - 优化版本，增加重试和错误处理"""
        logger.info("Starting polling mode...")
        offset = 0
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        while True:
            try:
                # 创建会话时设置超时
                timeout = aiohttp.ClientTimeout(total=60, connect=30)
                async with ClientSession(timeout=timeout) as session:
                    params = {
                        'offset': offset,
                        'limit': 100,
                        'timeout': 30
                    }
                    
                    async with session.get(self.get_updates_url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            if data.get('ok'):
                                updates = data.get('result', [])
                                consecutive_errors = 0  # 重置错误计数
                                
                                for update in updates:
                                    offset = update['update_id'] + 1
                                    
                                    try:
                                        if 'message' in update:
                                            await self._process_message(update['message'])
                                        elif 'callback_query' in update:
                                            await self._process_callback_query(update['callback_query'])
                                    except Exception as e:
                                        logger.error(f"Error processing update {update.get('update_id', 'unknown')}: {e}")
                                        # 继续处理其他更新，不中断整个循环
                                        continue
                            else:
                                logger.error(f"Telegram API error: {data}")
                                consecutive_errors += 1
                        else:
                            logger.error(f"HTTP error: {response.status}")
                            consecutive_errors += 1
                            
            except asyncio.TimeoutError:
                logger.error("Polling timeout - retrying...")
                consecutive_errors += 1
            except aiohttp.ClientError as e:
                logger.error(f"Client error: {e}")
                consecutive_errors += 1
            except Exception as e:
                logger.error(f"Unexpected polling error: {e}")
                consecutive_errors += 1
            
            # 如果连续错误过多，增加等待时间
            if consecutive_errors > 0:
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"Too many consecutive errors ({consecutive_errors}), sleeping for 60 seconds...")
                    await asyncio.sleep(60)
                    consecutive_errors = 0  # 重置计数
                else:
                    sleep_time = min(5 * consecutive_errors, 30)  # 最多等待30秒
                    logger.info(f"Sleeping for {sleep_time} seconds after error...")
                    await asyncio.sleep(sleep_time)
            
            # 正常情况下的短暂延迟
            await asyncio.sleep(0.1)

async def main():
    """主函数"""
    try:
        server = TelegramBotServer()
        
        # 根据环境变量决定使用webhook还是polling
        use_webhook = os.getenv('USE_WEBHOOK', 'false').lower() == 'true'
        
        if use_webhook:
            await server.start_server()
            # 保持服务器运行
            while True:
                await asyncio.sleep(1)
        else:
            await server.start_polling()
            
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 