#!/usr/bin/env python3
"""
WhatsApp Flow Service
处理WhatsApp Interactive Flow的用户交互
"""

import sqlite3
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from geographic_service import GeographicService

logger = logging.getLogger(__name__)

class WhatsAppFlowService:
    """WhatsApp Flow服务"""
    
    def __init__(self, db_path: str = 'nhs_alerts.db'):
        self.db_path = db_path
        self.geo_service = GeographicService(db_path)
        self._initialize_database()
    
    def _initialize_database(self):
        """初始化数据库表"""
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
            
            # 创建用户交互历史表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                interaction_type TEXT NOT NULL,
                interaction_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"初始化数据库失败: {e}")
    
    def create_interactive_flow(self, flow_type: str = 'user_preferences') -> Dict:
        """创建交互式Flow"""
        if flow_type == 'user_preferences':
            return self._create_preferences_flow()
        elif flow_type == 'hospital_comparison':
            return self._create_comparison_flow()
        else:
            return {"error": "未知的Flow类型"}
    
    def _create_preferences_flow(self) -> Dict:
        """创建用户偏好设置Flow"""
        return {
            "version": "3.0",
            "data_api_version": "3.0",
            "routing_model": {
                "PREFERENCES_SETUP": [
                    "POSTCODE_INPUT",
                    "SPECIALTY_SELECTION",
                    "THRESHOLD_SETTING",
                    "RADIUS_SETTING",
                    "NOTIFICATION_SETUP",
                    "CONFIRMATION"
                ]
            },
            "screens": [
                {
                    "id": "PREFERENCES_SETUP",
                    "title": "NHS 等候时间提醒设置",
                    "layout": {
                        "type": "SingleColumnLayout",
                        "children": [
                            {
                                "type": "TextHeading",
                                "text": "🏥 设置您的个人偏好"
                            },
                            {
                                "type": "TextBody",
                                "text": "我们将根据您的偏好提供个性化的NHS等候时间提醒"
                            }
                        ]
                    },
                    "terminal": False
                },
                {
                    "id": "POSTCODE_INPUT",
                    "title": "邮编设置",
                    "data": [
                        {
                            "type": "string",
                            "name": "postcode",
                            "label": "您的邮编",
                            "required": True,
                            "example": "SW1A 1AA"
                        }
                    ],
                    "layout": {
                        "type": "SingleColumnLayout",
                        "children": [
                            {
                                "type": "TextHeading", 
                                "text": "📍 输入您的邮编"
                            },
                            {
                                "type": "TextInput",
                                "label": "邮编",
                                "name": "postcode",
                                "required": True,
                                "input-type": "text"
                            }
                        ]
                    },
                    "terminal": False
                },
                {
                    "id": "SPECIALTY_SELECTION",
                    "title": "医疗专科选择",
                    "data": [
                        {
                            "type": "string",
                            "name": "specialty",
                            "label": "医疗专科",
                            "required": True
                        }
                    ],
                    "layout": {
                        "type": "SingleColumnLayout",
                        "children": [
                            {
                                "type": "TextHeading",
                                "text": "🩺 选择您关注的医疗专科"
                            },
                            {
                                "type": "RadioButtonsGroup",
                                "label": "医疗专科",
                                "name": "specialty",
                                "required": True,
                                "data-source": [
                                    {"id": "cardiology", "title": "心脏科 (Cardiology)"},
                                    {"id": "orthopaedics", "title": "骨科 (Orthopaedics)"},
                                    {"id": "general_surgery", "title": "普通外科 (General Surgery)"},
                                    {"id": "dermatology", "title": "皮肤科 (Dermatology)"},
                                    {"id": "ophthalmology", "title": "眼科 (Ophthalmology)"},
                                    {"id": "ent", "title": "耳鼻喉科 (ENT)"},
                                    {"id": "gynaecology", "title": "妇科 (Gynaecology)"},
                                    {"id": "urology", "title": "泌尿科 (Urology)"}
                                ]
                            }
                        ]
                    },
                    "terminal": False
                },
                {
                    "id": "THRESHOLD_SETTING",
                    "title": "等候时间阈值",
                    "data": [
                        {
                            "type": "number",
                            "name": "threshold_weeks",
                            "label": "等候时间阈值（周）",
                            "required": True
                        }
                    ],
                    "layout": {
                        "type": "SingleColumnLayout",
                        "children": [
                            {
                                "type": "TextHeading",
                                "text": "⏰ 设置等候时间阈值"
                            },
                            {
                                "type": "TextBody",
                                "text": "当等候时间超过此阈值时，我们会提醒您"
                            },
                            {
                                "type": "Dropdown",
                                "label": "等候时间阈值（周）",
                                "name": "threshold_weeks",
                                "required": True,
                                "data-source": [
                                    {"id": "4", "title": "4周"},
                                    {"id": "6", "title": "6周"},
                                    {"id": "8", "title": "8周"},
                                    {"id": "12", "title": "12周"},
                                    {"id": "18", "title": "18周"},
                                    {"id": "24", "title": "24周"}
                                ]
                            }
                        ]
                    },
                    "terminal": False
                },
                {
                    "id": "RADIUS_SETTING",
                    "title": "搜索范围",
                    "data": [
                        {
                            "type": "number",
                            "name": "radius_km",
                            "label": "搜索半径（公里）",
                            "required": True
                        }
                    ],
                    "layout": {
                        "type": "SingleColumnLayout",
                        "children": [
                            {
                                "type": "TextHeading",
                                "text": "📍 设置搜索范围"
                            },
                            {
                                "type": "TextBody",
                                "text": "我们会在此范围内为您查找医院"
                            },
                            {
                                "type": "Dropdown",
                                "label": "搜索半径（公里）",
                                "name": "radius_km",
                                "required": True,
                                "data-source": [
                                    {"id": "10", "title": "10公里"},
                                    {"id": "15", "title": "15公里"},
                                    {"id": "25", "title": "25公里"},
                                    {"id": "40", "title": "40公里"},
                                    {"id": "60", "title": "60公里"},
                                    {"id": "100", "title": "100公里"}
                                ]
                            }
                        ]
                    },
                    "terminal": False
                },
                {
                    "id": "NOTIFICATION_SETUP",
                    "title": "通知设置",
                    "data": [
                        {
                            "type": "array",
                            "name": "notification_types",
                            "label": "通知类型",
                            "required": True
                        }
                    ],
                    "layout": {
                        "type": "SingleColumnLayout",
                        "children": [
                            {
                                "type": "TextHeading",
                                "text": "🔔 选择通知类型"
                            },
                            {
                                "type": "CheckboxGroup",
                                "label": "通知类型",
                                "name": "notification_types",
                                "required": True,
                                "data-source": [
                                    {"id": "threshold_alerts", "title": "等候时间阈值提醒"},
                                    {"id": "shorter_alternatives", "title": "更短选择提醒"},
                                    {"id": "trend_updates", "title": "趋势更新"},
                                    {"id": "weekly_summary", "title": "每周总结"}
                                ]
                            }
                        ]
                    },
                    "terminal": False
                },
                {
                    "id": "CONFIRMATION",
                    "title": "设置确认",
                    "layout": {
                        "type": "SingleColumnLayout",
                        "children": [
                            {
                                "type": "TextHeading",
                                "text": "✅ 设置完成！"
                            },
                            {
                                "type": "TextBody",
                                "text": "您的个人偏好已保存，我们将开始为您提供个性化的NHS等候时间提醒。"
                            }
                        ]
                    },
                    "terminal": True
                }
            ]
        }
    
    def _create_comparison_flow(self) -> Dict:
        """创建医院比较Flow"""
        return {
            "version": "3.0",
            "data_api_version": "3.0",
            "routing_model": {
                "HOSPITAL_COMPARISON": ["RESULTS_DISPLAY"]
            },
            "screens": [
                {
                    "id": "HOSPITAL_COMPARISON",
                    "title": "医院等候时间对比",
                    "layout": {
                        "type": "SingleColumnLayout",
                        "children": [
                            {
                                "type": "TextHeading",
                                "text": "🏥 您附近的医院对比"
                            },
                            {
                                "type": "TextBody",
                                "text": "基于您的位置和专科偏好"
                            }
                        ]
                    },
                    "terminal": True
                }
            ]
        }
    
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
            
            # 获取附近医院信息（使用地理服务）
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
        """获取附近医院的等候时间数据（使用地理服务）"""
        try:
            # 使用地理服务获取附近医院
            nearby_hospitals = self.geo_service.get_nearby_hospitals_from_db(
                postcode, specialty, radius_km, self.db_path
            )
            
            # 为每个医院计算推荐评分
            for hospital in nearby_hospitals:
                hospital['recommendation_score'] = self._calculate_recommendation_score(
                    hospital.get('waiting_time_weeks', 0),
                    hospital.get('patient_count', 0),
                    hospital.get('distance_km', 0)
                )
            
            # 按推荐评分排序
            nearby_hospitals.sort(key=lambda x: x.get('recommendation_score', 0), reverse=True)
            
            return nearby_hospitals[:10]  # 返回前10个推荐医院
            
        except Exception as e:
            logger.error(f"获取附近医院失败: {e}")
            return []
    
    def _calculate_recommendation_score(self, waiting_weeks: int, patients_waiting: int, distance_km: float) -> float:
        """计算推荐评分（考虑等候时间、患者数量和距离）"""
        if waiting_weeks <= 0:
            return 5.0
        
        # 基础评分：等候时间越短，评分越高
        base_score = max(0, 5.0 - (waiting_weeks / 10))
        
        # 考虑患者数量
        if patients_waiting > 500:
            base_score -= 0.5
        elif patients_waiting < 100:
            base_score += 0.5
        
        # 考虑距离：距离越近，评分越高
        if distance_km:
            if distance_km <= 10:
                base_score += 0.5
            elif distance_km <= 25:
                base_score += 0.2
            elif distance_km > 50:
                base_score -= 0.3
        
        return round(max(0, min(5.0, base_score)), 1)
    
    def _create_confirmation_message(self, postcode: str, specialty: str, threshold_weeks: int, 
                                   radius_km: int, nearby_hospitals: List[Dict]) -> str:
        """创建确认消息"""
        specialty_names = {
            'cardiology': '心脏科',
            'orthopaedics': '骨科',
            'general_surgery': '普通外科',
            'dermatology': '皮肤科',
            'ophthalmology': '眼科',
            'ent': '耳鼻喉科',
            'gynaecology': '妇科',
            'urology': '泌尿科'
        }
        
        specialty_chinese = specialty_names.get(specialty, specialty)
        
        message = f"""✅ **设置完成！**

📍 **您的位置**: {postcode}
🩺 **关注专科**: {specialty_chinese}
⏰ **提醒阈值**: {threshold_weeks} 周
📏 **搜索范围**: {radius_km} 公里

🏥 **找到 {len(nearby_hospitals)} 家附近医院**"""

        if nearby_hospitals:
            message += "\n\n**🎯 最佳推荐**:"
            best_hospital = nearby_hospitals[0]
            message += f"\n🏆 {best_hospital.get('org_name', 'Unknown')}"
            message += f"\n⏰ 等候时间: {best_hospital.get('waiting_time_weeks', 0)} 周"
            if best_hospital.get('distance_km'):
                message += f"\n📍 距离: {best_hospital['distance_km']} 公里"
            message += f"\n⭐ 推荐评分: {best_hospital.get('recommendation_score', 0)}/5"
        
        message += "\n\n💡 我们会定期检查等候时间变化并及时提醒您！"
        
        return message
    
    def _send_hospital_comparison(self, user_phone: str, hospitals: List[Dict]):
        """发送医院对比信息"""
        if not hospitals:
            return
        
        comparison_message = "🏥 **您附近的医院对比**\n\n"
        
        for i, hospital in enumerate(hospitals[:5], 1):
            comparison_message += f"**{i}. {hospital.get('org_name', 'Unknown')}**\n"
            comparison_message += f"   ⏰ 等候: {hospital.get('waiting_time_weeks', 0)} 周\n"
            if hospital.get('distance_km'):
                comparison_message += f"   📍 距离: {hospital['distance_km']} 公里\n"
            comparison_message += f"   👥 等候人数: {hospital.get('patient_count', 0)}\n"
            comparison_message += f"   ⭐ 评分: {hospital.get('recommendation_score', 0)}/5\n\n"
        
        comparison_message += "💡 **提示**: 评分综合考虑了等候时间、距离和医院容量"
        
        # 这里应该通过WhatsApp发送消息
        logger.info(f"Hospital comparison for {user_phone}: {comparison_message}")
    
    def update_user_preferences(self, user_phone: str, updates: Dict) -> bool:
        """更新用户偏好"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 构建更新查询
            update_fields = []
            update_values = []
            
            for field, value in updates.items():
                if field in ['postcode', 'specialty', 'threshold_weeks', 'radius_km', 'notification_types']:
                    update_fields.append(f"{field} = ?")
                    if field == 'notification_types' and isinstance(value, list):
                        update_values.append(json.dumps(value))
                    else:
                        update_values.append(value)
            
            if not update_fields:
                return False
            
            update_values.append(datetime.now())
            update_values.append(user_phone)
            
            query = f'''
            UPDATE user_preferences 
            SET {', '.join(update_fields)}, updated_at = ?
            WHERE phone_number = ?
            '''
            
            cursor.execute(query, update_values)
            
            if cursor.rowcount > 0:
                conn.commit()
                conn.close()
                logger.info(f"用户偏好更新成功: {user_phone}")
                return True
            else:
                conn.close()
                return False
            
        except Exception as e:
            logger.error(f"更新用户偏好失败: {e}")
            return False
    
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
    
    def delete_user_preferences(self, user_phone: str) -> bool:
        """删除用户偏好"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            UPDATE user_preferences SET status = 'inactive', updated_at = ?
            WHERE phone_number = ?
            ''', (datetime.now(), user_phone))
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            if success:
                logger.info(f"用户偏好已删除: {user_phone}")
            
            return success
            
        except Exception as e:
            logger.error(f"删除用户偏好失败: {e}")
            return False
    
    def log_user_interaction(self, user_id: str, interaction_type: str, interaction_data: Dict):
        """记录用户交互"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO user_interactions (user_id, interaction_type, interaction_data)
            VALUES (?, ?, ?)
            ''', (user_id, interaction_type, json.dumps(interaction_data)))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"记录用户交互失败: {e}")
    
    def get_user_interaction_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """获取用户交互历史"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT interaction_type, interaction_data, created_at
            FROM user_interactions 
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            ''', (user_id, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            interactions = []
            for row in rows:
                interactions.append({
                    'interaction_type': row[0],
                    'interaction_data': json.loads(row[1]) if row[1] else {},
                    'created_at': row[2]
                })
            
            return interactions
            
        except Exception as e:
            logger.error(f"获取用户交互历史失败: {e}")
            return []
    
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
    
    def get_usage_statistics(self) -> Dict:
        """获取使用统计"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 总用户数
            cursor.execute('SELECT COUNT(*) FROM user_preferences')
            total_users = cursor.fetchone()[0]
            
            # 活跃用户数
            cursor.execute('SELECT COUNT(*) FROM user_preferences WHERE status = "active"')
            active_users = cursor.fetchone()[0]
            
            # 专科分布
            cursor.execute('''
            SELECT specialty, COUNT(*) FROM user_preferences 
            WHERE status = "active" GROUP BY specialty
            ''')
            specialty_distribution = dict(cursor.fetchall())
            
            # 地区分布（按邮编前缀）
            cursor.execute('''
            SELECT SUBSTR(postcode, 1, 2) as postcode_prefix, COUNT(*) 
            FROM user_preferences 
            WHERE status = "active" AND postcode IS NOT NULL
            GROUP BY postcode_prefix
            ORDER BY COUNT(*) DESC
            LIMIT 10
            ''')
            regional_distribution = dict(cursor.fetchall())
            
            conn.close()
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'specialty_distribution': specialty_distribution,
                'regional_distribution': regional_distribution,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取使用统计失败: {e}")
            return {'error': str(e)} 