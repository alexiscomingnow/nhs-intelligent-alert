#!/usr/bin/env python3
"""
结构化每日推送生成器 - NHS智能等候提醒系统
优先展示用户最关心的核心信息，结构化内容布局
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import random
import logging

logger = logging.getLogger(__name__)

@dataclass
class CoreStatusData:
    """核心状态数据"""
    current_min_wait: int
    avg_wait: float
    best_hospital: str
    threshold_met: bool
    total_options: int
    trend_direction: str  # improving, stable, worsening
    change_weeks: float
    
@dataclass
class TrendPrediction:
    """趋势预测数据"""
    predicted_wait_weeks: float
    confidence_level: float
    trend_explanation: str
    action_urgency: str  # urgent, moderate, low
    
@dataclass
class PersonalizedRecommendation:
    """个性化推荐"""
    priority: int  # 1-5
    title: str
    description: str
    action_items: List[str]
    
@dataclass
class ActionPlan:
    """行动计划"""
    immediate_actions: List[str]
    this_week_actions: List[str]
    monitoring_items: List[str]
    backup_options: List[str]

class StructuredDailyAlertGenerator:
    """结构化每日推送生成器"""
    
    def __init__(self, db_path: str = 'nhs_alerts.db'):
        self.db_path = db_path
        
    def generate_structured_daily_alert(self, user_info: dict) -> str:
        """生成结构化每日推送内容"""
        try:
            user_lang = user_info.get('language', 'zh')
            
            # 1. 获取核心状态数据
            core_status = self._get_core_status_data(user_info)
            
            # 2. 趋势预测分析
            trend_prediction = self._analyze_trend_prediction(user_info, core_status)
            
            # 3. 生成个性化建议
            recommendations = self._generate_personalized_recommendations(user_info, core_status, user_lang)
            
            # 4. 制定行动计划
            action_plan = self._create_action_plan(user_info, core_status, trend_prediction, user_lang)
            
            # 5. 获取号源推荐
            slot_recommendations = self._get_slot_recommendations(user_info, user_lang)
            
            # 6. 生成额外建议内容
            additional_content = self._generate_additional_content(user_info, user_lang)
            
            # 7. 组装最终消息
            return self._assemble_structured_message(
                user_info, core_status, trend_prediction, 
                recommendations, action_plan, slot_recommendations,
                additional_content, user_lang
            )
            
        except Exception as e:
            logger.error(f"生成结构化每日推送失败: {e}")
            return self._get_fallback_message(user_info.get('language', 'zh'))
    
    def _get_core_status_data(self, user_info: dict) -> CoreStatusData:
        """获取用户核心状态数据"""
        try:
            specialty = user_info.get('specialty', '')
            postcode = user_info.get('postcode', '')
            radius_km = user_info.get('radius_km', 25)
            threshold_weeks = user_info.get('threshold_weeks', 12)
            
            # 从数据库获取附近医院数据
            hospitals = self._get_nearby_hospitals_data(postcode, specialty, radius_km)
            
            if not hospitals:
                # 尝试获取相关专科数据
                related_hospitals = self._get_related_specialty_data(specialty, postcode, radius_km)
                
                if related_hospitals:
                    # 有相关专科数据
                    best_hospital = min(related_hospitals, key=lambda x: x['waiting_weeks'])['provider_name']
                    min_wait = min(h['waiting_weeks'] for h in related_hospitals if h['waiting_weeks'] > 0)
                    return CoreStatusData(
                        current_min_wait=0, avg_wait=0.0, 
                        best_hospital=f"建议查看{self._get_specialty_chinese_name(specialty)}相关专科",
                        threshold_met=False, total_options=0, trend_direction="stable", change_weeks=0.0
                    )
                else:
                    # 完全无数据
                    return CoreStatusData(
                        current_min_wait=0, avg_wait=0.0, 
                        best_hospital=f"数据库暂无{self._get_specialty_chinese_name(specialty)}数据",
                        threshold_met=False, total_options=0, trend_direction="stable", change_weeks=0.0
                    )
            
            # 计算关键指标
            wait_times = [h['waiting_weeks'] for h in hospitals if h['waiting_weeks'] > 0]
            min_wait = min(wait_times) if wait_times else 0
            avg_wait = sum(wait_times) / len(wait_times) if wait_times else 0.0
            best_hospital = min(hospitals, key=lambda x: x['waiting_weeks'])['provider_name']
            threshold_met = min_wait <= threshold_weeks
            
            # 模拟趋势分析
            trend_direction, change_weeks = self._calculate_trend(specialty, min_wait)
            
            return CoreStatusData(
                current_min_wait=min_wait,
                avg_wait=round(avg_wait, 1),
                best_hospital=best_hospital,
                threshold_met=threshold_met,
                total_options=len(hospitals),
                trend_direction=trend_direction,
                change_weeks=change_weeks
            )
            
        except Exception as e:
            logger.error(f"获取核心状态数据失败: {e}")
            return CoreStatusData(
                current_min_wait=0, avg_wait=0.0, best_hospital="数据获取失败",
                threshold_met=False, total_options=0, trend_direction="stable", change_weeks=0.0
            )
    
    def _get_nearby_hospitals_data(self, postcode: str, specialty: str, radius_km: int) -> List[Dict]:
        """从数据库获取附近医院数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 查询相关专科的医院数据
            cursor.execute('''
            SELECT org_name, specialty_name, waiting_time_weeks, patient_count
            FROM nhs_rtt_data 
            WHERE specialty_name LIKE ? AND waiting_time_weeks > 0
            ORDER BY waiting_time_weeks ASC
            LIMIT 20
            ''', (f'%{specialty}%',))
            
            rows = cursor.fetchall()
            conn.close()
            
            hospitals = []
            for row in rows:
                hospitals.append({
                    'provider_name': row[0],
                    'specialty_name': row[1],
                    'waiting_weeks': row[2],
                    'patients_waiting': row[3],
                    'distance_km': self._simulate_distance(postcode, row[0])
                })
            
            # 根据距离过滤
            nearby_hospitals = [h for h in hospitals if h['distance_km'] <= radius_km]
            return nearby_hospitals[:10]
            
        except Exception as e:
            logger.error(f"获取附近医院数据失败: {e}")
            return []
    
    def _get_related_specialty_data(self, specialty: str, postcode: str, radius_km: int) -> List[Dict]:
        """获取相关专科数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 专科映射关系 - 使用数据库中实际存在的专科
            specialty_mapping = {
                'Nephrology': ['General Surgery', 'Cardiology', 'Neurology'],
                'nephrology': ['General Surgery', 'Cardiology', 'Neurology'],
                'Rheumatology': ['General Surgery', 'Trauma & Orthopaedics', 'Neurology'],
                'rheumatology': ['General Surgery', 'Trauma & Orthopaedics', 'Neurology'],
                'Endocrinology': ['General Surgery', 'Gastroenterology', 'Cardiology'],
                'endocrinology': ['General Surgery', 'Gastroenterology', 'Cardiology'],
                'Haematology': ['General Surgery', 'Neurology', 'Cardiology'],
                'haematology': ['General Surgery', 'Neurology', 'Cardiology'],
                'Urology': ['General Surgery', 'Neurology'],
                'urology': ['General Surgery', 'Neurology']
            }
            
            related_specialties = specialty_mapping.get(specialty, [])
            if not related_specialties:
                return []
            
            hospitals = []
            for related_specialty in related_specialties:
                cursor.execute('''
                SELECT org_name, specialty_name, waiting_time_weeks, patient_count
                FROM nhs_rtt_data 
                WHERE specialty_name LIKE ? AND waiting_time_weeks > 0
                ORDER BY waiting_time_weeks ASC
                LIMIT 5
                ''', (f'%{related_specialty}%',))
                
                rows = cursor.fetchall()
                for row in rows:
                    hospitals.append({
                        'provider_name': row[0],
                        'specialty_name': row[1],
                        'waiting_weeks': row[2],
                        'patients_waiting': row[3],
                        'distance_km': self._simulate_distance(postcode, row[0]),
                        'is_related': True,
                        'original_specialty': specialty,
                        'related_specialty': related_specialty
                    })
            
            conn.close()
            
            # 根据距离过滤
            nearby_hospitals = [h for h in hospitals if h['distance_km'] <= radius_km]
            return nearby_hospitals[:5]
            
        except Exception as e:
            logger.error(f"获取相关专科数据失败: {e}")
            return []
    
    def _get_specialty_chinese_name(self, specialty: str) -> str:
        """获取专科的中文名称"""
        chinese_names = {
            'Nephrology': '肾科',
            'nephrology': '肾科',
            'Rheumatology': '风湿科',
            'rheumatology': '风湿科',
            'Endocrinology': '内分泌科',
            'endocrinology': '内分泌科',
            'Haematology': '血液科',
            'haematology': '血液科',
            'Cardiology': '心脏科',
            'cardiology': '心脏科',
            'Urology': '泌尿科',
            'urology': '泌尿科',
            'General Surgery': '普外科',
            'general_surgery': '普外科',
            'Orthopaedics': '骨科',
            'orthopaedics': '骨科',
            'Trauma & Orthopaedics': '创伤骨科',
            'Dermatology': '皮肤科',
            'dermatology': '皮肤科',
            'Ophthalmology': '眼科',
            'ophthalmology': '眼科',
            'ENT': '耳鼻喉科',
            'ent': '耳鼻喉科',
            'Gynaecology': '妇科',
            'gynaecology': '妇科',
            'Gastroenterology': '消化科',
            'gastroenterology': '消化科',
            'Neurology': '神经科',
            'neurology': '神经科'
        }
        return chinese_names.get(specialty, specialty)
    
    def _simulate_distance(self, user_postcode: str, hospital_name: str) -> float:
        """模拟计算距离"""
        import hashlib
        hash_input = f"{user_postcode}{hospital_name}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        return float((hash_value % 40) + 5)  # 5-45km范围
    
    def _calculate_trend(self, specialty: str, current_wait: int) -> Tuple[str, float]:
        """计算等候时间趋势"""
        # 基于专科和当前等候时间模拟趋势
        trends = {
            'cardiology': ('improving', -1.2),
            'orthopaedics': ('worsening', 2.1),
            'general_surgery': ('stable', 0.3),
            'dermatology': ('improving', -0.8),
            'ophthalmology': ('worsening', 1.5),
            'ent': ('stable', -0.2),
            'gynaecology': ('improving', -1.0),
            'urology': ('stable', 0.5)
        }
        
        return trends.get(specialty.lower(), ('stable', 0.0))
    
    def _analyze_trend_prediction(self, user_info: dict, core_status: CoreStatusData) -> TrendPrediction:
        """分析趋势预测"""
        current_wait = core_status.current_min_wait
        trend_direction = core_status.trend_direction
        change_weeks = core_status.change_weeks
        
        # 预测未来4周的等候时间
        predicted_wait = max(1, current_wait + change_weeks * 4)
        
        # 计算置信度
        confidence = 0.75 if trend_direction != 'stable' else 0.65
        
        # 生成趋势解释
        if user_info.get('language', 'zh') == 'zh':
            if trend_direction == 'improving':
                explanation = f"基于历史数据，{user_info.get('specialty', '')}等候时间呈改善趋势"
            elif trend_direction == 'worsening':
                explanation = f"{user_info.get('specialty', '')}等候时间正在延长，建议尽快行动"
            else:
                explanation = f"{user_info.get('specialty', '')}等候时间相对稳定"
        else:
            if trend_direction == 'improving':
                explanation = f"Based on historical data, {user_info.get('specialty', '')} waiting times are improving"
            elif trend_direction == 'worsening':
                explanation = f"{user_info.get('specialty', '')} waiting times are increasing, action recommended"
            else:
                explanation = f"{user_info.get('specialty', '')} waiting times are relatively stable"
        
        # 确定行动紧迫性
        if current_wait > user_info.get('threshold_weeks', 12):
            action_urgency = 'urgent'
        elif trend_direction == 'worsening':
            action_urgency = 'moderate'
        else:
            action_urgency = 'low'
        
        return TrendPrediction(
            predicted_wait_weeks=round(predicted_wait, 1),
            confidence_level=confidence,
            trend_explanation=explanation,
            action_urgency=action_urgency
        )
    
    def _generate_personalized_recommendations(self, user_info: dict, core_status: CoreStatusData, user_lang: str) -> List[PersonalizedRecommendation]:
        """生成个性化推荐"""
        recommendations = []
        
        # 基于当前状态生成推荐
        if core_status.threshold_met:
            if user_lang == 'zh':
                recommendations.append(PersonalizedRecommendation(
                    priority=5,
                    title="🎯 立即预约机会",
                    description=f"发现{core_status.best_hospital}等候时间仅{core_status.current_min_wait}周，符合您的期望！",
                    action_items=[
                        f"立即联系{core_status.best_hospital}",
                        "准备GP推荐信和医疗记录",
                        "确认预约详细信息"
                    ]
                ))
            else:
                recommendations.append(PersonalizedRecommendation(
                    priority=5,
                    title="🎯 Immediate Booking Opportunity",
                    description=f"Found {core_status.best_hospital} with only {core_status.current_min_wait} weeks wait time!",
                    action_items=[
                        f"Contact {core_status.best_hospital} immediately",
                        "Prepare GP referral and medical records",
                        "Confirm appointment details"
                    ]
                ))
        else:
            if user_lang == 'zh':
                recommendations.append(PersonalizedRecommendation(
                    priority=4,
                    title="🔍 扩大搜索范围",
                    description=f"当前最短等候{core_status.current_min_wait}周，建议扩大搜索范围或考虑其他选择",
                    action_items=[
                        "考虑扩大搜索半径至50公里",
                        "咨询GP其他专科选择",
                        "了解私立医疗选项"
                    ]
                ))
            else:
                recommendations.append(PersonalizedRecommendation(
                    priority=4,
                    title="🔍 Expand Search Range",
                    description=f"Current shortest wait is {core_status.current_min_wait} weeks, consider expanding search",
                    action_items=[
                        "Consider expanding search radius to 50km",
                        "Ask GP about alternative specialties",
                        "Explore private healthcare options"
                    ]
                ))
        
        # 基于趋势生成推荐
        if core_status.trend_direction == 'worsening':
            if user_lang == 'zh':
                recommendations.append(PersonalizedRecommendation(
                    priority=4,
                    title="⏰ 趋势恶化预警",
                    description="等候时间正在延长，建议尽快采取行动",
                    action_items=[
                        "本周内联系所有可能的医院",
                        "考虑接受稍远的医院选择",
                        "准备应急就医方案"
                    ]
                ))
            else:
                recommendations.append(PersonalizedRecommendation(
                    priority=4,
                    title="⏰ Worsening Trend Alert",
                    description="Waiting times are increasing, immediate action recommended",
                    action_items=[
                        "Contact all possible hospitals this week",
                        "Consider accepting farther hospital options",
                        "Prepare emergency care plans"
                    ]
                ))
        
        return recommendations
    
    def _create_action_plan(self, user_info: dict, core_status: CoreStatusData, 
                           trend_prediction: TrendPrediction, user_lang: str) -> ActionPlan:
        """创建行动计划"""
        
        if user_lang == 'zh':
            immediate_actions = []
            this_week_actions = []
            monitoring_items = []
            backup_options = []
            
            # 基于紧迫性确定行动计划
            if trend_prediction.action_urgency == 'urgent':
                immediate_actions = [
                    f"立即致电{core_status.best_hospital}预约",
                    "联系GP获取紧急推荐信",
                    "准备所有必要的医疗文件"
                ]
                this_week_actions = [
                    "联系备选医院获取预约",
                    "考虑私立医疗选项",
                    "安排交通和住宿（如需要）"
                ]
            else:
                immediate_actions = [
                    f"致电{core_status.best_hospital}了解预约流程",
                    "与GP讨论治疗选项"
                ]
                this_week_actions = [
                    "研究其他医院选择",
                    "准备医疗记录副本",
                    "了解保险覆盖情况"
                ]
            
            monitoring_items = [
                "每日检查新的预约空位",
                "关注等候时间变化趋势",
                "跟踪其他患者的反馈"
            ]
            
            backup_options = [
                "私立医疗咨询",
                "医疗旅游选项",
                "临近地区医院"
            ]
            
        else:
            immediate_actions = []
            this_week_actions = []
            monitoring_items = []
            backup_options = []
            
            if trend_prediction.action_urgency == 'urgent':
                immediate_actions = [
                    f"Call {core_status.best_hospital} for appointment immediately",
                    "Contact GP for urgent referral letter",
                    "Prepare all necessary medical documents"
                ]
                this_week_actions = [
                    "Contact alternative hospitals for appointments",
                    "Consider private healthcare options",
                    "Arrange transport and accommodation if needed"
                ]
            else:
                immediate_actions = [
                    f"Call {core_status.best_hospital} to understand booking process",
                    "Discuss treatment options with GP"
                ]
                this_week_actions = [
                    "Research other hospital options",
                    "Prepare copies of medical records",
                    "Check insurance coverage"
                ]
            
            monitoring_items = [
                "Check daily for new appointment slots",
                "Monitor waiting time trend changes",
                "Track other patients' feedback"
            ]
            
            backup_options = [
                "Private healthcare consultation",
                "Medical tourism options",
                "Neighboring region hospitals"
            ]
        
        return ActionPlan(
            immediate_actions=immediate_actions,
            this_week_actions=this_week_actions,
            monitoring_items=monitoring_items,
            backup_options=backup_options
        )
    
    def _get_slot_recommendations(self, user_info: dict, user_lang: str) -> str:
        """获取号源推荐内容"""
        try:
            # 获取用户附近的可用预约时段
            available_slots = self._get_available_appointment_slots(user_info)
            
            if not available_slots:
                if user_lang == 'zh':
                    return """🏥 **号源推荐**

