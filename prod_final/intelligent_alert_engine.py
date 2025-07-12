#!/usr/bin/env python3
"""
Intelligent Alert Engine - NHS Alert System
智能提醒引擎：基于规则的个性化NHS等候时间提醒
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import statistics
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class AlertRule:
    """提醒规则定义"""
    rule_id: str
    name: str
    condition_type: str  # threshold, change, comparison, prediction
    parameters: Dict
    priority: int  # 1-5, 5最高
    frequency_hours: int  # 提醒频率（小时）
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
    sent_at: Optional[datetime] = None
    status: str = 'pending'  # pending, sent, failed

class IntelligentAlertEngine:
    """智能提醒引擎"""
    
    def __init__(self, config_manager, whatsapp_service=None):
        self.config = config_manager
        self.whatsapp_service = whatsapp_service
        self.db_path = self.config.get('database_url', 'sqlite:///nhs_alerts.db').replace('sqlite:///', '')
        
        # 初始化默认提醒规则
        self.default_rules = self._create_default_rules()
        self._initialize_database()
    
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
                rule_id="shorter_alternative_found",
                name="发现更短等候选择",
                condition_type="comparison",
                parameters={"metric": "waiting_weeks", "operator": "<", "improvement_weeks": 4},
                priority=5,
                frequency_hours=24
            ),
            AlertRule(
                rule_id="regional_outlier",
                name="区域等候时间异常",
                condition_type="comparison",
                parameters={"metric": "waiting_weeks", "comparison": "regional_median", "threshold": 1.5},
                priority=2,
                frequency_hours=168
            ),
            AlertRule(
                rule_id="trend_prediction",
                name="等候时间趋势预测",
                condition_type="prediction",
                parameters={"metric": "waiting_weeks", "trend_weeks": 8, "prediction_threshold": 3},
                priority=3,
                frequency_hours=168
            ),
            AlertRule(
                rule_id="capacity_alert",
                name="医院容量提醒", 
                condition_type="threshold",
                parameters={"metric": "patients_waiting", "operator": ">", "value": 1000},
                priority=2,
                frequency_hours=168
            ),
            AlertRule(
                rule_id="specialty_bottleneck",
                name="专科瓶颈提醒",
                condition_type="comparison",
                parameters={"metric": "waiting_weeks", "comparison": "specialty_average", "threshold": 2.0},
                priority=4,
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
                priority INTEGER NOT NULL,
                frequency_hours INTEGER NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                priority INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP NULL,
                FOREIGN KEY (rule_id) REFERENCES alert_rules (rule_id)
            )
            ''')
            
            # 创建数据历史表（用于趋势分析）
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS nhs_data_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_name TEXT NOT NULL,
                specialty_name TEXT NOT NULL,
                waiting_time_weeks INTEGER,
                patients_waiting INTEGER,
                data_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(provider_name, specialty_name, data_date)
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
                UNIQUE(user_id, rule_id)
            )
            ''')
            
            conn.commit()
            
            # 插入默认规则
            self._insert_default_rules()
            
            conn.close()
            logger.info("提醒引擎数据库初始化完成")
            
        except Exception as e:
            logger.error(f"初始化提醒引擎数据库失败: {e}")
            raise
    
    def _insert_default_rules(self):
        """插入默认提醒规则"""
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
    
    def run_alert_checks(self) -> List[AlertEvent]:
        """运行所有提醒检查"""
        try:
            alerts = []
            active_users = self._get_active_users()
            active_rules = self._get_active_rules()
            
            logger.info(f"开始检查提醒: {len(active_users)}个用户, {len(active_rules)}个规则")
            
            for user in active_users:
                for rule in active_rules:
                    # 检查是否需要执行这个规则
                    if self._should_execute_rule(user['user_id'], rule):
                        try:
                            alert_events = self._execute_rule(user, rule)
                            alerts.extend(alert_events)
                        except Exception as e:
                            logger.error(f"执行规则 {rule.rule_id} 失败: {e}")
            
            # 处理生成的提醒
            processed_alerts = self._process_alerts(alerts)
            
            logger.info(f"提醒检查完成: 生成 {len(alerts)} 个提醒事件, 处理 {len(processed_alerts)} 个")
            
            return processed_alerts
            
        except Exception as e:
            logger.error(f"运行提醒检查失败: {e}")
            return []
    
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
                    'radius_km': row[5],
                    'notification_types': json.loads(row[6]) if row[6] else []
                })
            
            return users
            
        except Exception as e:
            logger.error(f"获取活跃用户失败: {e}")
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
            
            # 获取用户相关的医院数据
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
                        'provider_name': hospital.get('provider_name'),
                        'specialty_name': hospital.get('specialty_name'),
                        'current_value': current_value,
                        'threshold_value': threshold_value,
                        'metric': metric,
                        'operator': operator,
                        'user_threshold': user.get('threshold_weeks', 12)
                    }
                    
                    alert = AlertEvent(
                        event_id=f"alert_{user['user_id']}_{rule.rule_id}_{datetime.now().timestamp()}",
                        user_id=user['user_id'],
                        rule_id=rule.rule_id,
                        alert_type="threshold_breach",
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
            min_change = params.get('min_change', 1)
            
            # 获取历史数据对比
            changes = self._get_data_changes(user, metric, days=7)
            
            for change in changes:
                change_value = change.get('change', 0)
                
                # 检查变化条件
                condition_met = False
                if change_type == 'increase' and change_value >= min_change:
                    condition_met = True
                elif change_type == 'decrease' and change_value <= -min_change:
                    condition_met = True
                elif change_type == 'any' and abs(change_value) >= min_change:
                    condition_met = True
                
                if condition_met:
                    alert_data = {
                        'provider_name': change.get('provider_name'),
                        'specialty_name': change.get('specialty_name'),
                        'previous_value': change.get('previous_value'),
                        'current_value': change.get('current_value'),
                        'change_value': change_value,
                        'change_type': 'increase' if change_value > 0 else 'decrease',
                        'metric': metric
                    }
                    
                    alert = AlertEvent(
                        event_id=f"alert_{user['user_id']}_{rule.rule_id}_{datetime.now().timestamp()}",
                        user_id=user['user_id'],
                        rule_id=rule.rule_id,
                        alert_type="data_change",
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
                # 寻找更短等候时间的替代选择
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
            trend_weeks = params.get('trend_weeks', 8)
            prediction_threshold = params.get('prediction_threshold', 3)
            
            # 获取趋势预测
            predictions = self._predict_waiting_times(user, trend_weeks)
            
            for prediction in predictions:
                predicted_change = prediction.get('predicted_change', 0)
                
                if abs(predicted_change) >= prediction_threshold:
                    alert_data = {
                        'provider_name': prediction.get('provider_name'),
                        'specialty_name': prediction.get('specialty_name'),
                        'current_weeks': prediction.get('current_weeks'),
                        'predicted_weeks': prediction.get('predicted_weeks'),
                        'predicted_change': predicted_change,
                        'trend_direction': 'increasing' if predicted_change > 0 else 'decreasing',
                        'confidence': prediction.get('confidence', 0.5)
                    }
                    
                    alert = AlertEvent(
                        event_id=f"alert_{user['user_id']}_{rule.rule_id}_{datetime.now().timestamp()}",
                        user_id=user['user_id'],
                        rule_id=rule.rule_id,
                        alert_type="trend_prediction",
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
        """获取用户相关的医院数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 根据用户专科获取相关数据
            specialty = user.get('specialty', '')
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
            SELECT provider_name, specialty_name, waiting_time_weeks, patients_waiting
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
                    'patients_waiting': row[3]
                })
            
            return hospitals
            
        except Exception as e:
            logger.error(f"获取用户医院数据失败: {e}")
            return []
    
    def _get_data_changes(self, user: Dict, metric: str, days: int = 7) -> List[Dict]:
        """获取数据变化"""
        try:
            # 简化实现：模拟数据变化
            # 实际实现中应该查询历史数据表
            changes = []
            
            # 模拟一些数据变化
            if user.get('specialty') == 'cardiology':
                changes.append({
                    'provider_name': 'King\'s College Hospital NHS Foundation Trust',
                    'specialty_name': 'Cardiology',
                    'previous_value': 15,
                    'current_value': 18,
                    'change': 3
                })
            
            return changes
            
        except Exception as e:
            logger.error(f"获取数据变化失败: {e}")
            return []
    
    def _find_shorter_alternatives(self, user: Dict, min_improvement: int) -> List[Dict]:
        """寻找更短等候时间的替代选择"""
        try:
            # 获取用户当前关注的医院等候时间
            current_data = self._get_user_hospital_data(user)
            if not current_data:
                return []
            
            # 找到最短等候时间作为基准
            min_waiting = min(hospital['waiting_weeks'] for hospital in current_data if hospital['waiting_weeks'] > 0)
            
            alternatives = []
            for hospital in current_data:
                if hospital['waiting_weeks'] > 0 and hospital['waiting_weeks'] < min_waiting + min_improvement:
                    savings = min_waiting - hospital['waiting_weeks'] if hospital['waiting_weeks'] < min_waiting else 0
                    
                    if savings >= min_improvement:
                        alternatives.append({
                            'current_provider': 'Default Hospital',
                            'current_weeks': min_waiting,
                            'recommended_provider': hospital['provider_name'],
                            'recommended_weeks': hospital['waiting_weeks'],
                            'savings_weeks': savings,
                            'distance_km': 15.5,  # 模拟距离
                            'specialty_name': hospital['specialty_name']
                        })
            
            return alternatives[:3]  # 返回前3个最佳选择
            
        except Exception as e:
            logger.error(f"寻找替代选择失败: {e}")
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
                    'confidence': round(random.uniform(0.6, 0.9), 2)
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
            VALUES (?, ?, ?, COALESCE((SELECT alert_count + 1 FROM user_alert_history WHERE user_id = ? AND rule_id = ?), 1))
            ''', (user_id, rule_id, datetime.now(), user_id, rule_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"更新提醒历史失败: {e}")
    
    def _process_alerts(self, alerts: List[AlertEvent]) -> List[AlertEvent]:
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
                alert.created_at,
                alert.sent_at
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"保存提醒事件失败: {e}")
    
    def _send_alert_notification(self, alert: AlertEvent) -> bool:
        """发送提醒通知"""
        try:
            if not self.whatsapp_service:
                logger.warning("WhatsApp服务未配置，无法发送通知")
                return False
            
            # 获取用户手机号
            user_phone = self._get_user_phone(alert.user_id)
            if not user_phone:
                logger.error(f"找不到用户手机号: {alert.user_id}")
                return False
            
            # 发送通知
            return self.whatsapp_service.send_alert_notification(
                user_phone=user_phone,
                alert_type=alert.alert_type,
                alert_data=alert.data
            )
            
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
    
    def get_alert_statistics(self) -> Dict:
        """获取提醒统计信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 总提醒数
            cursor.execute('SELECT COUNT(*) FROM alert_events')
            total_alerts = cursor.fetchone()[0]
            
            # 按状态统计
            cursor.execute('''
            SELECT status, COUNT(*) FROM alert_events GROUP BY status
            ''')
            status_stats = dict(cursor.fetchall())
            
            # 按优先级统计
            cursor.execute('''
            SELECT priority, COUNT(*) FROM alert_events GROUP BY priority ORDER BY priority DESC
            ''')
            priority_stats = dict(cursor.fetchall())
            
            # 按类型统计
            cursor.execute('''
            SELECT alert_type, COUNT(*) FROM alert_events GROUP BY alert_type
            ''')
            type_stats = dict(cursor.fetchall())
            
            # 今日提醒数
            cursor.execute('''
            SELECT COUNT(*) FROM alert_events 
            WHERE DATE(created_at) = DATE('now')
            ''')
            today_alerts = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_alerts': total_alerts,
                'today_alerts': today_alerts,
                'status_distribution': status_stats,
                'priority_distribution': priority_stats,
                'type_distribution': type_stats,
                'success_rate': status_stats.get('sent', 0) / max(total_alerts, 1) * 100
            }
            
        except Exception as e:
            logger.error(f"获取提醒统计失败: {e}")
            return {}
    
    def create_custom_rule(self, rule_data: Dict) -> bool:
        """创建自定义提醒规则"""
        try:
            rule = AlertRule(
                rule_id=rule_data.get('rule_id'),
                name=rule_data.get('name'),
                condition_type=rule_data.get('condition_type'),
                parameters=rule_data.get('parameters', {}),
                priority=rule_data.get('priority', 3),
                frequency_hours=rule_data.get('frequency_hours', 24),
                is_active=rule_data.get('is_active', True)
            )
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
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
            
            logger.info(f"自定义规则创建成功: {rule.rule_id}")
            return True
            
        except Exception as e:
            logger.error(f"创建自定义规则失败: {e}")
            return False 