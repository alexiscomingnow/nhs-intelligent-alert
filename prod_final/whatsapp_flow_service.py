#!/usr/bin/env python3
"""
WhatsApp Flow Service - NHS Alert System
患者交互和订阅管理服务
"""

import json
import logging
import sqlite3
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class WhatsAppFlowService:
    """WhatsApp Flow集成服务"""
    
    def __init__(self, config_manager):
        self.config = config_manager
        self.db_path = self.config.get('database_url', 'sqlite:///nhs_alerts.db').replace('sqlite:///', '')
        
        # WhatsApp配置
        self.wa_token = os.getenv('WHATSAPP_TOKEN', 'demo_token')
        self.wa_phone_id = os.getenv('WHATSAPP_PHONE_ID', 'demo_phone_id')
        self.wa_verify_token = os.getenv('WHATSAPP_VERIFY_TOKEN', 'nhs_alert_verify')
        
        self.base_url = f"https://graph.facebook.com/v18.0/{self.wa_phone_id}/messages"
        
    def create_patient_setup_flow(self) -> Dict:
        """创建患者设置流程"""
        flow_config = {
            "version": "3.0",
            "screens": [
                {
                    "id": "WELCOME",
                    "title": "NHS等候提醒设置",
                    "layout": {
                        "type": "SingleColumnLayout",
                        "children": [
                            {
                                "type": "TextHeading",
                                "text": "欢迎使用NHS等候时间提醒服务"
                            },
                            {
                                "type": "TextBody",
                                "text": "我们将为您监控NHS等候时间，并在有更短等候选择时通知您。"
                            },
                            {
                                "type": "Footer",
                                "label": "开始设置",
                                "on-click-action": {
                                    "name": "navigate",
                                    "payload": {"screen": "POSTCODE_INPUT"}
                                }
                            }
                        ]
                    }
                },
                {
                    "id": "POSTCODE_INPUT",
                    "title": "输入您的邮编",
                    "layout": {
                        "type": "SingleColumnLayout",
                        "children": [
                            {
                                "type": "TextInput",
                                "name": "postcode",
                                "label": "邮编",
                                "input-type": "text",
                                "required": True,
                                "helper-text": "例如: SW1A 1AA"
                            },
                            {
                                "type": "Footer",
                                "label": "下一步",
                                "on-click-action": {
                                    "name": "navigate",
                                    "payload": {"screen": "SPECIALTY_SELECTION"}
                                }
                            }
                        ]
                    }
                },
                {
                    "id": "SPECIALTY_SELECTION",
                    "title": "选择专科",
                    "layout": {
                        "type": "SingleColumnLayout",
                        "children": [
                            {
                                "type": "RadioButtonsGroup",
                                "name": "specialty",
                                "label": "您需要哪个专科的治疗？",
                                "required": True,
                                "data-source": [
                                    {"id": "cardiology", "title": "心脏科 (Cardiology)"},
                                    {"id": "orthopaedics", "title": "骨科 (Orthopaedics)"},
                                    {"id": "general_surgery", "title": "普外科 (General Surgery)"},
                                    {"id": "dermatology", "title": "皮肤科 (Dermatology)"},
                                    {"id": "ophthalmology", "title": "眼科 (Ophthalmology)"},
                                    {"id": "ent", "title": "耳鼻喉科 (ENT)"},
                                    {"id": "gynaecology", "title": "妇科 (Gynaecology)"},
                                    {"id": "urology", "title": "泌尿科 (Urology)"}
                                ]
                            },
                            {
                                "type": "Footer",
                                "label": "下一步",
                                "on-click-action": {
                                    "name": "navigate",
                                    "payload": {"screen": "PREFERENCES"}
                                }
                            }
                        ]
                    }
                },
                {
                    "id": "PREFERENCES",
                    "title": "提醒偏好",
                    "layout": {
                        "type": "SingleColumnLayout",
                        "children": [
                            {
                                "type": "Dropdown",
                                "name": "threshold_weeks",
                                "label": "当等候时间超过多少周时提醒我？",
                                "required": True,
                                "data-source": [
                                    {"id": "4", "title": "4周"},
                                    {"id": "8", "title": "8周"},
                                    {"id": "12", "title": "12周"},
                                    {"id": "18", "title": "18周"},
                                    {"id": "25", "title": "25周"}
                                ]
                            },
                            {
                                "type": "Dropdown",
                                "name": "radius_km",
                                "label": "搜索范围",
                                "required": True,
                                "data-source": [
                                    {"id": "10", "title": "10公里内"},
                                    {"id": "25", "title": "25公里内"},
                                    {"id": "50", "title": "50公里内"},
                                    {"id": "100", "title": "100公里内"}
                                ]
                            },
                            {
                                "type": "CheckboxGroup",
                                "name": "notification_types",
                                "label": "通知类型",
                                "data-source": [
                                    {"id": "wait_time_change", "title": "等候时间变化"},
                                    {"id": "shorter_alternative", "title": "发现更短等候选择"},
                                    {"id": "slot_available", "title": "预约空位可用"},
                                    {"id": "private_option", "title": "私立医疗选择"}
                                ]
                            },
                            {
                                "type": "Footer",
                                "label": "完成设置",
                                "on-click-action": {
                                    "name": "complete",
                                    "payload": {"action": "setup_complete"}
                                }
                            }
                        ]
                    }
                }
            ]
        }
        
        return flow_config
    
    def process_flow_response(self, flow_data: Dict, user_phone: str) -> Dict:
        """处理Flow响应数据"""
        try:
            # 提取用户输入
            postcode = flow_data.get('postcode', '').upper().strip()
            specialty = flow_data.get('specialty', '')
            threshold_weeks = int(flow_data.get('threshold_weeks', 12))
            radius_km = int(flow_data.get('radius_km', 25))
            notification_types = flow_data.get('notification_types', [])
            
            # 验证邮编格式
            if not self._validate_postcode(postcode):
                return {
                    "status": "error",
                    "message": "邮编格式不正确，请重新输入"
                }
            
            # 保存用户偏好
            user_id = self._save_user_preferences(
                user_phone=user_phone,
                postcode=postcode,
                specialty=specialty,
                threshold_weeks=threshold_weeks,
                radius_km=radius_km,
                notification_types=notification_types
            )
            
            # 获取附近医院信息
            nearby_hospitals = self._get_nearby_hospitals(postcode, specialty, radius_km)
            
            # 发送确认消息
            confirmation_message = self._create_confirmation_message(
                postcode, specialty, threshold_weeks, radius_km, nearby_hospitals
            )
            
            # 发送初始数据卡片
            self._send_hospital_comparison(user_phone, nearby_hospitals)
            
            return {
                "status": "success",
                "message": "设置完成",
                "user_id": user_id,
                "nearby_hospitals": nearby_hospitals
            }
            
        except Exception as e:
            logger.error(f"处理Flow响应失败: {e}")
            return {
                "status": "error", 
                "message": "设置过程出错，请重试"
            }
    
    def _validate_postcode(self, postcode: str) -> bool:
        """验证英国邮编格式"""
        import re
        # 简化的英国邮编正则
        pattern = r'^[A-Z]{1,2}[0-9][A-Z0-9]?\s?[0-9][A-Z]{2}$'
        return bool(re.match(pattern, postcode))
    
    def _save_user_preferences(self, user_phone: str, postcode: str, specialty: str, 
                             threshold_weeks: int, radius_km: int, notification_types: List[str]) -> str:
        """保存用户偏好到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建用户偏好表（如果不存在）
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id TEXT PRIMARY KEY,
                phone_number TEXT UNIQUE,
                postcode TEXT,
                specialty TEXT,
                threshold_weeks INTEGER,
                radius_km INTEGER,
                notification_types TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            user_id = f"user_{user_phone.replace('+', '')}"
            notification_types_json = json.dumps(notification_types)
            
            # 插入或更新用户偏好
            cursor.execute('''
            INSERT OR REPLACE INTO user_preferences 
            (user_id, phone_number, postcode, specialty, threshold_weeks, radius_km, notification_types, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, user_phone, postcode, specialty, threshold_weeks, radius_km, notification_types_json, datetime.now()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"用户偏好已保存: {user_id}")
            return user_id
            
        except Exception as e:
            logger.error(f"保存用户偏好失败: {e}")
            raise
    
    def _get_nearby_hospitals(self, postcode: str, specialty: str, radius_km: int) -> List[Dict]:
        """获取附近医院的等候时间数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 简化版本：直接从NHS数据中查找匹配的专科
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
            LIMIT 5
            ''', (f'%{mapped_specialty}%',))
            
            rows = cursor.fetchall()
            conn.close()
            
            hospitals = []
            for row in rows:
                hospitals.append({
                    'provider_name': row[0],
                    'specialty_name': row[1], 
                    'waiting_time_weeks': row[2],
                    'patients_waiting': row[3],
                    'distance_km': self._calculate_distance(postcode, row[0]),  # 模拟距离
                    'recommendation_score': self._calculate_recommendation_score(row[2], row[3])
                })
            
            return hospitals
            
        except Exception as e:
            logger.error(f"获取附近医院失败: {e}")
            return []
    
    def _calculate_distance(self, postcode: str, provider_name: str) -> float:
        """计算距离（模拟实现）"""
        # 实际实现中应该使用地理编码API
        import random
        return round(random.uniform(5.0, 45.0), 1)
    
    def _calculate_recommendation_score(self, waiting_weeks: int, patients_waiting: int) -> float:
        """计算推荐评分"""
        # 简单评分算法：等候时间越短，评分越高
        if waiting_weeks <= 0:
            return 5.0
        
        base_score = max(0, 5.0 - (waiting_weeks / 10))
        
        # 考虑患者数量
        if patients_waiting > 500:
            base_score -= 0.5
        elif patients_waiting < 100:
            base_score += 0.5
            
        return round(max(0, min(5.0, base_score)), 1)
    
    def _create_confirmation_message(self, postcode: str, specialty: str, threshold_weeks: int, 
                                   radius_km: int, hospitals: List[Dict]) -> str:
        """创建确认消息"""
        specialty_cn = {
            'cardiology': '心脏科',
            'orthopaedics': '骨科',
            'general_surgery': '普外科',
            'dermatology': '皮肤科',
            'ophthalmology': '眼科',
            'ent': '耳鼻喉科',
            'gynaecology': '妇科',
            'urology': '泌尿科'
        }.get(specialty, specialty)
        
        message = f"""
🏥 *NHS等候提醒设置确认*

📍 *您的区域*: {postcode}
🩺 *专科*: {specialty_cn}
⏰ *提醒阈值*: {threshold_weeks}周
📍 *搜索范围*: {radius_km}公里

✅ *设置完成！*我们将为您监控等候时间变化。

📊 *当前附近医院状况*:
"""
        
        for i, hospital in enumerate(hospitals[:3], 1):
            message += f"""
{i}. *{hospital['provider_name']}*
   ⏰ 等候: {hospital['waiting_time_weeks']}周
   📍 距离: {hospital['distance_km']}公里
   ⭐ 推荐: {hospital['recommendation_score']}/5.0
"""
        
        message += """
🔔 我们会在以下情况通知您:
• 等候时间发生变化
• 发现更短等候的医院
• 有预约空位可用

输入 *停止* 可随时取消订阅
输入 *设置* 可修改偏好
"""
        
        return message
    
    def _send_hospital_comparison(self, user_phone: str, hospitals: List[Dict]):
        """发送医院对比卡片"""
        if not hospitals:
            return
            
        # 创建结构化消息
        message_data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": user_phone,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {
                    "type": "text",
                    "text": "附近医院等候时间对比"
                },
                "body": {
                    "text": "以下是根据您的偏好推荐的医院，按等候时间排序："
                },
                "footer": {
                    "text": "点击查看详细信息"
                },
                "action": {
                    "button": "查看医院",
                    "sections": [
                        {
                            "title": "推荐医院",
                            "rows": []
                        }
                    ]
                }
            }
        }
        
        # 添加医院选项
        for i, hospital in enumerate(hospitals[:10]):
            message_data["interactive"]["action"]["sections"][0]["rows"].append({
                "id": f"hospital_{i}",
                "title": hospital['provider_name'][:24],
                "description": f"{hospital['waiting_time_weeks']}周 • {hospital['distance_km']}km • ⭐{hospital['recommendation_score']}"
            })
        
        # 发送消息（模拟）
        self._send_whatsapp_message(message_data)
    
    def _send_whatsapp_message(self, message_data: Dict) -> bool:
        """发送WhatsApp消息"""
        try:
            headers = {
                'Authorization': f'Bearer {self.wa_token}',
                'Content-Type': 'application/json'
            }
            
            # 在开发环境中记录消息而不实际发送
            if self.config.get('debug', True):
                logger.info(f"模拟发送WhatsApp消息: {json.dumps(message_data, indent=2, ensure_ascii=False)}")
                return True
            
            response = requests.post(self.base_url, headers=headers, json=message_data)
            
            if response.status_code == 200:
                logger.info(f"WhatsApp消息发送成功: {message_data.get('to', 'unknown')}")
                return True
            else:
                logger.error(f"WhatsApp消息发送失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"发送WhatsApp消息异常: {e}")
            return False
    
    def send_alert_notification(self, user_phone: str, alert_type: str, alert_data: Dict) -> bool:
        """发送提醒通知"""
        try:
            if alert_type == "waiting_time_change":
                message = self._create_waiting_time_alert(alert_data)
            elif alert_type == "shorter_alternative":
                message = self._create_alternative_alert(alert_data)
            elif alert_type == "slot_available":
                message = self._create_slot_alert(alert_data)
            else:
                message = self._create_generic_alert(alert_data)
            
            message_data = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual", 
                "to": user_phone,
                "type": "text",
                "text": {"body": message}
            }
            
            return self._send_whatsapp_message(message_data)
            
        except Exception as e:
            logger.error(f"发送提醒通知失败: {e}")
            return False
    
    def _create_waiting_time_alert(self, alert_data: Dict) -> str:
        """创建等候时间变化提醒"""
        return f"""
🔔 *NHS等候时间更新*

🏥 *{alert_data.get('provider_name', '医院')}*
🩺 *{alert_data.get('specialty_name', '专科')}*

⏰ *等候时间变化*:
   之前: {alert_data.get('previous_weeks', 0)}周
   现在: {alert_data.get('current_weeks', 0)}周
   变化: {alert_data.get('change_weeks', 0):+d}周

📅 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}

🔍 输入 *搜索* 查看其他选择
⚙️ 输入 *设置* 修改提醒偏好
"""
    
    def _create_alternative_alert(self, alert_data: Dict) -> str:
        """创建替代选择提醒"""
        return f"""
🎯 *发现更好的选择！*

🏥 *推荐医院*: {alert_data.get('recommended_provider', '医院')}
🩺 *专科*: {alert_data.get('specialty_name', '专科')}

⏰ *等候对比*:
   您当前选择: {alert_data.get('current_weeks', 0)}周
   推荐选择: {alert_data.get('recommended_weeks', 0)}周
   可节省: {alert_data.get('savings_weeks', 0)}周 ⚡

📍 距离: {alert_data.get('distance_km', 0)}公里
⭐ 推荐评分: {alert_data.get('score', 0)}/5.0

🔗 [立即预约] | 🔍 [查看更多选择]

💡 此推荐基于最新NHS数据
"""
    
    def _create_slot_alert(self, alert_data: Dict) -> str:
        """创建空位可用提醒"""
        return f"""
🚨 *预约空位可用！*

🏥 *{alert_data.get('provider_name', '医院')}*
🩺 *{alert_data.get('specialty_name', '专科')}*

📅 *可用时间*:
   {alert_data.get('available_date', '即将公布')}
   {alert_data.get('available_time', '')}

⏰ 等候时间: {alert_data.get('waiting_weeks', 0)}周
📍 距离: {alert_data.get('distance_km', 0)}公里

🔗 *[立即预约]* - 空位有限！

⚠️ 请尽快行动，空位可能很快被占用
"""
    
    def _create_generic_alert(self, alert_data: Dict) -> str:
        """创建通用提醒"""
        return f"""
🔔 *NHS提醒更新*

{alert_data.get('message', '有新的更新信息')}

📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}

🔍 输入 *详情* 查看完整信息
⚙️ 输入 *设置* 修改提醒偏好
"""
    
    def get_user_preferences(self, user_phone: str) -> Optional[Dict]:
        """获取用户偏好"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT user_id, postcode, specialty, threshold_weeks, radius_km, notification_types, status
            FROM user_preferences WHERE phone_number = ?
            ''', (user_phone,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'user_id': row[0],
                    'postcode': row[1],
                    'specialty': row[2],
                    'threshold_weeks': row[3],
                    'radius_km': row[4],
                    'notification_types': json.loads(row[5]) if row[5] else [],
                    'status': row[6]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"获取用户偏好失败: {e}")
            return None
    
    def update_user_status(self, user_phone: str, status: str) -> bool:
        """更新用户状态"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            UPDATE user_preferences SET status = ?, updated_at = ?
            WHERE phone_number = ?
            ''', (status, datetime.now(), user_phone))
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            return success
            
        except Exception as e:
            logger.error(f"更新用户状态失败: {e}")
            return False
    
    def get_active_users(self) -> List[Dict]:
        """获取所有活跃用户"""
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