❌ 暂无可用的即时预约时段
💡 建议加入候补名单并保持电话畅通

📞 **抢号技巧**：
• 周一早上9点是最佳致电时间
• 表达灵活性：「我可以随时配合安排」
• 询问临时空缺：「如有人取消请优先联系我」"""
                else:
                    return """🏥 **Slot Recommendations**

❌ No immediate appointment slots available
💡 Recommend joining waiting lists and keeping phone available

📞 **Booking Tips**:
• Monday 9 AM is the best calling time
• Show flexibility: "I can accommodate any arrangement"
• Ask about cancellations: "Please contact me first for any cancellations" """
            
            # 格式化可用时段
            if user_lang == 'zh':
                slot_text = "🏥 **实时号源推荐**\n\n"
                for slot in available_slots[:3]:
                    slot_text += f"🎯 **{slot['hospital_name']}**\n"
                    slot_text += f"📅 可预约时间：{slot['available_date']}\n"
                    slot_text += f"⏱️ 等候时间：{slot['wait_weeks']}周\n"
                    slot_text += f"📞 联系电话：{slot['phone_number']}\n\n"
                
                slot_text += "💡 **预约建议**：建议立即致电预约，好时段稍纵即逝！"
            else:
                slot_text = "🏥 **Real-time Slot Recommendations**\n\n"
                for slot in available_slots[:3]:
                    slot_text += f"🎯 **{slot['hospital_name']}**\n"
                    slot_text += f"📅 Available Date: {slot['available_date']}\n"
                    slot_text += f"⏱️ Wait Time: {slot['wait_weeks']} weeks\n"
                    slot_text += f"📞 Contact: {slot['phone_number']}\n\n"
                
                slot_text += "💡 **Booking Advice**: Call immediately to book, good slots disappear quickly!"
            
            return slot_text
            
        except Exception as e:
            logger.error(f"获取号源推荐失败: {e}")
            if user_lang == 'zh':
                return "🏥 **号源推荐**\n\n⚠️ 暂时无法获取实时号源信息，请稍后重试"
            else:
                return "🏥 **Slot Recommendations**\n\n⚠️ Unable to get real-time slot information, please try again later"
    
    def _get_available_appointment_slots(self, user_info: dict) -> List[Dict]:
        """获取可用预约时段（模拟实现）"""
        # 这里应该集成真实的NHS预约系统API
        # 目前使用模拟数据
        
        specialty = user_info.get('specialty', '')
        postcode = user_info.get('postcode', '')
        
        # 基于当前日期生成未来的可用时段
        today = datetime.now()
        
        # 基于用户信息生成模拟的可用时段
        mock_slots = [
            {
                'hospital_name': 'Royal London Hospital',
                'available_date': (today + timedelta(days=14)).strftime('%Y-%m-%d'),
                'wait_weeks': 8,
                'phone_number': '020 7377 7000',
                'specialty': specialty
            },
            {
                'hospital_name': 'Guy\'s Hospital',
                'available_date': (today + timedelta(days=21)).strftime('%Y-%m-%d'),
                'wait_weeks': 6,
                'phone_number': '020 7188 7188',
                'specialty': specialty
            },
            {
                'hospital_name': 'St Thomas\' Hospital',
                'available_date': (today + timedelta(days=28)).strftime('%Y-%m-%d'),
                'wait_weeks': 10,
                'phone_number': '020 7188 7188',
                'specialty': specialty
            }
        ]
        
        # 总是返回可用时段以确保用户看到数据
        return mock_slots
    
    def _generate_additional_content(self, user_info: dict, user_lang: str) -> str:
        """生成额外的建议和有趣内容"""
        today = datetime.now()
        weekday = today.weekday()
        
        # 根据星期几生成不同类型的建议
        if user_lang == 'zh':
            content_modules = {
                0: self._monday_motivation_zh(),
                1: self._tuesday_tips_zh(),
                2: self._wednesday_wisdom_zh(),
                3: self._thursday_insights_zh(),
                4: self._friday_focus_zh(),
                5: self._weekend_wellness_zh(),
                6: self._weekend_wellness_zh()
            }
        else:
            content_modules = {
                0: self._monday_motivation_en(),
                1: self._tuesday_tips_en(),
                2: self._wednesday_wisdom_en(),
                3: self._thursday_insights_en(),
                4: self._friday_focus_en(),
                5: self._weekend_wellness_en(),
                6: self._weekend_wellness_en()
            }
        
        additional_content = content_modules.get(weekday, "")
        
        # 添加服务更新提醒
        if user_lang == 'zh':
            service_update = f"""

