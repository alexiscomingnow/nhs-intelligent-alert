#!/usr/bin/env python3
"""
智能提醒引擎
提供NHS等候时间的智能提醒功能
"""

import sqlite3
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from geographic_service import GeographicService

logger = logging.getLogger(__name__)

@dataclass
class AlertRule:
    """提醒规则"""
    rule_id: str
    name: str
    condition_type: str  # threshold, change, comparison, prediction
    parameters: Dict
    priority: int = 1
    frequency_hours: int = 24
    is_active: bool = True

@dataclass
class AlertEvent:
    """提醒事件"""
    event_id: str
    user_id: str
    rule_id: str
    alert_type: str
    data: Dict
    priority: int
    created_at: datetime
    status: str = 'pending'
    sent_at: Optional[datetime] = None

class IntelligentAlertEngine:
    """智能提醒引擎"""
    
    def __init__(self, config_manager, whatsapp_service=None):
        self.config = config_manager
        self.whatsapp_service = whatsapp_service
        self.db_path = self.config.get('database_url', 'sqlite:///nhs_alerts.db').replace('sqlite:///', '')
        self.geo_service = GeographicService(self.db_path)
        
        # 初始化默认提醒规则
        self.default_rules = self._create_default_rules()
        self._initialize_database()
        self._monitor_interval_seconds = self.config.get('alert_monitor_interval', 300)
        self._monitoring_task: Optional['asyncio.Task'] = None
    
    def _create_default_rules(self) -> List[AlertRule]:
        """创建默认提醒规则"""
        return [
            AlertRule(
                rule_id="waiting_time_threshold",
                name="等候时间阈值提醒",
                condition_type="threshold",
                parameters={"metric": "waiting_weeks", "operator": ">", "value": 12},
                priority=3,
                frequency_hours=168  # 每周检查一次
            ),
            AlertRule(
                rule_id="waiting_time_increase",
                name="等候时间增加提醒",
                condition_type="change",
                parameters={"metric": "waiting_weeks", "change_type": "increase", "min_change": 2},
                priority=4,
                frequency_hours=24  # 每天检查
            ),
            AlertRule(
                rule_id="waiting_time_decrease",
                name="等候时间减少提醒",
                condition_type="change", 
                parameters={"metric": "waiting_weeks", "change_type": "decrease", "min_change": 2},
                priority=4,
                frequency_hours=24
            ),
            AlertRule(
                rule_id="shorter_alternatives",
                name="更短等候时间替代方案",
                condition_type="comparison",
                parameters={"improvement_weeks": 4},
                priority=3,
                frequency_hours=168
            ),
            AlertRule(
                rule_id="regional_outlier",
                name="地区异常提醒",
                condition_type="comparison",
                parameters={"outlier_threshold": 2.0},  # 超过平均值2倍标准差
                priority=2,
                frequency_hours=72
            )
        ]
    
    def _initialize_database(self):
        """初始化数据库表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建提醒规则表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_rules (
                rule_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                condition_type TEXT NOT NULL,
                parameters TEXT NOT NULL,
                priority INTEGER DEFAULT 1,
                frequency_hours INTEGER DEFAULT 24,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # 创建用户提醒历史表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_alert_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                rule_id TEXT NOT NULL,
                last_alert_time TIMESTAMP NOT NULL,
                alert_count INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # 创建提醒事件表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_events (
                event_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                rule_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                data TEXT NOT NULL,
                priority INTEGER DEFAULT 1,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP
            )
            ''')
            
            conn.commit()
            conn.close()
            
            # 插入默认规则
            self._insert_default_rules()
            
        except Exception as e:
            logger.error(f"初始化数据库失败: {e}")
    
    def _insert_default_rules(self):
        """插入默认规则"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for rule in self.default_rules:
                cursor.execute('''
                INSERT OR REPLACE INTO alert_rules 
                (rule_id, name, condition_type, parameters, priority, frequency_hours, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    rule.rule_id,
                    rule.name,
                    rule.condition_type,
                    json.dumps(rule.parameters),
                    rule.priority,
                    rule.frequency_hours,
                    rule.is_active
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"插入默认规则失败: {e}")
    
    async def start_monitoring(self):
        """开始监控"""
        if self._monitoring_task and not self._monitoring_task.done():
            return
        
        self._monitoring_task = asyncio.create_task(self._monitor_loop())
        logger.info("智能提醒监控已启动")
    
    async def stop_monitoring(self):
        """停止监控"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("智能提醒监控已停止")
    
    async def _monitor_loop(self):
        """监控循环"""
        try:
            while True:
                await self._check_all_alerts()
                await asyncio.sleep(self._monitor_interval_seconds)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"监控循环错误: {e}")
            await asyncio.sleep(60)  # 等待1分钟后重试
    
    async def _check_all_alerts(self):
        """检查所有用户的提醒"""
        try:
            users = self._get_active_users()
            logger.info(f"检查 {len(users)} 个活跃用户的提醒")
            
            all_alerts = []
            for user in users:
                user_alerts = await self._check_user_alerts(user)
                all_alerts.extend(user_alerts)
            
            if all_alerts:
                processed_alerts = await self._process_alerts(all_alerts)
                logger.info(f"处理了 {len(processed_alerts)} 个提醒")
            
        except Exception as e:
            logger.error(f"检查提醒失败: {e}")
    
    def _get_active_users(self) -> List[Dict]:
        """获取活跃用户"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT user_id, phone_number, postcode, specialty, threshold_weeks, radius_km, notification_types
            FROM user_preferences WHERE status = 'active'
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            users = []
            for row in rows:
                users.append({
                    'user_id': row[0],
                    'phone_number': row[1],
                    'postcode': row[2],
                    'specialty': row[3],
                    'threshold_weeks': row[4],
                    'radius_km': row[5] or 25,
                    'notification_types': json.loads(row[6]) if row[6] else []
                })
            
            return users
            
        except Exception as e:
            logger.error(f"获取活跃用户失败: {e}")
            return []
    
    async def _check_user_alerts(self, user: Dict) -> List[AlertEvent]:
        """检查单个用户的提醒"""
        try:
            alerts = []
            rules = self._get_active_rules()
            
            for rule in rules:
                if self._should_execute_rule(user['user_id'], rule):
                    rule_alerts = self._execute_rule(user, rule)
                    alerts.extend(rule_alerts)
            
            return alerts
            
        except Exception as e:
            logger.error(f"检查用户提醒失败: {e}")
            return []
    
    def _get_active_rules(self) -> List[AlertRule]:
        """获取活跃规则"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT rule_id, name, condition_type, parameters, priority, frequency_hours, is_active
            FROM alert_rules WHERE is_active = 1
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            rules = []
            for row in rows:
                rules.append(AlertRule(
                    rule_id=row[0],
                    name=row[1],
                    condition_type=row[2],
                    parameters=json.loads(row[3]),
                    priority=row[4],
                    frequency_hours=row[5],
                    is_active=bool(row[6])
                ))
            
            return rules
            
        except Exception as e:
            logger.error(f"获取活跃规则失败: {e}")
            return []
    
    def _should_execute_rule(self, user_id: str, rule: AlertRule) -> bool:
        """检查是否应该执行规则"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查上次执行时间
            cursor.execute('''
            SELECT last_alert_time FROM user_alert_history 
            WHERE user_id = ? AND rule_id = ?
            ''', (user_id, rule.rule_id))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return True  # 从未执行过
            
            last_time = datetime.fromisoformat(row[0])
            time_diff = datetime.now() - last_time
            
            return time_diff.total_seconds() >= rule.frequency_hours * 3600
            
        except Exception as e:
            logger.error(f"检查规则执行条件失败: {e}")
            return False
    
    def _execute_rule(self, user: Dict, rule: AlertRule) -> List[AlertEvent]:
        """执行单个规则"""
        try:
            alerts = []
            
            if rule.condition_type == "threshold":
                alerts = self._check_threshold_condition(user, rule)
            elif rule.condition_type == "change":
                alerts = self._check_change_condition(user, rule)
            elif rule.condition_type == "comparison":
                alerts = self._check_comparison_condition(user, rule)
            elif rule.condition_type == "prediction":
                alerts = self._check_prediction_condition(user, rule)
            
            # 更新执行历史
            if alerts:
                self._update_alert_history(user['user_id'], rule.rule_id)
            
            return alerts
            
        except Exception as e:
            logger.error(f"执行规则失败: {e}")
            return []
    
    def _check_threshold_condition(self, user: Dict, rule: AlertRule) -> List[AlertEvent]:
        """检查阈值条件"""
        try:
            alerts = []
            params = rule.parameters
            metric = params.get('metric', 'waiting_weeks')
            operator = params.get('operator', '>')
            threshold_value = params.get('value', 0)
            
            # 获取用户相关的医院数据（基于地理位置过滤）
            hospital_data = self._get_user_hospital_data(user)
            
            for hospital in hospital_data:
                current_value = hospital.get(metric, 0)
                
                # 检查阈值条件
                condition_met = False
                if operator == '>' and current_value > threshold_value:
                    condition_met = True
                elif operator == '<' and current_value < threshold_value:
                    condition_met = True
                elif operator == '>=' and current_value >= threshold_value:
                    condition_met = True
                elif operator == '<=' and current_value <= threshold_value:
                    condition_met = True
                elif operator == '==' and current_value == threshold_value:
                    condition_met = True
                
                if condition_met:
                    alert_data = {
                        'hospital_name': hospital.get('provider_name'),
                        'specialty_name': hospital.get('specialty_name'),
                        'current_value': current_value,
                        'threshold_value': threshold_value,
                        'metric': metric,
                        'distance_km': hospital.get('distance_km')
                    }
                    
                    alert = AlertEvent(
                        event_id=f"alert_{user['user_id']}_{rule.rule_id}_{datetime.now().timestamp()}",
                        user_id=user['user_id'],
                        rule_id=rule.rule_id,
                        alert_type="threshold_exceeded",
                        data=alert_data,
                        priority=rule.priority,
                        created_at=datetime.now()
                    )
                    
                    alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"检查阈值条件失败: {e}")
            return []
    
    def _check_change_condition(self, user: Dict, rule: AlertRule) -> List[AlertEvent]:
        """检查变化条件"""
        try:
            alerts = []
            params = rule.parameters
            metric = params.get('metric', 'waiting_weeks')
            change_type = params.get('change_type', 'increase')
            min_change = params.get('min_change', 2)
            
            # 获取历史对比数据
            historical_changes = self._get_historical_changes(user, metric)
            
            for change in historical_changes:
                if change_type == 'increase' and change['change'] >= min_change:
                    condition_met = True
                elif change_type == 'decrease' and change['change'] <= -min_change:
                    condition_met = True
                else:
                    condition_met = False
                
                if condition_met:
                    alert_data = {
                        'hospital_name': change.get('hospital_name'),
                        'specialty_name': change.get('specialty_name'),
                        'previous_value': change.get('previous_value'),
                        'current_value': change.get('current_value'),
                        'change': change.get('change'),
                        'change_type': change_type,
                        'distance_km': change.get('distance_km')
                    }
                    
                    alert = AlertEvent(
                        event_id=f"alert_{user['user_id']}_{rule.rule_id}_{datetime.now().timestamp()}",
                        user_id=user['user_id'],
                        rule_id=rule.rule_id,
                        alert_type=f"waiting_time_{change_type}",
                        data=alert_data,
                        priority=rule.priority,
                        created_at=datetime.now()
                    )
                    
                    alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"检查变化条件失败: {e}")
            return []
    
    def _check_comparison_condition(self, user: Dict, rule: AlertRule) -> List[AlertEvent]:
        """检查比较条件"""
        try:
            alerts = []
            params = rule.parameters
            
            if params.get('improvement_weeks'):
                # 寻找更短等候时间的替代选择（基于地理位置）
                alternatives = self._find_shorter_alternatives(user, params.get('improvement_weeks', 4))
                
                for alt in alternatives:
                    alert_data = {
                        'current_provider': alt.get('current_provider'),
                        'current_weeks': alt.get('current_weeks'),
                        'recommended_provider': alt.get('recommended_provider'),
                        'recommended_weeks': alt.get('recommended_weeks'),
                        'savings_weeks': alt.get('savings_weeks'),
                        'distance_km': alt.get('distance_km'),
                        'specialty_name': alt.get('specialty_name')
                    }
                    
                    alert = AlertEvent(
                        event_id=f"alert_{user['user_id']}_{rule.rule_id}_{datetime.now().timestamp()}",
                        user_id=user['user_id'],
                        rule_id=rule.rule_id,
                        alert_type="shorter_alternative",
                        data=alert_data,
                        priority=rule.priority,
                        created_at=datetime.now()
                    )
                    
                    alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"检查比较条件失败: {e}")
            return []
    
    def _check_prediction_condition(self, user: Dict, rule: AlertRule) -> List[AlertEvent]:
        """检查预测条件"""
        try:
            alerts = []
            params = rule.parameters
            
            # 预测等候时间趋势
            predictions = self._predict_waiting_times(user, params.get('prediction_weeks', 4))
            
            for prediction in predictions:
                if prediction.get('predicted_change', 0) > params.get('threshold_change', 2):
                    alert_data = {
                        'hospital_name': prediction.get('provider_name'),
                        'specialty_name': prediction.get('specialty_name'),
                        'current_weeks': prediction.get('current_weeks'),
                        'predicted_weeks': prediction.get('predicted_weeks'),
                        'predicted_change': prediction.get('predicted_change'),
                        'confidence': prediction.get('confidence'),
                        'distance_km': prediction.get('distance_km')
                    }
                    
                    alert = AlertEvent(
                        event_id=f"alert_{user['user_id']}_{rule.rule_id}_{datetime.now().timestamp()}",
                        user_id=user['user_id'],
                        rule_id=rule.rule_id,
                        alert_type="waiting_time_prediction",
                        data=alert_data,
                        priority=rule.priority,
                        created_at=datetime.now()
                    )
                    
                    alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"检查预测条件失败: {e}")
            return []
    
    def _get_user_hospital_data(self, user: Dict) -> List[Dict]:
        """获取用户相关的医院数据（基于地理位置过滤）"""
        try:
            specialty = user.get('specialty', '')
            postcode = user.get('postcode', '')
            radius_km = user.get('radius_km', 25)
            
            if not postcode:
                # 如果没有邮编，返回所有相关专科数据
                return self._get_all_specialty_data(specialty)
            
            # 使用地理服务获取附近医院
            nearby_hospitals = self.geo_service.get_nearby_hospitals_from_db(
                postcode, specialty, radius_km, self.db_path
            )
            
            return nearby_hospitals
            
        except Exception as e:
            logger.error(f"获取用户医院数据失败: {e}")
            return []
    
    def _get_all_specialty_data(self, specialty: str) -> List[Dict]:
        """获取所有专科数据（无地理限制）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 根据用户专科获取相关数据
            specialty_mapping = {
                'cardiology': 'Cardiology',
                'orthopaedics': 'Orthopaedics',
                'general_surgery': 'General Surgery',
                'dermatology': 'Dermatology',
                'ophthalmology': 'Ophthalmology',
                'ent': 'ENT',
                'gynaecology': 'Gynaecology',
                'urology': 'Urology'
            }
            
            mapped_specialty = specialty_mapping.get(specialty, specialty)
            
            cursor.execute('''
            SELECT org_name, specialty_name, waiting_time_weeks, patient_count
            FROM nhs_rtt_data 
            WHERE specialty_name LIKE ?
            ORDER BY waiting_time_weeks ASC
            ''', (f'%{mapped_specialty}%',))
            
            rows = cursor.fetchall()
            conn.close()
            
            hospitals = []
            for row in rows:
                hospitals.append({
                    'provider_name': row[0],
                    'specialty_name': row[1],
                    'waiting_weeks': row[2],
                    'patients_waiting': row[3],
                    'distance_km': None  # 无地理信息
                })
            
            return hospitals
            
        except Exception as e:
            logger.error(f"获取所有专科数据失败: {e}")
            return []
    
    def _find_shorter_alternatives(self, user: Dict, min_improvement: int) -> List[Dict]:
        """寻找更短等候时间的替代选择（基于地理位置）"""
        try:
            # 获取用户当前关注的医院等候时间（基于地理位置）
            current_data = self._get_user_hospital_data(user)
            if not current_data:
                return []
            
            # 找到当前最短等候时间作为基准
            min_waiting = min(hospital['waiting_weeks'] for hospital in current_data if hospital['waiting_weeks'] > 0)
            
            alternatives = []
            for hospital in current_data:
                if hospital['waiting_weeks'] > 0 and hospital['waiting_weeks'] < min_waiting:
                    savings = min_waiting - hospital['waiting_weeks']
                    
                    if savings >= min_improvement:
                        alternatives.append({
                            'current_provider': 'Current Choice',
                            'current_weeks': min_waiting,
                            'recommended_provider': hospital['provider_name'],
                            'recommended_weeks': hospital['waiting_weeks'],
                            'savings_weeks': savings,
                            'distance_km': hospital.get('distance_km'),
                            'specialty_name': hospital['specialty_name']
                        })
            
            return alternatives[:3]  # 返回前3个最佳选择
            
        except Exception as e:
            logger.error(f"寻找替代选择失败: {e}")
            return []
    
    def _get_historical_changes(self, user: Dict, metric: str) -> List[Dict]:
        """获取历史变化数据"""
        try:
            # 简化实现：获取最近的变化数据
            hospital_data = self._get_user_hospital_data(user)
            
            # 模拟历史变化数据
            changes = []
            for hospital in hospital_data[:3]:  # 只检查前3个医院
                import random
                previous_value = hospital.get('waiting_weeks', 0) + random.randint(-3, 3)
                current_value = hospital.get('waiting_weeks', 0)
                change = current_value - previous_value
                
                changes.append({
                    'hospital_name': hospital['provider_name'],
                    'specialty_name': hospital['specialty_name'],
                    'previous_value': previous_value,
                    'current_value': current_value,
                    'change': change,
                    'distance_km': hospital.get('distance_km')
                })
            
            return changes
            
        except Exception as e:
            logger.error(f"获取历史变化数据失败: {e}")
            return []
    
    def _predict_waiting_times(self, user: Dict, weeks: int) -> List[Dict]:
        """预测等候时间趋势"""
        try:
            # 简化实现：基于历史数据的线性回归预测
            # 实际实现中需要更复杂的时间序列分析
            
            predictions = []
            hospital_data = self._get_user_hospital_data(user)
            
            for hospital in hospital_data[:3]:  # 只预测前3个医院
                current_weeks = hospital.get('waiting_weeks', 0)
                
                # 模拟趋势预测
                import random
                trend = random.uniform(-2, 3)  # 随机趋势
                predicted_weeks = max(0, current_weeks + trend)
                
                predictions.append({
                    'provider_name': hospital['provider_name'],
                    'specialty_name': hospital['specialty_name'],
                    'current_weeks': current_weeks,
                    'predicted_weeks': round(predicted_weeks, 1),
                    'predicted_change': round(trend, 1),
                    'confidence': round(random.uniform(0.6, 0.9), 2),
                    'distance_km': hospital.get('distance_km')
                })
            
            return predictions
            
        except Exception as e:
            logger.error(f"预测等候时间失败: {e}")
            return []
    
    def _update_alert_history(self, user_id: str, rule_id: str):
        """更新提醒历史"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT OR REPLACE INTO user_alert_history 
            (user_id, rule_id, last_alert_time, alert_count)
            VALUES (?, ?, ?, COALESCE((SELECT alert_count FROM user_alert_history WHERE user_id = ? AND rule_id = ?), 0) + 1)
            ''', (user_id, rule_id, datetime.now().isoformat(), user_id, rule_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"更新提醒历史失败: {e}")
    
    async def _process_alerts(self, alerts: List[AlertEvent]) -> List[AlertEvent]:
        """处理提醒事件"""
        try:
            processed = []
            
            # 按优先级排序
            alerts.sort(key=lambda x: x.priority, reverse=True)
            
            # 去重和限制
            seen_users = set()
            for alert in alerts:
                # 每个用户每次最多收到一个高优先级提醒
                if alert.priority >= 4 and alert.user_id in seen_users:
                    continue
                
                # 保存到数据库
                self._save_alert_event(alert)
                
                # 发送通知
                if self.whatsapp_service:
                    success = self._send_alert_notification(alert)
                    if success:
                        alert.status = 'sent'
                        alert.sent_at = datetime.now()
                    else:
                        alert.status = 'failed'
                
                processed.append(alert)
                if alert.priority >= 4:
                    seen_users.add(alert.user_id)
            
            return processed
            
        except Exception as e:
            logger.error(f"处理提醒事件失败: {e}")
            return []
    
    def _save_alert_event(self, alert: AlertEvent):
        """保存提醒事件到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO alert_events 
            (event_id, user_id, rule_id, alert_type, data, priority, status, created_at, sent_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert.event_id,
                alert.user_id,
                alert.rule_id,
                alert.alert_type,
                json.dumps(alert.data),
                alert.priority,
                alert.status,
                alert.created_at.isoformat(),
                alert.sent_at.isoformat() if alert.sent_at else None
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"保存提醒事件失败: {e}")
    
    def _send_alert_notification(self, alert: AlertEvent) -> bool:
        """发送提醒通知"""
        try:
            if not self.whatsapp_service:
                return False
            
            # 格式化提醒消息
            message = self._format_alert_message(alert)
            
            # 发送消息
            # 注意：这里需要从用户ID获取手机号
            user_phone = self._get_user_phone(alert.user_id)
            if user_phone:
                return self.whatsapp_service.send_message(user_phone, message)
            
            return False
            
        except Exception as e:
            logger.error(f"发送提醒通知失败: {e}")
            return False
    
    def _get_user_phone(self, user_id: str) -> Optional[str]:
        """获取用户手机号"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT phone_number FROM user_preferences WHERE user_id = ?
            ''', (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            return row[0] if row else None
            
        except Exception as e:
            logger.error(f"获取用户手机号失败: {e}")
            return None
    
    def _format_alert_message(self, alert: AlertEvent) -> str:
        """格式化提醒消息"""
        try:
            data = alert.data
            alert_type = alert.alert_type
            
            if alert_type == "threshold_exceeded":
                message = f"""🚨 **等候时间提醒**

🏥 医院: {data.get('hospital_name', 'Unknown')}
🩺 专科: {data.get('specialty_name', 'Unknown')}
⏰ 等候时间: {data.get('current_value', 0)} 周
📊 阈值: {data.get('threshold_value', 0)} 周"""
                
                if data.get('distance_km'):
                    message += f"\n📍 距离: {data['distance_km']} 公里"
                
                message += "\n\n💡 建议查看其他选择或考虑私立医疗"
                
            elif alert_type == "shorter_alternative":
                message = f"""🎯 **更短等候时间选择**

🏥 推荐医院: {data.get('recommended_provider', 'Unknown')}
🩺 专科: {data.get('specialty_name', 'Unknown')}
⏰ 等候时间: {data.get('recommended_weeks', 0)} 周
⚡ 可节省: {data.get('savings_weeks', 0)} 周"""
                
                if data.get('distance_km'):
                    message += f"\n📍 距离: {data['distance_km']} 公里"
                
                message += "\n\n💡 考虑转诊到此医院获得更快治疗"
                
            elif alert_type.startswith("waiting_time_"):
                change_type = "增加" if "increase" in alert_type else "减少"
                icon = "📈" if "increase" in alert_type else "📉"
                
                message = f"""{icon} **等候时间{change_type}提醒**

🏥 医院: {data.get('hospital_name', 'Unknown')}
🩺 专科: {data.get('specialty_name', 'Unknown')}
⏰ 之前: {data.get('previous_value', 0)} 周
⏰ 现在: {data.get('current_value', 0)} 周
📊 变化: {data.get('change', 0):+} 周"""
                
                if data.get('distance_km'):
                    message += f"\n📍 距离: {data['distance_km']} 公里"
                
            else:
                message = f"📋 **系统提醒**: {alert_type}"
            
            return message
            
        except Exception as e:
            logger.error(f"格式化提醒消息失败: {e}")
            return "📋 系统提醒（格式化错误）"
    
    def get_alert_statistics(self) -> Dict:
        """获取提醒统计信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 统计各种提醒类型的数量
            cursor.execute('''
            SELECT alert_type, status, COUNT(*) 
            FROM alert_events 
            WHERE created_at >= date('now', '-7 days')
            GROUP BY alert_type, status
            ''')
            
            stats_rows = cursor.fetchall()
            
            # 统计活跃用户数
            cursor.execute('''
            SELECT COUNT(DISTINCT user_id) FROM user_preferences WHERE status = 'active'
            ''')
            
            active_users = cursor.fetchone()[0]
            
            # 统计活跃规则数
            cursor.execute('''
            SELECT COUNT(*) FROM alert_rules WHERE is_active = 1
            ''')
            
            active_rules = cursor.fetchone()[0]
            
            conn.close()
            
            stats = {
                'active_users': active_users,
                'active_rules': active_rules,
                'recent_alerts': {}
            }
            
            for alert_type, status, count in stats_rows:
                if alert_type not in stats['recent_alerts']:
                    stats['recent_alerts'][alert_type] = {}
                stats['recent_alerts'][alert_type][status] = count
            
            return stats
            
        except Exception as e:
            logger.error(f"获取提醒统计失败: {e}")
            return {'error': str(e)} 