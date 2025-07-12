#!/usr/bin/env python3
"""
GP Slot Monitor - NHS Alert System
GP预约空位监控服务，集成NHS GP Connect API和实时提醒
"""

import json
import logging
import sqlite3
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import asyncio
import aiohttp
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class GPSlot:
    """GP预约空位数据"""
    slot_id: str
    practice_code: str
    practice_name: str
    doctor_name: str
    specialty: str
    appointment_datetime: datetime
    duration_minutes: int
    appointment_type: str  # routine, urgent, emergency
    availability_status: str  # available, booked, cancelled
    booking_url: Optional[str] = None
    created_at: datetime = None

@dataclass
class SlotAlert:
    """空位提醒"""
    alert_id: str
    user_id: str
    slot_id: str
    practice_code: str
    alert_type: str  # new_slot, slot_change, urgent_available
    priority: int
    created_at: datetime

class GPSlotMonitor:
    """GP预约空位监控器"""
    
    def __init__(self, config_manager, whatsapp_service=None):
        self.config = config_manager
        self.whatsapp_service = whatsapp_service
        self.db_path = self.config.get('database_url', 'sqlite:///nhs_alerts.db').replace('sqlite:///', '')
        
        # NHS API配置
        self.nhs_api_key = self.config.get('nhs_api_key', 'demo_key')
        self.gp_connect_base_url = "https://orange.testlab.nhs.uk/B82617/STU3/1"
        self.appointment_api_url = "https://api.nhs.uk/service-search"
        
        # 监控配置
        self.monitor_interval_minutes = self.config.get('slot_monitor_interval', 5)
        self.max_slots_per_check = 50
        self.is_monitoring = False
        
        self._initialize_database()
    
    def _initialize_database(self):
        """初始化数据库表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # GP实践信息表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS gp_practices (
                practice_code TEXT PRIMARY KEY,
                practice_name TEXT NOT NULL,
                address TEXT,
                postcode TEXT,
                phone_number TEXT,
                website_url TEXT,
                accepts_new_patients BOOLEAN DEFAULT 0,
                online_booking_available BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # GP预约空位表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS gp_slots (
                slot_id TEXT PRIMARY KEY,
                practice_code TEXT NOT NULL,
                doctor_name TEXT,
                specialty TEXT,
                appointment_datetime TIMESTAMP NOT NULL,
                duration_minutes INTEGER DEFAULT 15,
                appointment_type TEXT DEFAULT 'routine',
                availability_status TEXT DEFAULT 'available',
                booking_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (practice_code) REFERENCES gp_practices (practice_code)
            )
            ''')
            
            # 空位提醒表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS slot_alerts (
                alert_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                slot_id TEXT NOT NULL,
                practice_code TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                priority INTEGER DEFAULT 3,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP NULL,
                FOREIGN KEY (slot_id) REFERENCES gp_slots (slot_id)
            )
            ''')
            
            # 用户GP偏好表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_gp_preferences (
                user_id TEXT NOT NULL,
                practice_code TEXT NOT NULL,
                specialty_preference TEXT,
                appointment_type_preference TEXT DEFAULT 'routine',
                preferred_days TEXT,  -- JSON array of preferred days
                preferred_times TEXT, -- JSON array of preferred time slots
                max_distance_km INTEGER DEFAULT 10,
                enable_urgent_alerts BOOLEAN DEFAULT 1,
                enable_routine_alerts BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, practice_code),
                FOREIGN KEY (practice_code) REFERENCES gp_practices (practice_code)
            )
            ''')
            
            # 监控日志表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS slot_monitor_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                check_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                practices_checked INTEGER DEFAULT 0,
                slots_found INTEGER DEFAULT 0,
                alerts_generated INTEGER DEFAULT 0,
                api_calls_made INTEGER DEFAULT 0,
                errors_count INTEGER DEFAULT 0,
                duration_seconds REAL DEFAULT 0.0
            )
            ''')
            
            conn.commit()
            
            # 插入示例GP实践数据
            self._insert_sample_practices()
            
            conn.close()
            logger.info("GP空位监控数据库初始化完成")
            
        except Exception as e:
            logger.error(f"初始化GP监控数据库失败: {e}")
            raise
    
    def _insert_sample_practices(self):
        """插入示例GP实践数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            sample_practices = [
                {
                    'practice_code': 'A12345',
                    'practice_name': 'Central London GP Practice',
                    'address': '123 High Street, London',
                    'postcode': 'W1A 1AA',
                    'phone_number': '020 7123 4567',
                    'website_url': 'https://centrallondongp.nhs.uk',
                    'accepts_new_patients': True,
                    'online_booking_available': True
                },
                {
                    'practice_code': 'B67890',
                    'practice_name': 'Tower Hamlets Health Centre',
                    'address': '456 Commercial Road, London',
                    'postcode': 'E1 1AB',
                    'phone_number': '020 7987 6543',
                    'website_url': 'https://towerhamletshealth.nhs.uk',
                    'accepts_new_patients': True,
                    'online_booking_available': False
                },
                {
                    'practice_code': 'C11111',
                    'practice_name': 'Westminster Medical Centre',
                    'address': '789 Victoria Street, London',
                    'postcode': 'SW1V 1QT',
                    'phone_number': '020 7456 7890',
                    'website_url': 'https://westminstermedical.nhs.uk',
                    'accepts_new_patients': False,
                    'online_booking_available': True
                }
            ]
            
            for practice in sample_practices:
                cursor.execute('''
                INSERT OR IGNORE INTO gp_practices 
                (practice_code, practice_name, address, postcode, phone_number, website_url, accepts_new_patients, online_booking_available)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    practice['practice_code'],
                    practice['practice_name'],
                    practice['address'],
                    practice['postcode'],
                    practice['phone_number'],
                    practice['website_url'],
                    practice['accepts_new_patients'],
                    practice['online_booking_available']
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"插入示例GP实践数据失败: {e}")
    
    async def start_monitoring(self):
        """开始监控GP空位"""
        if self.is_monitoring:
            logger.warning("GP空位监控已在运行")
            return
        
        self.is_monitoring = True
        logger.info(f"开始GP空位监控，检查间隔: {self.monitor_interval_minutes}分钟")
        
        try:
            while self.is_monitoring:
                start_time = datetime.now()
                
                # 执行一次监控检查
                stats = await self._run_monitoring_cycle()
                
                # 记录监控日志
                duration = (datetime.now() - start_time).total_seconds()
                self._log_monitoring_cycle(stats, duration)
                
                # 等待下次检查
                await asyncio.sleep(self.monitor_interval_minutes * 60)
                
        except Exception as e:
            logger.error(f"GP空位监控异常: {e}")
        finally:
            self.is_monitoring = False
            logger.info("GP空位监控已停止")
    
    def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        logger.info("正在停止GP空位监控...")
    
    async def _run_monitoring_cycle(self) -> Dict:
        """运行一次监控周期"""
        stats = {
            'practices_checked': 0,
            'slots_found': 0,
            'alerts_generated': 0,
            'api_calls_made': 0,
            'errors_count': 0
        }
        
        try:
            # 获取需要监控的GP实践
            practices = self._get_monitored_practices()
            logger.info(f"开始检查 {len(practices)} 个GP实践")
            
            # 并发检查多个实践
            semaphore = asyncio.Semaphore(5)  # 限制并发数
            tasks = []
            
            for practice in practices:
                task = self._check_practice_slots(practice, semaphore, stats)
                tasks.append(task)
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
            logger.info(f"监控周期完成: {stats}")
            
        except Exception as e:
            logger.error(f"监控周期执行失败: {e}")
            stats['errors_count'] += 1
        
        return stats
    
    def _get_monitored_practices(self) -> List[Dict]:
        """获取需要监控的GP实践"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取有用户关注的GP实践
            cursor.execute('''
            SELECT DISTINCT p.practice_code, p.practice_name, p.postcode, p.online_booking_available
            FROM gp_practices p
            INNER JOIN user_gp_preferences ugp ON p.practice_code = ugp.practice_code
            WHERE p.accepts_new_patients = 1 OR ugp.user_id IS NOT NULL
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            practices = []
            for row in rows:
                practices.append({
                    'practice_code': row[0],
                    'practice_name': row[1],
                    'postcode': row[2],
                    'online_booking_available': bool(row[3])
                })
            
            # 如果没有用户关注的实践，返回所有支持在线预约的实践
            if not practices:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                SELECT practice_code, practice_name, postcode, online_booking_available
                FROM gp_practices
                WHERE online_booking_available = 1
                LIMIT 10
                ''')
                
                rows = cursor.fetchall()
                conn.close()
                
                for row in rows:
                    practices.append({
                        'practice_code': row[0],
                        'practice_name': row[1],
                        'postcode': row[2],
                        'online_booking_available': bool(row[3])
                    })
            
            return practices
            
        except Exception as e:
            logger.error(f"获取监控实践失败: {e}")
            return []
    
    async def _check_practice_slots(self, practice: Dict, semaphore: asyncio.Semaphore, stats: Dict):
        """检查单个实践的空位"""
        async with semaphore:
            try:
                practice_code = practice['practice_code']
                logger.debug(f"检查实践 {practice_code} 的空位")
                
                # 获取空位数据
                slots = await self._fetch_practice_slots(practice_code)
                stats['api_calls_made'] += 1
                stats['practices_checked'] += 1
                
                if slots:
                    # 保存空位数据
                    saved_slots = self._save_slots(slots)
                    stats['slots_found'] += len(saved_slots)
                    
                    # 生成提醒
                    alerts = await self._generate_slot_alerts(practice_code, saved_slots)
                    stats['alerts_generated'] += len(alerts)
                    
                    logger.debug(f"实践 {practice_code}: 找到 {len(slots)} 个空位, 生成 {len(alerts)} 个提醒")
                
            except Exception as e:
                logger.error(f"检查实践 {practice['practice_code']} 空位失败: {e}")
                stats['errors_count'] += 1
    
    async def _fetch_practice_slots(self, practice_code: str) -> List[GPSlot]:
        """从NHS API获取实践空位"""
        try:
            # 在生产环境中，这里会调用真实的NHS GP Connect API
            # 当前为模拟实现
            if self.config.get('debug', True):
                return self._generate_mock_slots(practice_code)
            
            # 真实API调用
            headers = {
                'Authorization': f'Bearer {self.nhs_api_key}',
                'Accept': 'application/fhir+json',
                'Content-Type': 'application/fhir+json'
            }
            
            # GP Connect Slot查询
            url = f"{self.gp_connect_base_url}/Slot"
            params = {
                'schedule.actor:Organization': practice_code,
                'start': datetime.now().isoformat(),
                'end': (datetime.now() + timedelta(days=14)).isoformat(),
                'status': 'free',
                '_count': self.max_slots_per_check
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_fhir_slots(data, practice_code)
                    else:
                        logger.error(f"NHS API调用失败: {response.status}")
                        return []
            
        except Exception as e:
            logger.error(f"获取实践 {practice_code} 空位失败: {e}")
            return []
    
    def _generate_mock_slots(self, practice_code: str) -> List[GPSlot]:
        """生成模拟空位数据（开发环境使用）"""
        import random
        
        slots = []
        now = datetime.now()
        
        # 生成未来7天的随机空位
        for day in range(1, 8):
            if random.random() < 0.7:  # 70%概率有空位
                slot_date = now + timedelta(days=day)
                
                # 每天生成1-3个空位
                for _ in range(random.randint(1, 3)):
                    hour = random.choice([9, 10, 11, 14, 15, 16])
                    minute = random.choice([0, 15, 30, 45])
                    
                    slot_datetime = slot_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    slot = GPSlot(
                        slot_id=f"{practice_code}_{slot_datetime.strftime('%Y%m%d_%H%M')}",
                        practice_code=practice_code,
                        practice_name=self._get_practice_name(practice_code),
                        doctor_name=random.choice(['Dr. Smith', 'Dr. Johnson', 'Dr. Brown', 'Dr. Wilson']),
                        specialty='General Practice',
                        appointment_datetime=slot_datetime,
                        duration_minutes=15,
                        appointment_type=random.choice(['routine', 'urgent']),
                        availability_status='available',
                        booking_url=f'https://appointments.nhs.uk/book/{practice_code}/{slot_datetime.strftime("%Y%m%d%H%M")}',
                        created_at=datetime.now()
                    )
                    
                    slots.append(slot)
        
        return slots
    
    def _get_practice_name(self, practice_code: str) -> str:
        """获取实践名称"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT practice_name FROM gp_practices WHERE practice_code = ?', (practice_code,))
            row = cursor.fetchone()
            conn.close()
            
            return row[0] if row else f"Practice {practice_code}"
            
        except Exception as e:
            logger.error(f"获取实践名称失败: {e}")
            return f"Practice {practice_code}"
    
    def _parse_fhir_slots(self, fhir_data: Dict, practice_code: str) -> List[GPSlot]:
        """解析FHIR格式的空位数据"""
        try:
            slots = []
            
            if 'entry' not in fhir_data:
                return slots
            
            for entry in fhir_data['entry']:
                resource = entry.get('resource', {})
                
                if resource.get('resourceType') != 'Slot':
                    continue
                
                slot = GPSlot(
                    slot_id=resource.get('id', ''),
                    practice_code=practice_code,
                    practice_name=self._get_practice_name(practice_code),
                    doctor_name=self._extract_practitioner_name(resource),
                    specialty=self._extract_specialty(resource),
                    appointment_datetime=datetime.fromisoformat(resource.get('start', '').replace('Z', '+00:00')),
                    duration_minutes=self._calculate_duration(resource),
                    appointment_type=self._extract_appointment_type(resource),
                    availability_status=resource.get('status', 'available'),
                    booking_url=self._generate_booking_url(practice_code, resource.get('id')),
                    created_at=datetime.now()
                )
                
                slots.append(slot)
            
            return slots
            
        except Exception as e:
            logger.error(f"解析FHIR空位数据失败: {e}")
            return []
    
    def _extract_practitioner_name(self, slot_resource: Dict) -> str:
        """从FHIR资源中提取医生姓名"""
        # 简化实现
        return "Dr. Available"
    
    def _extract_specialty(self, slot_resource: Dict) -> str:
        """从FHIR资源中提取专科"""
        return "General Practice"
    
    def _calculate_duration(self, slot_resource: Dict) -> int:
        """计算预约时长"""
        try:
            start = slot_resource.get('start', '')
            end = slot_resource.get('end', '')
            
            if start and end:
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                return int((end_dt - start_dt).total_seconds() / 60)
            
        except Exception:
            pass
        
        return 15  # 默认15分钟
    
    def _extract_appointment_type(self, slot_resource: Dict) -> str:
        """提取预约类型"""
        # 从FHIR资源中提取，简化为routine
        return "routine"
    
    def _generate_booking_url(self, practice_code: str, slot_id: str) -> str:
        """生成预约URL"""
        return f"https://appointments.nhs.uk/book/{practice_code}/{slot_id}"
    
    def _save_slots(self, slots: List[GPSlot]) -> List[GPSlot]:
        """保存空位到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            saved_slots = []
            for slot in slots:
                try:
                    cursor.execute('''
                    INSERT OR REPLACE INTO gp_slots 
                    (slot_id, practice_code, doctor_name, specialty, appointment_datetime, 
                     duration_minutes, appointment_type, availability_status, booking_url, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        slot.slot_id,
                        slot.practice_code,
                        slot.doctor_name,
                        slot.specialty,
                        slot.appointment_datetime,
                        slot.duration_minutes,
                        slot.appointment_type,
                        slot.availability_status,
                        slot.booking_url,
                        datetime.now()
                    ))
                    
                    saved_slots.append(slot)
                    
                except Exception as e:
                    logger.error(f"保存空位 {slot.slot_id} 失败: {e}")
            
            conn.commit()
            conn.close()
            
            return saved_slots
            
        except Exception as e:
            logger.error(f"保存空位失败: {e}")
            return []
    
    async def _generate_slot_alerts(self, practice_code: str, slots: List[GPSlot]) -> List[SlotAlert]:
        """为新空位生成提醒"""
        try:
            alerts = []
            
            # 获取关注此实践的用户
            interested_users = self._get_interested_users(practice_code)
            
            for user in interested_users:
                for slot in slots:
                    # 检查空位是否符合用户偏好
                    if self._matches_user_preferences(user, slot):
                        alert = SlotAlert(
                            alert_id=f"slot_alert_{user['user_id']}_{slot.slot_id}_{datetime.now().timestamp()}",
                            user_id=user['user_id'],
                            slot_id=slot.slot_id,
                            practice_code=practice_code,
                            alert_type='new_slot' if slot.appointment_type == 'routine' else 'urgent_slot',
                            priority=5 if slot.appointment_type == 'urgent' else 3,
                            created_at=datetime.now()
                        )
                        
                        # 保存提醒
                        if self._save_slot_alert(alert):
                            alerts.append(alert)
                            
                            # 发送通知
                            await self._send_slot_notification(user, slot, alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"生成空位提醒失败: {e}")
            return []
    
    def _get_interested_users(self, practice_code: str) -> List[Dict]:
        """获取关注指定实践的用户"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT ugp.user_id, up.phone_number, ugp.specialty_preference, 
                   ugp.appointment_type_preference, ugp.preferred_days, ugp.preferred_times,
                   ugp.enable_urgent_alerts, ugp.enable_routine_alerts
            FROM user_gp_preferences ugp
            INNER JOIN user_preferences up ON ugp.user_id = up.user_id
            WHERE ugp.practice_code = ? AND up.status = 'active'
            ''', (practice_code,))
            
            rows = cursor.fetchall()
            conn.close()
            
            users = []
            for row in rows:
                users.append({
                    'user_id': row[0],
                    'phone_number': row[1],
                    'specialty_preference': row[2],
                    'appointment_type_preference': row[3],
                    'preferred_days': json.loads(row[4]) if row[4] else [],
                    'preferred_times': json.loads(row[5]) if row[5] else [],
                    'enable_urgent_alerts': bool(row[6]),
                    'enable_routine_alerts': bool(row[7])
                })
            
            return users
            
        except Exception as e:
            logger.error(f"获取关注用户失败: {e}")
            return []
    
    def _matches_user_preferences(self, user: Dict, slot: GPSlot) -> bool:
        """检查空位是否符合用户偏好"""
        try:
            # 检查预约类型偏好
            if slot.appointment_type == 'urgent' and not user.get('enable_urgent_alerts', True):
                return False
            
            if slot.appointment_type == 'routine' and not user.get('enable_routine_alerts', True):
                return False
            
            # 检查首选日期
            preferred_days = user.get('preferred_days', [])
            if preferred_days:
                slot_day = slot.appointment_datetime.strftime('%A').lower()
                if slot_day not in [day.lower() for day in preferred_days]:
                    return False
            
            # 检查首选时间
            preferred_times = user.get('preferred_times', [])
            if preferred_times:
                slot_hour = slot.appointment_datetime.hour
                time_matched = False
                
                for time_range in preferred_times:
                    if isinstance(time_range, str):
                        if 'morning' in time_range.lower() and 6 <= slot_hour < 12:
                            time_matched = True
                        elif 'afternoon' in time_range.lower() and 12 <= slot_hour < 18:
                            time_matched = True
                        elif 'evening' in time_range.lower() and 18 <= slot_hour < 22:
                            time_matched = True
                
                if not time_matched:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查用户偏好匹配失败: {e}")
            return False
    
    def _save_slot_alert(self, alert: SlotAlert) -> bool:
        """保存空位提醒"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT OR IGNORE INTO slot_alerts 
            (alert_id, user_id, slot_id, practice_code, alert_type, priority, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert.alert_id,
                alert.user_id,
                alert.slot_id,
                alert.practice_code,
                alert.alert_type,
                alert.priority,
                alert.created_at
            ))
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            return success
            
        except Exception as e:
            logger.error(f"保存空位提醒失败: {e}")
            return False
    
    async def _send_slot_notification(self, user: Dict, slot: GPSlot, alert: SlotAlert):
        """发送空位通知"""
        try:
            if not self.whatsapp_service:
                logger.warning("WhatsApp服务未配置，无法发送空位通知")
                return
            
            alert_data = {
                'provider_name': slot.practice_name,
                'doctor_name': slot.doctor_name,
                'specialty_name': slot.specialty,
                'appointment_datetime': slot.appointment_datetime.strftime('%Y-%m-%d %H:%M'),
                'appointment_type': slot.appointment_type,
                'duration_minutes': slot.duration_minutes,
                'booking_url': slot.booking_url,
                'alert_type': alert.alert_type,
                'practice_code': slot.practice_code
            }
            
            success = self.whatsapp_service.send_alert_notification(
                user_phone=user['phone_number'],
                alert_type='slot_available',
                alert_data=alert_data
            )
            
            if success:
                # 更新提醒状态
                self._update_alert_status(alert.alert_id, 'sent')
                logger.info(f"空位通知发送成功: {alert.alert_id}")
            else:
                self._update_alert_status(alert.alert_id, 'failed')
                logger.error(f"空位通知发送失败: {alert.alert_id}")
            
        except Exception as e:
            logger.error(f"发送空位通知失败: {e}")
    
    def _update_alert_status(self, alert_id: str, status: str):
        """更新提醒状态"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            sent_at = datetime.now() if status == 'sent' else None
            
            cursor.execute('''
            UPDATE slot_alerts SET status = ?, sent_at = ? WHERE alert_id = ?
            ''', (status, sent_at, alert_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"更新提醒状态失败: {e}")
    
    def _log_monitoring_cycle(self, stats: Dict, duration: float):
        """记录监控周期日志"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO slot_monitor_log 
            (practices_checked, slots_found, alerts_generated, api_calls_made, errors_count, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                stats['practices_checked'],
                stats['slots_found'],
                stats['alerts_generated'],
                stats['api_calls_made'],
                stats['errors_count'],
                duration
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"记录监控日志失败: {e}")
    
    def add_user_gp_preference(self, user_id: str, practice_code: str, preferences: Dict) -> bool:
        """添加用户GP偏好"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT OR REPLACE INTO user_gp_preferences 
            (user_id, practice_code, specialty_preference, appointment_type_preference, 
             preferred_days, preferred_times, max_distance_km, enable_urgent_alerts, enable_routine_alerts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                practice_code,
                preferences.get('specialty_preference', ''),
                preferences.get('appointment_type_preference', 'routine'),
                json.dumps(preferences.get('preferred_days', [])),
                json.dumps(preferences.get('preferred_times', [])),
                preferences.get('max_distance_km', 10),
                preferences.get('enable_urgent_alerts', True),
                preferences.get('enable_routine_alerts', True)
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"用户GP偏好已保存: {user_id} -> {practice_code}")
            return True
            
        except Exception as e:
            logger.error(f"保存用户GP偏好失败: {e}")
            return False
    
    def get_available_slots(self, practice_code: str = None, days_ahead: int = 7) -> List[Dict]:
        """获取可用空位"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            where_clause = "WHERE availability_status = 'available' AND appointment_datetime >= datetime('now')"
            params = []
            
            if practice_code:
                where_clause += " AND practice_code = ?"
                params.append(practice_code)
            
            if days_ahead:
                where_clause += " AND appointment_datetime <= datetime('now', '+{} days')".format(days_ahead)
            
            cursor.execute(f'''
            SELECT s.slot_id, s.practice_code, p.practice_name, s.doctor_name, s.specialty,
                   s.appointment_datetime, s.duration_minutes, s.appointment_type, s.booking_url
            FROM gp_slots s
            INNER JOIN gp_practices p ON s.practice_code = p.practice_code
            {where_clause}
            ORDER BY s.appointment_datetime ASC
            ''', params)
            
            rows = cursor.fetchall()
            conn.close()
            
            slots = []
            for row in rows:
                slots.append({
                    'slot_id': row[0],
                    'practice_code': row[1],
                    'practice_name': row[2],
                    'doctor_name': row[3],
                    'specialty': row[4],
                    'appointment_datetime': row[5],
                    'duration_minutes': row[6],
                    'appointment_type': row[7],
                    'booking_url': row[8]
                })
            
            return slots
            
        except Exception as e:
            logger.error(f"获取可用空位失败: {e}")
            return []
    
    def get_monitoring_statistics(self) -> Dict:
        """获取监控统计信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 总统计
            cursor.execute('SELECT COUNT(*) FROM gp_slots')
            total_slots = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM gp_slots WHERE availability_status = 'available'")
            available_slots = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM slot_alerts')
            total_alerts = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM slot_alerts WHERE status = 'sent'")
            sent_alerts = cursor.fetchone()[0]
            
            # 今日统计
            cursor.execute("SELECT COUNT(*) FROM gp_slots WHERE DATE(created_at) = DATE('now')")
            today_slots = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM slot_alerts WHERE DATE(created_at) = DATE('now')")
            today_alerts = cursor.fetchone()[0]
            
            # 监控性能
            cursor.execute('''
            SELECT AVG(duration_seconds), AVG(practices_checked), AVG(slots_found), AVG(alerts_generated)
            FROM slot_monitor_log
            WHERE check_timestamp >= datetime('now', '-7 days')
            ''')
            perf_row = cursor.fetchone()
            
            conn.close()
            
            return {
                'total_slots': total_slots,
                'available_slots': available_slots,
                'total_alerts': total_alerts,
                'sent_alerts': sent_alerts,
                'today_slots': today_slots,
                'today_alerts': today_alerts,
                'alert_success_rate': (sent_alerts / max(total_alerts, 1)) * 100,
                'monitoring_performance': {
                    'avg_duration_seconds': round(perf_row[0] or 0, 2),
                    'avg_practices_checked': round(perf_row[1] or 0, 1),
                    'avg_slots_found': round(perf_row[2] or 0, 1),
                    'avg_alerts_generated': round(perf_row[3] or 0, 1)
                }
            }
            
        except Exception as e:
            logger.error(f"获取监控统计失败: {e}")
            return {} 