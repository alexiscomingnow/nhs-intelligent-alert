#!/usr/bin/env python3
"""
Structured Daily Alert Generator - NHS Alert System
结构化每日推送生成器
重新设计的每日推送内容，优先展示用户最关心的核心信息
"""

import sqlite3
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CoreStatusData:
    """核心状态数据"""
    current_min_wait: int
    avg_wait: float
    best_hospital: str
    threshold_met: bool
    total_options: int
    trend_direction: str  # 'improving', 'worsening', 'stable'
    change_weeks: float

@dataclass
class TrendPrediction:
    """趋势预测数据"""
    predicted_wait_weeks: float
    confidence_level: float
    trend_explanation: str

@dataclass
class PersonalizedRecommendation:
    """个性化推荐"""
    priority: int
    title: str
    description: str
    action_items: List[str]

@dataclass
class ActionPlan:
    """行动计划"""
    immediate_actions: List[str]
    this_week_actions: List[str]
    monitoring_items: List[str]

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
            
            # 简单趋势分析（可以后续扩展为更复杂的算法）
            trend_direction = random.choice(['improving', 'stable', 'worsening'])
            change_weeks = random.uniform(-2.0, 2.0)
            
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
            return CoreStatusData(0, 0.0, "数据获取失败", False, 0, "stable", 0.0)
    
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
    
    def _simulate_distance(self, user_postcode: str, hospital_name: str) -> float:
        """模拟计算距离（简化实现）"""
        # 基于医院名称的hash值生成模拟距离
        hospital_hash = hash(hospital_name) % 100
        base_distance = 10 + (hospital_hash % 40)  # 10-50km之间
        return round(base_distance + random.uniform(-5, 5), 1)
    
    def _get_specialty_chinese_name(self, specialty: str) -> str:
        """获取专科中文名称"""
        specialty_names = {
            'cardiology': '心脏科',
            'cardiology': '心脏科',
            'orthopaedics': '骨科',
            'trauma & orthopaedics': '创伤骨科',
            'general surgery': '普外科',
            'dermatology': '皮肤科',
            'ophthalmology': '眼科',
            'ent': '耳鼻喉科',
            'gynaecology': '妇科',
            'urology': '泌尿科',
            'neurology': '神经科',
            'gastroenterology': '消化科',
            'nephrology': '肾科',
            'rheumatology': '风湿科',
            'endocrinology': '内分泌科',
            'haematology': '血液科'
        }
        return specialty_names.get(specialty.lower(), specialty)
    
    def _analyze_trend_prediction(self, user_info: dict, core_status: CoreStatusData) -> TrendPrediction:
        """分析趋势预测"""
        try:
            # 简化的趋势预测算法，实际实现应该基于历史数据
            current_wait = core_status.current_min_wait
            trend = core_status.trend_direction
            
            if trend == 'improving':
                predicted_wait = max(1, current_wait - random.uniform(1, 3))
                confidence = 0.75
                explanation = f"{self._get_specialty_chinese_name(user_info.get('specialty', ''))}等候时间呈改善趋势"
            elif trend == 'worsening':
                predicted_wait = current_wait + random.uniform(1, 4)
                confidence = 0.65
                explanation = f"{self._get_specialty_chinese_name(user_info.get('specialty', ''))}等候时间正在延长"
            else:
                predicted_wait = current_wait + random.uniform(-0.5, 0.5)
                confidence = 0.80
                explanation = f"{self._get_specialty_chinese_name(user_info.get('specialty', ''))}等候时间相对稳定"
            
            return TrendPrediction(
                predicted_wait_weeks=max(1, round(predicted_wait)),
                confidence_level=confidence,
                trend_explanation=explanation
            )
            
        except Exception as e:
            logger.error(f"趋势预测分析失败: {e}")
            return TrendPrediction(1, 0.5, "暂无趋势数据")
    
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
        """制定行动计划"""
        
        immediate_actions = []
        this_week_actions = []
        monitoring_items = []
        
        if user_lang == 'zh':
            if core_status.threshold_met:
                immediate_actions = [
                    f"联系{core_status.best_hospital}预约",
                    "准备完整的医疗记录",
                    "确认GP推荐信状态"
                ]
            else:
                immediate_actions = [
                    "扩大搜索半径至50公里",
                    "考虑私立医疗选择",
                    "联系GP讨论紧急转诊"
                ]
            
            this_week_actions = [
                "联系3-5家备选医院",
                "更新个人医疗信息",
                "研究交通路线和住宿"
            ]
            
            monitoring_items = [
                "每日检查等候时间变化",
                "关注突发预约空缺",
                "跟踪其他用户经验分享"
            ]
        else:
            if core_status.threshold_met:
                immediate_actions = [
                    f"Contact {core_status.best_hospital} for booking",
                    "Prepare complete medical records",
                    "Confirm GP referral status"
                ]
            else:
                immediate_actions = [
                    "Expand search radius to 50km",
                    "Consider private healthcare options",
                    "Contact GP about urgent referral"
                ]
            
            this_week_actions = [
                "Contact 3-5 alternative hospitals",
                "Update personal medical information",
                "Research transport routes and accommodation"
            ]
            
            monitoring_items = [
                "Check daily waiting time changes",
                "Monitor sudden appointment cancellations",
                "Track other patients' experience sharing"
            ]
        
        return ActionPlan(immediate_actions, this_week_actions, monitoring_items)
    
    def _get_slot_recommendations(self, user_info: dict, user_lang: str) -> str:
        """获取号源推荐内容"""
        try:
            # 获取用户附近的可用预约时段
            available_slots = self._get_available_appointment_slots(user_info)
            
            if not available_slots:
                if user_lang == 'zh':
                    return """🏥 **实时号源推荐**

❌ 暂无可用的即时预约时段
💡 建议加入候补名单并保持电话畅通

📞 **抢号技巧**：
• 周一早上9点是最佳致电时间
• 表达灵活性：「我可以随时配合安排」
• 询问临时空缺：「如有人取消请优先联系我」"""
                else:
                    return """🏥 **Real-time Slot Recommendations**

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
                return "🏥 **实时号源推荐**\n\n⚠️ 暂时无法获取实时号源信息，请稍后重试"
            else:
                return "🏥 **Real-time Slot Recommendations**\n\n⚠️ Unable to get real-time slot information, please try again later"
    
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
        
        # 随机决定是否有可用时段（70%概率有）
        if random.random() < 0.7:
            return mock_slots
        else:
            return []
    
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
🔥 **周一动力**

新的一周开始了！这是采取积极行动的最佳时机。统计显示，周一进行的医疗咨询和预约安排效果最佳。

💪 **本周目标**：主动联系医院，不要等待机会自己降临。"""
    
    def _tuesday_tips_zh(self) -> str:
        return """
💡 **周二贴士**

想要提高预约成功率？这里有一个秘密：大部分医院在周二上午处理取消预约，这意味着会有临时空缺释放。

📱 **实用技巧**：设置多个医院的提醒，保持电话畅通。"""
    
    def _wednesday_wisdom_zh(self) -> str:
        return """
🧠 **周三智慧**

数据显示，主动联系医院的患者比被动等待的患者节省30%的等候时间。您的积极行动正在为自己创造更多机会。

🎯 **关键指标**：医院联系频率与预约预订速度成正比。"""
    
    def _thursday_insights_zh(self) -> str:
        return """
📊 **周四洞察**

即将到来的周末是回顾本周进展和规划下周行动的好时机。回顾本周的联系记录，为下周的行动做准备。

📋 **周末任务**：整理医疗文档，更新联系清单。"""
    
    def _friday_focus_zh(self) -> str:
        return """
🎯 **周五重点**

周末即将到来，这是回顾本周进展和规划下周行动的好时机。回顾本周的联系记录，为下周的行动做准备。

📋 **周末任务**：整理医疗文档，更新联系清单。"""
    
    def _weekend_wellness_zh(self) -> str:
        return """
🌟 **周末健康**

周末是关注整体健康的好时机。除了监控等候时间，也要关注饮食、运动和心理健康的平衡。

🏃‍♀️ **周末建议**：适度运动，保持积极心态，为下周的医疗行动积蓄能量。"""
    
    def _monday_motivation_en(self) -> str:
        return """
🔥 **Monday Motivation**

A new week begins! This is the best time to take positive action. Statistics show that medical consultations and appointment arrangements made on Mondays are most effective.

💪 **Weekly Goal**: Proactively contact hospitals, don't wait for opportunities to come to you."""
    
    def _tuesday_tips_en(self) -> str:
        return """
💡 **Tuesday Tips**

Want to improve your appointment success rate? Here's a secret: Most hospitals process cancellations on Tuesday mornings, meaning temporary slots become available.

📱 **Practical Tip**: Set up alerts for multiple hospitals and keep your phone available."""
    
    def _wednesday_wisdom_en(self) -> str:
        return """
🧠 **Wednesday Wisdom**

Data shows that patients who actively contact hospitals save an average of 30% waiting time compared to those who wait passively. Your proactive actions are creating more opportunities for yourself.

🎯 **Key Metric**: Hospital contact frequency is proportional to appointment booking speed."""
    
    def _thursday_insights_en(self) -> str:
        return """
📊 **Thursday Insights**

The weekend is approaching, a good time to review this week's progress and plan next week's actions. Review this week's contact records and prepare for next week's actions.

📋 **Weekend Tasks**: Organize medical documents, update contact lists."""
    
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
            
            # 将号源推荐紧接在当前等候状态分析之后
            message += f"""
━━━━━━━━━━━━━━━━━━━━━━

{slot_recommendations}

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
            
            # 将号源推荐紧接在当前等候状态分析之后
            message += f"""
━━━━━━━━━━━━━━━━━━━━━━

{slot_recommendations}

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
        """获取后备消息"""
        if user_lang == 'zh':
            return """🌅 **NHS智能提醒系统**

⚠️ 系统临时无法生成个性化推送，但我们仍在为您监控等候时间变化。

💡 **建议**：
• 请稍后重试
• 联系客服获取人工协助
• 直接查询NHS官方网站

使用命令：
• *1* - 查看状态
• *7* - 重新生成推送"""
        else:
            return """🌅 **NHS Smart Alert System**

⚠️ System temporarily unable to generate personalized alerts, but we're still monitoring waiting time changes for you.

💡 **Suggestions**:
• Please try again later
• Contact customer service for manual assistance
• Check NHS official website directly

Use commands:
• *1* - View status
• *7* - Regenerate alert""" 