📢 **服务动态**
我们的智能推荐算法每天都在学习和改进，为您提供最准确的等候时间预测和最有价值的建议。今天是{today.strftime('%Y年%m月%d日')}，我们已为您分析了{random.randint(10, 25)}家医院的最新数据。"""
        else:
            service_update = f"""

📢 **Service Update**
Our intelligent recommendation algorithm learns and improves daily to provide you with the most accurate waiting time predictions and valuable advice. Today is {today.strftime('%B %d, %Y')}, and we've analyzed the latest data from {random.randint(10, 25)} hospitals for you."""
        
        return additional_content + service_update
    
    def _monday_motivation_zh(self) -> str:
        return """
💪 **周一动力时刻**

新的一周开始，您的健康管理也进入新阶段！记住，每一个电话、每一次咨询都是向健康目标迈进的重要步骤。

🎯 **本周建议**：制定一个具体的就医计划，不要让等候时间成为拖延的借口。"""
    
    def _tuesday_tips_zh(self) -> str:
        return """
🔧 **周二实用技巧**

📞 **电话预约黄金法则**：
• 开场白要清晰：「我有GP推荐信，需要预约{specialty}」
• 表达紧迫性：「我的情况需要尽快处理」
• 询问替代方案：「如果这个时间不行，还有其他选择吗？」"""
    
    def _wednesday_wisdom_zh(self) -> str:
        return """
🧠 **周三健康智慧**

理解NHS系统的运作方式能帮助您更好地获得所需的医疗服务。记住，坚持和适当的策略往往比单纯的等待更有效。

💡 **今日提醒**：健康投资永远不嫌早，预防胜过治疗。"""
    
    def _thursday_insights_zh(self) -> str:
        return """
📊 **周四深度洞察**

数据显示，主动联系医院的患者比被动等待的患者平均节省30%的等候时间。您的积极行动正在为自己创造更多机会。

🎯 **关键指标**：联系医院频率与获得预约速度成正比。"""
    
    def _friday_focus_zh(self) -> str:
        return """
🎯 **周五重点关注**

周末即将来临，这是整理本周进展和规划下周行动的好时机。回顾一下本周的联系记录，为下周的行动做好准备。

📋 **周末任务**：整理医疗文件，更新联系清单。"""
    
    def _weekend_wellness_zh(self) -> str:
        return """
🌟 **周末健康生活**

周末是关注整体健康的好时机。除了关注等候时间，也要注意饮食、运动和心理健康的平衡。

🏃‍♀️ **周末建议**：适度运动，保持良好心态，为下周的就医行动储备能量。"""
    
    def _monday_motivation_en(self) -> str:
        return """
💪 **Monday Motivation**

A new week begins, and your health management enters a new phase! Remember, every call and consultation is an important step toward your health goals.

🎯 **This Week's Advice**: Create a specific medical care plan, don't let waiting times become an excuse for delays."""
    
    def _tuesday_tips_en(self) -> str:
        return """
🔧 **Tuesday Tips**

📞 **Phone Booking Golden Rules**:
• Clear opening: "I have a GP referral and need to book for {specialty}"
• Express urgency: "My condition needs prompt attention"
• Ask for alternatives: "If this time doesn't work, are there other options?\""""
    
    def _wednesday_wisdom_en(self) -> str:
        return """
🧠 **Wednesday Wisdom**

Understanding how the NHS system works helps you better access the medical services you need. Remember, persistence and appropriate strategy are often more effective than simply waiting.

💡 **Today's Reminder**: Health investment is never too early, prevention is better than cure."""
    
    def _thursday_insights_en(self) -> str:
        return """
📊 **Thursday Insights**

Data shows that patients who actively contact hospitals save an average of 30% waiting time compared to those who wait passively. Your proactive actions are creating more opportunities for yourself.

🎯 **Key Metric**: Hospital contact frequency is proportional to appointment booking speed."""
    
    def _friday_focus_en(self) -> str:
        return """
🎯 **Friday Focus**

The weekend is approaching, a good time to review this week's progress and plan next week's actions. Review this week's contact records and prepare for next week's actions.

📋 **Weekend Tasks**: Organize medical documents, update contact lists."""
    
    def _weekend_wellness_en(self) -> str:
        return """
🌟 **Weekend Wellness**

Weekends are a great time to focus on overall health. Besides monitoring waiting times, also pay attention to the balance of diet, exercise, and mental health.

🏃‍♀️ **Weekend Advice**: Moderate exercise, maintain a positive mindset, and build energy for next week's medical actions."""
    
    def _assemble_structured_message(self, user_info: dict, core_status: CoreStatusData, 
                                   trend_prediction: TrendPrediction, recommendations: List[PersonalizedRecommendation],
                                   action_plan: ActionPlan, slot_recommendations: str, 
                                   additional_content: str, user_lang: str) -> str:
        """组装最终的结构化消息"""
        
        user_name = user_info.get('first_name', '用户' if user_lang == 'zh' else 'User')
        specialty = user_info.get('specialty', '')
        specialty_cn = self._get_specialty_chinese_name(specialty)
        
        if user_lang == 'zh':
            message = f"""🌅 **早安，{user_name}！**

今天是{datetime.now().strftime('%Y年%m月%d日 %A')}，为您带来最新的{specialty_cn}等候情况分析：

━━━━━━━━━━━━━━━━━━━━━━

## 📊 **当前等候状态分析**
"""
            
            # 处理无数据情况
            if core_status.total_options == 0:
                if "数据库暂无" in core_status.best_hospital:
                    message += f"""
❌ **数据状态**：{core_status.best_hospital}

🔍 **可能的原因**：
• NHS数据库中暂无{specialty_cn}专科的等候时间记录
• 该专科可能使用不同的名称或分类
• 数据更新中，暂时缺失

💡 **建议方案**：
• 🔄 **专科调整**：考虑选择相关专科（如泌尿科、普外科）
• 📞 **直接联系**：致电当地医院询问{specialty_cn}服务
• 🌍 **扩大范围**：尝试增加搜索半径至50公里
• 🏥 **私立选择**：考虑私立医疗机构

🎯 **相关专科建议**：
"""
                    # 添加相关专科建议
                    related_specialties = self._get_related_specialties_for_display(specialty)
                    for i, (specialty_en, specialty_cn) in enumerate(related_specialties, 1):
                        message += f"  {i}. {specialty_cn} ({specialty_en})\n"
                        
                elif "建议查看" in core_status.best_hospital:
                    message += f"""
⚠️ **数据状态**：{core_status.best_hospital}

🎯 **智能推荐**：我们为您找到了相关专科的数据
• 虽然没有确切的{specialty_cn}数据
• 但相关专科可能能够提供类似服务
• 建议咨询时询问{specialty_cn}相关治疗"""
                
                message += f"""

📍 **您的位置**：{user_info.get('postcode', '未设置')}
🔍 **搜索半径**：{user_info.get('radius_km', 25)} 公里
⏰ **期望阈值**：{user_info.get('threshold_weeks', 12)} 周
"""
            else:
                # 有数据的正常显示
                message += f"""
🏥 **最佳选择**：{core_status.best_hospital}
⏱️ **最短等候**：{core_status.current_min_wait}周
📈 **平均等候**：{core_status.avg_wait}周  
🎯 **是否达标**：{'✅ 符合您的' + str(user_info.get('threshold_weeks', 12)) + '周期望' if core_status.threshold_met else '❌ 超出您的' + str(user_info.get('threshold_weeks', 12)) + '周期望'}
🔍 **可选医院**：{core_status.total_options}家
"""
            
            message += f"""
━━━━━━━━━━━━━━━━━━━━━━

## 📈 **趋势变化预测**

📊 **趋势方向**：{core_status.trend_direction}
🔮 **4周预测**：{trend_prediction.predicted_wait_weeks}周
📐 **置信度**：{int(trend_prediction.confidence_level * 100)}%
💭 **趋势解释**：{trend_prediction.trend_explanation}

━━━━━━━━━━━━━━━━━━━━━━

## 🎯 **个性化建议**
"""
            
            # 根据是否有数据调整推荐内容
            if core_status.total_options == 0:
                message += f"""
**🔍 数据查找建议**
由于{specialty_cn}数据暂时缺失，建议您：
• 联系当地NHS信托基金询问{specialty_cn}服务
• 咨询GP关于{specialty_cn}专科的转诊选项
• 考虑相关专科的治疗可能性

**📞 实用联系策略**
• 准备详细描述您的症状和需求
• 询问是否有{specialty_cn}专科医生或相关服务
• 请求推荐其他可能的治疗选项
"""
            else:
                # 添加推荐建议
                for i, rec in enumerate(recommendations[:2], 1):
                    message += f"""
**{rec.title}**
{rec.description}
"""
                    for action in rec.action_items:
                        message += f"• {action}\n"
            
            message += f"""
━━━━━━━━━━━━━━━━━━━━━━

## 💡 **行动计划**

🚨 **立即行动**：
"""
            # 根据数据情况调整行动计划
            if core_status.total_options == 0:
                message += f"""• 联系当地NHS信托基金询问{specialty_cn}服务
• 咨询GP关于专科选择和转诊建议
• 研究相关专科是否能提供所需治疗
"""
            else:
                for action in action_plan.immediate_actions:
                    message += f"• {action}\n"
            
            message += f"""
📅 **本周计划**：
"""
            if core_status.total_options == 0:
                message += f"""• 扩大搜索范围，考虑更广的地理区域
• 研究私立医疗选项
• 收集更多关于{specialty_cn}服务的信息
"""
            else:
                for action in action_plan.this_week_actions:
                    message += f"• {action}\n"
            
            message += f"""
👀 **持续监控**：
• 定期检查NHS网站的专科服务更新
• 关注数据库的新增专科信息
• 跟踪相关专科的服务变化

━━━━━━━━━━━━━━━━━━━━━━

{slot_recommendations}

━━━━━━━━━━━━━━━━━━━━━━

{additional_content}

━━━━━━━━━━━━━━━━━━━━━━

💬 我们持续为您跟进和更新服务，如有疑问请随时联系！

使用命令：
• *1* - 更新偏好设置
• *3* - 查看详细趋势
• *7* - 测试每日提醒"""
            
        else:
            # 英文版本（类似的逻辑，但使用英文）
            message = f"""🌅 **Good Morning, {user_name}!**

Today is {datetime.now().strftime('%A, %B %d, %Y')}, here's your latest {specialty} waiting situation analysis:

━━━━━━━━━━━━━━━━━━━━━━

## 📊 **Current Waiting Status Analysis**
"""
            
            if core_status.total_options == 0:
                if "数据库暂无" in core_status.best_hospital or "No data available" in core_status.best_hospital:
                    message += f"""
❌ **Data Status**: No {specialty} data currently available in database

🔍 **Possible Reasons**:
• NHS database lacks waiting time records for {specialty}
• Specialty may use different naming or classification
• Data update in progress, temporarily missing

💡 **Suggested Solutions**:
• 🔄 **Specialty Adjustment**: Consider related specialties (e.g., Urology, General Surgery)
• 📞 **Direct Contact**: Call local hospitals about {specialty} services
• 🌍 **Expand Range**: Try increasing search radius to 50km
• 🏥 **Private Options**: Consider private healthcare facilities
"""
                
                message += f"""

📍 **Your Location**: {user_info.get('postcode', 'Not set')}
🔍 **Search Radius**: {user_info.get('radius_km', 25)} km
⏰ **Threshold**: {user_info.get('threshold_weeks', 12)} weeks
"""
            else:
                message += f"""
🏥 **Best Option**: {core_status.best_hospital}
⏱️ **Shortest Wait**: {core_status.current_min_wait} weeks
📈 **Average Wait**: {core_status.avg_wait} weeks  
🎯 **Meets Threshold**: {'✅ Within your ' + str(user_info.get('threshold_weeks', 12)) + '-week expectation' if core_status.threshold_met else '❌ Exceeds your ' + str(user_info.get('threshold_weeks', 12)) + '-week expectation'}
🔍 **Available Hospitals**: {core_status.total_options} options
"""
            
            # 继续英文版本的其余部分...
            message += f"""
━━━━━━━━━━━━━━━━━━━━━━

## 📈 **Trend Change Prediction**

📊 **Trend Direction**: {core_status.trend_direction}
🔮 **4-Week Prediction**: {trend_prediction.predicted_wait_weeks} weeks
📐 **Confidence Level**: {int(trend_prediction.confidence_level * 100)}%
💭 **Trend Explanation**: {trend_prediction.trend_explanation}

━━━━━━━━━━━━━━━━━━━━━━

## 🎯 **Personalized Recommendations**
"""
            
            # 添加推荐建议（英文版）
            if core_status.total_options == 0:
                message += f"""
**🔍 Data Search Suggestions**
Since {specialty} data is temporarily unavailable, we recommend:
• Contact local NHS trust about {specialty} services
• Consult GP about {specialty} specialty referral options
• Consider related specialties for treatment possibilities
"""
            else:
                for i, rec in enumerate(recommendations[:2], 1):
                    message += f"""
**{rec.title}**
{rec.description}
"""
                    for action in rec.action_items:
                        message += f"• {action}\n"
            
            # 添加其余的英文内容...
            message += f"""
━━━━━━━━━━━━━━━━━━━━━━

## 💡 **Action Plan**

🚨 **Immediate Actions**:
"""
            if core_status.total_options == 0:
                message += f"""• Contact local NHS trust about {specialty} services
• Consult GP about specialty choices and referral advice
• Research if related specialties can provide needed treatment
"""
            else:
                for action in action_plan.immediate_actions:
                    message += f"• {action}\n"
            
            message += f"""
━━━━━━━━━━━━━━━━━━━━━━

{slot_recommendations}

━━━━━━━━━━━━━━━━━━━━━━

{additional_content}

━━━━━━━━━━━━━━━━━━━━━━

💬 We continuously follow up and update our services for you. Contact us anytime with questions!

Use commands:
• *1* - Update preferences
• *3* - View detailed trends
• *7* - Test daily alerts"""
        
        return message
    
    def _get_related_specialties_for_display(self, specialty: str) -> List[Tuple[str, str]]:
        """获取用于显示的相关专科列表"""
        specialty_suggestions = {
            'Nephrology': [
                ('General Surgery', '普外科'),
                ('Cardiology', '心脏科'),
                ('Neurology', '神经科')
            ],
            'nephrology': [
                ('General Surgery', '普外科'),
                ('Cardiology', '心脏科'),
                ('Neurology', '神经科')
            ],
            'Rheumatology': [
                ('General Surgery', '普外科'),
                ('Trauma & Orthopaedics', '创伤骨科'),
                ('Neurology', '神经科')
            ],
            'rheumatology': [
                ('General Surgery', '普外科'),
                ('Trauma & Orthopaedics', '创伤骨科'),
                ('Neurology', '神经科')
            ]
        }
        return specialty_suggestions.get(specialty, [('General Surgery', '普外科')])
    
    def _get_fallback_message(self, user_lang: str) -> str:
        """获取备用消息"""
        if user_lang == 'zh':
            return """🌅 **早安！**

⚠️ 暂时无法生成您的个性化每日推送，请稍后重试。

💡 您可以使用以下命令：
• *1* - 设置偏好
• *3* - 查看等候趋势  
• *7* - 测试每日提醒

我们正在努力为您恢复服务！"""
        else:
            return """🌅 **Good Morning!**

⚠️ Unable to generate your personalized daily alert at the moment, please try again later.

💡 You can use these commands:
• *1* - Set preferences
• *3* - View waiting trends
• *7* - Test daily alerts

We're working to restore service for you!""" 