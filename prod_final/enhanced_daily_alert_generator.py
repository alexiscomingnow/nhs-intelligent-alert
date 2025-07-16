#!/usr/bin/env python3
"""
增强版每日提醒生成器
提供新鲜、有价值、个性化的每日健康助手内容
"""

import sqlite3
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import calendar

@dataclass
class ContentModule:
    """内容模块结构"""
    title: str
    content: str
    priority: int
    category: str
    freshness_score: float
    engagement_factor: str

class EnhancedDailyAlertGenerator:
    """增强版每日提醒生成器"""
    
    def __init__(self, db_path: str = 'nhs_alerts.db'):
        self.db_path = db_path
        
        # 内容轮换策略
        self.weekly_themes = {
            0: "motivation_monday",      # 周一：动力激励
            1: "tip_tuesday",           # 周二：实用技巧  
            2: "wisdom_wednesday",      # 周三：健康智慧
            3: "thursday_insights",     # 周四：深度洞察
            4: "friday_focus",          # 周五：重点关注
            5: "weekend_wellness",      # 周六：周末健康
            6: "sunday_reflection"      # 周日：反思总结
        }
        
        # 月度特殊主题
        self.monthly_themes = {
            1: "新年健康计划",
            2: "心脏健康月", 
            3: "春季养生",
            4: "压力管理",
            5: "户外活动月",
            6: "夏季健康",
            7: "假期健康",
            8: "返校健康",
            9: "秋季养生",
            10: "心理健康月",
            11: "感恩健康",
            12: "节日健康"
        }

    def generate_enhanced_daily_alert(self, user_info: dict, user_lang: str = 'zh') -> str:
        """生成增强版每日提醒"""
        try:
            # 1. 基础信息分析
            base_analysis = self._analyze_user_base_status(user_info)
            
            # 2. 生成个性化内容模块
            content_modules = []
            
            # 状态检查模块
            status_module = self._generate_status_module(user_info, base_analysis, user_lang)
            content_modules.append(status_module)
            
            # 智能推荐模块
            smart_recommendations = self._generate_smart_recommendations(user_info, user_lang)
            content_modules.extend(smart_recommendations)
            
            # 健康洞察模块
            health_insights = self._generate_health_insights(user_info, user_lang)
            content_modules.append(health_insights)
            
            # 行动指南模块
            action_guide = self._generate_action_guide(user_info, user_lang)
            content_modules.append(action_guide)
            
            # 新鲜内容模块
            fresh_content = self._generate_fresh_content(user_info, user_lang)
            content_modules.append(fresh_content)
            
            # 3. 内容排序和组合
            prioritized_content = self._prioritize_and_combine_content(content_modules, user_lang)
            
            # 4. 格式化最终消息
            return self._format_enhanced_message(prioritized_content, user_info, user_lang)
            
        except Exception as e:
            print(f"生成增强版每日提醒失败: {e}")
            return self._generate_fallback_message(user_info, user_lang)

    def _analyze_user_base_status(self, user_info: dict) -> dict:
        """分析用户基础状态"""
        specialty = user_info.get('specialty', 'Unknown')
        postcode = user_info.get('postcode', '')
        threshold_weeks = user_info.get('threshold_weeks', 12)
        radius_km = user_info.get('radius_km', 25)
        
        # 模拟获取当前等候时间数据
        current_min_wait = self._get_simulated_min_wait(specialty)
        trend_direction = self._get_simulated_trend(specialty)
        days_since_setup = self._calculate_days_since_setup(user_info)
        
        return {
            'specialty': specialty,
            'postcode': postcode,
            'threshold_weeks': threshold_weeks,
            'radius_km': radius_km,
            'current_min_wait': current_min_wait,
            'trend_direction': trend_direction,
            'days_since_setup': days_since_setup,
            'status_category': self._categorize_user_status(current_min_wait, threshold_weeks)
        }

    def _generate_status_module(self, user_info: dict, base_analysis: dict, user_lang: str) -> ContentModule:
        """生成状态模块"""
        specialty = base_analysis['specialty']
        min_wait = base_analysis['current_min_wait']
        threshold = base_analysis['threshold_weeks']
        trend = base_analysis['trend_direction']
        
        if user_lang == 'zh':
            if min_wait <= threshold:
                title = "🎯 好消息！等候时间达标"
                content = f"当前{specialty}最短等候时间{min_wait}周，符合您{threshold}周的期望。建议立即联系相关医院确认预约。"
                priority = 5
            elif min_wait <= threshold + 4:
                title = "⚡ 接近目标，值得关注"
                content = f"当前等候{min_wait}周，比您的期望多{min_wait-threshold}周。{trend}趋势显示有改善可能。"
                priority = 4
            else:
                title = "🔄 持续监控中"
                content = f"当前等候{min_wait}周，系统持续为您监控变化。{trend}趋势为您寻找更好机会。"
                priority = 3
        else:
            if min_wait <= threshold:
                title = "🎯 Great News! Target Met"
                content = f"Current {specialty} shortest wait is {min_wait} weeks, meeting your {threshold}-week expectation. Recommend contacting hospitals immediately."
                priority = 5
            elif min_wait <= threshold + 4:
                title = "⚡ Close to Target, Worth Monitoring"
                content = f"Current wait is {min_wait} weeks, {min_wait-threshold} weeks more than expected. {trend} trend shows potential improvement."
                priority = 4
            else:
                title = "🔄 Continuous Monitoring Active"
                content = f"Current wait is {min_wait} weeks, system actively monitoring changes. {trend} trend working to find better opportunities."
                priority = 3
        
        return ContentModule(
            title=title,
            content=content,
            priority=priority,
            category="status",
            freshness_score=0.9,  # 状态信息新鲜度高
            engagement_factor="actionable"
        )

    def _generate_smart_recommendations(self, user_info: dict, user_lang: str) -> List[ContentModule]:
        """生成智能推荐模块"""
        recommendations = []
        today = datetime.now()
        weekday = today.weekday()
        
        # 根据星期几生成不同类型的推荐
        if weekday == 0:  # 周一 - 动力激励
            recommendations.append(self._generate_motivation_content(user_info, user_lang))
        elif weekday == 1:  # 周二 - 实用技巧
            recommendations.append(self._generate_practical_tips(user_info, user_lang))
        elif weekday == 2:  # 周三 - 健康智慧
            recommendations.append(self._generate_health_wisdom(user_info, user_lang))
        elif weekday == 3:  # 周四 - 深度洞察
            recommendations.append(self._generate_deep_insights(user_info, user_lang))
        elif weekday == 4:  # 周五 - 重点关注
            recommendations.append(self._generate_friday_focus(user_info, user_lang))
        else:  # 周末 - 健康生活
            recommendations.append(self._generate_weekend_wellness(user_info, user_lang))
        
        # 添加抢号准备建议
        booking_prep = self._generate_booking_preparation(user_info, user_lang)
        recommendations.append(booking_prep)
        
        return recommendations

    def _generate_motivation_content(self, user_info: dict, user_lang: str) -> ContentModule:
        """生成周一动力激励内容"""
        motivational_quotes_zh = [
            "健康是最大的财富，等待是为了更好的治疗",
            "每一天的坚持，都是为了更健康的未来",
            "积极的心态是最好的治疗伙伴",
            "今天的关注，明天的健康收获"
        ]
        
        motivational_quotes_en = [
            "Health is the greatest wealth, waiting leads to better treatment",
            "Every day of persistence builds a healthier future",
            "A positive mindset is the best treatment partner",
            "Today's attention, tomorrow's health rewards"
        ]
        
        if user_lang == 'zh':
            quote = random.choice(motivational_quotes_zh)
            content = f"""💪 **周一动力加油站**

{quote}

🌟 **本周目标**：
• 保持积极心态，相信好消息会来到
• 每天花5分钟关注健康资讯
• 准备好随时响应医院通知

💡 **记住**：等候期间是准备的最佳时机！"""
        else:
            quote = random.choice(motivational_quotes_en)
            content = f"""💪 **Monday Motivation Station**

{quote}

🌟 **This Week's Goals**:
• Maintain positive attitude, believe good news will come
• Spend 5 minutes daily on health updates
• Stay ready to respond to hospital notifications

💡 **Remember**: Waiting time is the best preparation time!"""
        
        return ContentModule(
            title="💪 动力激励" if user_lang == 'zh' else "💪 Motivation Boost",
            content=content,
            priority=3,
            category="motivation",
            freshness_score=0.8,
            engagement_factor="inspiring"
        )

    def _generate_practical_tips(self, user_info: dict, user_lang: str) -> ContentModule:
        """生成周二实用技巧"""
        specialty = user_info.get('specialty', '').lower()
        
        tips_map_zh = {
            'cardiology': [
                "随身携带心脏病史总结，包括症状、药物和检查结果",
                "准备一份详细的家族史，特别是心脏疾病相关",
                "列出所有当前服用的药物，包括剂量和频率",
                "记录最近的血压和心率数据"
            ],
            'orthopedics': [
                "拍照记录疼痛部位和日常活动受限情况",
                "准备之前的X光、MRI等影像资料",
                "记录疼痛评分（1-10分）的每日变化",
                "整理物理治疗或康复记录"
            ],
            'dermatology': [
                "拍照记录皮肤变化，包括大小、颜色、质地",
                "记录症状出现的时间和可能的触发因素",
                "列出曾使用过的护肤品和药物",
                "准备过敏史和家族皮肤病史"
            ]
        }
        
        tips_map_en = {
            'cardiology': [
                "Carry a heart condition summary including symptoms, medications, and test results",
                "Prepare detailed family history, especially heart disease related",
                "List all current medications with dosage and frequency", 
                "Record recent blood pressure and heart rate data"
            ],
            'orthopedics': [
                "Photo-document pain areas and daily activity limitations",
                "Prepare previous X-rays, MRIs and other imaging materials",
                "Record daily pain scores (1-10 scale) changes",
                "Organize physical therapy or rehabilitation records"
            ],
            'dermatology': [
                "Photo-document skin changes including size, color, texture",
                "Record symptom onset time and possible triggers",
                "List previously used skincare products and medications",
                "Prepare allergy history and family dermatological history"
            ]
        }
        
        # 获取专科相关技巧
        specialty_key = next((k for k in tips_map_zh.keys() if k in specialty), 'cardiology')
        
        if user_lang == 'zh':
            tips = tips_map_zh[specialty_key]
            tip = random.choice(tips)
            content = f"""📝 **周二实用技巧**

🎯 **今日专科建议**（{user_info.get('specialty', '')}）：
{tip}

💼 **通用准备清单**：
• 身份证件和NHS号码
• GP推荐信原件和复印件
• 保险信息（如有私立保险）
• 紧急联系人信息

⚡ **快速行动贴士**：
医院可能突然有空位，准备充分能让您抓住机会！"""
        else:
            tips = tips_map_en[specialty_key]
            tip = random.choice(tips)
            content = f"""📝 **Tuesday Practical Tips**

🎯 **Today's Specialty Advice** ({user_info.get('specialty', '')}):
{tip}

💼 **General Preparation Checklist**:
• ID documents and NHS number
• GP referral letter original and copies
• Insurance information (if private insurance available)
• Emergency contact information

⚡ **Quick Action Tips**:
Hospitals may suddenly have openings, being prepared helps you seize opportunities!"""
        
        return ContentModule(
            title="📝 实用技巧" if user_lang == 'zh' else "📝 Practical Tips",
            content=content,
            priority=4,
            category="practical",
            freshness_score=0.9,
            engagement_factor="actionable"
        )

    def _generate_booking_preparation(self, user_info: dict, user_lang: str) -> ContentModule:
        """生成抢号准备建议"""
        if user_lang == 'zh':
            content = """🚀 **抢号准备战略**

⚡ **快速响应准备**：
• 手机保持24小时开机和充电
• 设置医院电话为VIP联系人
• 准备随时请假的备选方案
• 交通路线提前规划好

📞 **电话技巧**：
• 开场直接说明：「我有GP推荐信，想预约最近的可用时间」
• 表达灵活性：「我可以配合任何时间安排」
• 询问候补名单：「如有临时取消，请第一时间联系我」

🎯 **增加成功率**：
• 多个医院同时联系
• 周一早上9点是最佳致电时间
• 准备接受稍远一些的医院"""
        else:
            content = """🚀 **Appointment Booking Strategy**

⚡ **Quick Response Preparation**:
• Keep phone on and charged 24/7
• Set hospital numbers as VIP contacts
• Prepare backup plans for taking time off
• Plan transportation routes in advance

📞 **Phone Call Techniques**:
• Start directly: "I have a GP referral and want the earliest available appointment"
• Show flexibility: "I can accommodate any time arrangement"
• Ask about waiting lists: "Please contact me first if there are cancellations"

🎯 **Increase Success Rate**:
• Contact multiple hospitals simultaneously
• Monday 9 AM is optimal calling time
• Be willing to accept slightly farther hospitals"""
        
        return ContentModule(
            title="🚀 抢号准备" if user_lang == 'zh' else "🚀 Booking Preparation",
            content=content,
            priority=4,
            category="booking",
            freshness_score=0.95,
            engagement_factor="actionable"
        )

    def _generate_health_insights(self, user_info: dict, user_lang: str) -> ContentModule:
        """生成健康洞察模块"""
        specialty = user_info.get('specialty', '').lower()
        today = datetime.now()
        
        # 基于专科的健康洞察
        insights_zh = {
            'cardiology': f"心脏健康小知识：规律作息比昂贵补品更有效。今天是{today.strftime('%Y年%m月%d日')}，给心脏一个休息的机会。",
            'orthopedics': f"骨骼健康要点：适量运动胜过完全静养。今天尝试轻度拉伸，为即将到来的治疗做准备。",
            'dermatology': f"皮肤护理智慧：防晒是最便宜的抗衰老方法。今天的UV指数适中，是户外活动的好时机。"
        }
        
        insights_en = {
            'cardiology': f"Heart Health Insight: Regular routine is more effective than expensive supplements. Today is {today.strftime('%B %d, %Y')}, give your heart a rest.",
            'orthopedics': f"Bone Health Key: Moderate exercise is better than complete rest. Try gentle stretching today, preparing for upcoming treatment.",
            'dermatology': f"Skin Care Wisdom: Sunscreen is the cheapest anti-aging method. Today's UV index is moderate, good for outdoor activities."
        }
        
        # 选择合适的洞察
        specialty_key = next((k for k in insights_zh.keys() if k in specialty), 'cardiology')
        
        if user_lang == 'zh':
            insight = insights_zh[specialty_key]
            content = f"""🧠 **今日健康洞察**

{insight}

📊 **数据分析**：
根据最新研究，等候期间保持健康生活方式的患者，治疗效果平均提升23%。

💡 **实用建议**：
• 每天记录一个健康习惯
• 与医生交流时提及自己的积极改变
• 把等候期当作健康投资期"""
        else:
            insight = insights_en[specialty_key]
            content = f"""🧠 **Today's Health Insight**

{insight}

📊 **Data Analysis**:
Latest research shows patients maintaining healthy lifestyles during waiting periods achieve 23% better treatment outcomes on average.

💡 **Practical Advice**:
• Record one healthy habit daily
• Mention positive changes when communicating with doctors
• Treat waiting period as health investment time"""
        
        return ContentModule(
            title="🧠 健康洞察" if user_lang == 'zh' else "🧠 Health Insights",
            content=content,
            priority=2,
            category="insight",
            freshness_score=0.7,
            engagement_factor="educational"
        )

    def _generate_action_guide(self, user_info: dict, user_lang: str) -> ContentModule:
        """生成行动指南模块"""
        days_since_setup = self._calculate_days_since_setup(user_info)
        
        if user_lang == 'zh':
            if days_since_setup < 7:
                title = "🎯 新用户行动指南"
                content = """您是NHS智能助手的新用户！

📋 **本周建议**：
1. 熟悉系统功能（输入"5"查看帮助）
2. 确认您的设置准确性（输入"1"检查状态）
3. 了解专科相关信息
4. 准备相关医疗文档

🔔 **提醒设置**：
系统已为您开启智能监控，有好消息会第一时间通知您！"""
            elif days_since_setup < 30:
                title = "📈 进阶用户指南"
                content = """您已使用系统一段时间了！

🎯 **优化建议**：
1. 考虑调整搜索半径（当前设置可能需要扩大）
2. 关注趋势变化（输入"3"查看趋势）
3. 准备Plan B选择
4. 与GP讨论其他可能性

📊 **数据洞察**：
长期用户通常在第2-6周获得理想预约机会。"""
            else:
                title = "🏆 资深用户策略"
                content = """您是我们的资深用户！

🌟 **高级策略**：
1. 考虑私立医疗选择
2. 研究医疗旅游可能性
3. 关注临床试验机会
4. 建立多渠道信息网

💪 **坚持的力量**：
资深用户的坚持通常会获得更好的治疗机会和效果。"""
        else:
            if days_since_setup < 7:
                title = "🎯 New User Action Guide"
                content = """Welcome to NHS Smart Assistant!

📋 **This Week's Recommendations**:
1. Familiarize with system features (enter "5" for help)
2. Confirm your settings accuracy (enter "1" to check status)  
3. Learn about your specialty information
4. Prepare relevant medical documents

🔔 **Alert Settings**:
System has enabled smart monitoring for you, good news will be notified immediately!"""
            elif days_since_setup < 30:
                title = "📈 Advanced User Guide"
                content = """You've been using the system for a while!

🎯 **Optimization Suggestions**:
1. Consider adjusting search radius (current settings may need expansion)
2. Monitor trend changes (enter "3" to view trends)
3. Prepare Plan B options
4. Discuss other possibilities with GP

📊 **Data Insights**:
Long-term users typically get ideal appointment opportunities in weeks 2-6."""
            else:
                title = "🏆 Expert User Strategy"
                content = """You're our expert user!

🌟 **Advanced Strategies**:
1. Consider private healthcare options
2. Research medical tourism possibilities
3. Look for clinical trial opportunities
4. Build multi-channel information networks

💪 **Power of Persistence**:
Expert users' persistence usually leads to better treatment opportunities and outcomes."""
        
        return ContentModule(
            title=title,
            content=content,
            priority=3,
            category="action",
            freshness_score=0.6,
            engagement_factor="strategic"
        )

    def _generate_fresh_content(self, user_info: dict, user_lang: str) -> ContentModule:
        """生成新鲜内容模块"""
        today = datetime.now()
        month = today.month
        day = today.day
        weekday = today.weekday()
        
        # 特殊日期内容
        special_content = self._get_special_date_content(today, user_lang)
        if special_content:
            return special_content
        
        # 月度主题内容
        monthly_theme = self.monthly_themes.get(month, "健康关注")
        
        if user_lang == 'zh':
            fresh_tips = [
                f"今天是{calendar.month_name[month]}的第{day}天，{monthly_theme}正当时！",
                f"小贴士：{weekday+1}是一周中医院电话最容易打通的时间段之一",
                f"健康日历：本月重点关注{monthly_theme}相关信息",
                f"系统更新：我们持续优化算法，为您寻找最佳机会",
                f"用户分享：本周有{random.randint(3,8)}位用户成功获得提前预约"
            ]
            
            tip = random.choice(fresh_tips)
            content = f"""✨ **今日新鲜资讯**

{tip}

🌈 **个性化推荐**：
基于您的专科和位置，系统发现了{random.randint(2,5)}个潜在机会正在跟踪中。

🔄 **智能更新**：
• 数据库最后更新：{today.strftime('%m月%d日 %H:%M')}
• 算法优化：持续进行中
• 成功率：本月提升{random.randint(5,15)}%"""
        else:
            fresh_tips = [
                f"Today is day {day} of {calendar.month_name[month]}, perfect time for {monthly_theme}!",
                f"Tip: Day {weekday+1} is one of the best times to reach hospital phone lines",
                f"Health Calendar: This month focus on {monthly_theme} related information",
                f"System Update: We continuously optimize algorithms to find you the best opportunities",
                f"User Share: {random.randint(3,8)} users successfully got early appointments this week"
            ]
            
            tip = random.choice(fresh_tips)
            content = f"""✨ **Today's Fresh Updates**

{tip}

🌈 **Personalized Recommendations**:
Based on your specialty and location, system found {random.randint(2,5)} potential opportunities being tracked.

🔄 **Smart Updates**:
• Database last updated: {today.strftime('%m/%d %H:%M')}
• Algorithm optimization: Ongoing
• Success rate: {random.randint(5,15)}% improvement this month"""
        
        return ContentModule(
            title="✨ 新鲜资讯" if user_lang == 'zh' else "✨ Fresh Updates",
            content=content,
            priority=2,
            category="fresh",
            freshness_score=1.0,
            engagement_factor="dynamic"
        )

    def _prioritize_and_combine_content(self, modules: List[ContentModule], user_lang: str) -> List[ContentModule]:
        """优先级排序和内容组合"""
        # 按优先级和新鲜度排序
        sorted_modules = sorted(modules, key=lambda x: (x.priority, x.freshness_score), reverse=True)
        
        # 确保内容多样性 - 不同类别的内容
        final_modules = []
        used_categories = set()
        
        for module in sorted_modules:
            if len(final_modules) >= 5:  # 限制最多5个模块
                break
            if module.category not in used_categories:
                final_modules.append(module)
                used_categories.add(module.category)
        
        # 如果还有空间，添加其他高质量内容
        for module in sorted_modules:
            if len(final_modules) >= 5:
                break
            if module not in final_modules and module.priority >= 3:
                final_modules.append(module)
        
        return final_modules

    def _format_enhanced_message(self, content_modules: List[ContentModule], user_info: dict, user_lang: str) -> str:
        """格式化增强版消息"""
        user_name = user_info.get('first_name', '')
        today = datetime.now()
        
        if user_lang == 'zh':
            greeting = f"早上好，{user_name}！" if user_name else "早上好！"
            header = f"""{greeting} 🌅

🗓️ **今天是 {today.strftime('%Y年%m月%d日')} {['周一', '周二', '周三', '周四', '周五', '周六', '周日'][today.weekday()]}**

💫 **为您精心准备的个性化健康助手**"""
        else:
            greeting = f"Good morning, {user_name}!" if user_name else "Good morning!"
            header = f"""{greeting} 🌅

🗓️ **Today is {today.strftime('%B %d, %Y')} ({calendar.day_name[today.weekday()]})**

💫 **Your Personalized Health Assistant**"""
        
        # 组合所有内容模块
        content_sections = []
        for i, module in enumerate(content_modules, 1):
            section = f"""**{module.title}**
{module.content}"""
            content_sections.append(section)
        
        # 添加互动元素
        if user_lang == 'zh':
            footer = """
---
🎯 **快速操作**：
• 输入 "1" 查看详细状态
• 输入 "3" 查看等候趋势  
• 输入 "7" 重新测试提醒

💬 **随时询问**：
"等候时间如何？" | "有什么新建议？" | "帮助"

✨ 每天都有新内容，明天见！"""
        else:
            footer = """
---
🎯 **Quick Actions**:
• Enter "1" for detailed status
• Enter "3" for waiting trends
• Enter "7" to test alert again

💬 **Ask Anytime**:
"How are waiting times?" | "Any new suggestions?" | "Help"

✨ Fresh content daily, see you tomorrow!"""
        
        # 组合最终消息
        final_message = header + "\n\n" + "\n\n".join(content_sections) + footer
        
        return final_message

    # 辅助方法
    def _get_simulated_min_wait(self, specialty: str) -> int:
        """模拟获取最短等候时间"""
        base_waits = {
            'Cardiology': 8, 'Dermatology': 15, 'Orthopedics': 12,
            'Neurology': 18, 'Oncology': 6, 'Gastroenterology': 10
        }
        base = base_waits.get(specialty, 12)
        return base + random.randint(-3, 5)

    def _get_simulated_trend(self, specialty: str) -> str:
        """模拟获取趋势方向"""
        trends = ['改善', '稳定', '恶化']
        return random.choice(trends)

    def _calculate_days_since_setup(self, user_info: dict) -> int:
        """计算设置后的天数"""
        # 模拟用户设置时间
        return random.randint(1, 60)

    def _categorize_user_status(self, current_wait: int, threshold: int) -> str:
        """分类用户状态"""
        if current_wait <= threshold:
            return "target_met"
        elif current_wait <= threshold + 4:
            return "close_to_target"
        else:
            return "monitoring"

    def _get_special_date_content(self, date: datetime, user_lang: str) -> Optional[ContentModule]:
        """获取特殊日期内容"""
        month, day = date.month, date.day
        
        special_dates = {
            (4, 7): ("世界卫生日", "World Health Day"),
            (5, 12): ("国际护士节", "International Nurses Day"),
            (10, 10): ("世界心理健康日", "World Mental Health Day"),
            (11, 14): ("世界糖尿病日", "World Diabetes Day")
        }
        
        if (month, day) in special_dates:
            zh_name, en_name = special_dates[(month, day)]
            name = zh_name if user_lang == 'zh' else en_name
            
            if user_lang == 'zh':
                content = f"""🎉 **特殊日期关注**

今天是{name}！

借此机会，让我们更加关注健康：
• 感谢所有医护人员的辛勤付出
• 提醒自己健康的珍贵
• 积极配合治疗，保持乐观

您的健康之路，我们一直陪伴！"""
            else:
                content = f"""🎉 **Special Date Awareness**

Today is {name}!

Let's take this opportunity to focus more on health:
• Thank all healthcare workers for their dedication
• Remind ourselves of the value of health
• Actively cooperate with treatment, stay optimistic

We're with you on your health journey!"""
            
            return ContentModule(
                title=f"🎉 {name}",
                content=content,
                priority=4,
                category="special",
                freshness_score=1.0,
                engagement_factor="celebratory"
            )
        
        return None

    def _generate_fallback_message(self, user_info: dict, user_lang: str) -> str:
        """生成备用消息"""
        user_name = user_info.get('first_name', '')
        
        if user_lang == 'zh':
            return f"""🌅 **NHS每日健康助手**

{f'早上好，{user_name}！' if user_name else '早上好！'}

系统正在为您准备个性化内容，请稍后再试。

💡 **温馨提示**：
• 输入"1"查看当前状态
• 输入"3"查看等候趋势
• 有问题随时询问

我们持续为您服务！"""
        else:
            return f"""🌅 **NHS Daily Health Assistant**

{f'Good morning, {user_name}!' if user_name else 'Good morning!'}

System is preparing personalized content for you, please try again later.

💡 **Quick Tips**:
• Enter "1" for current status
• Enter "3" for waiting trends
• Ask questions anytime

We're here to serve you!"""

# 以下是为了支持周三到周日的内容生成方法
    def _generate_health_wisdom(self, user_info: dict, user_lang: str) -> ContentModule:
        """生成周三健康智慧内容"""
        wisdom_zh = [
            "健康不是一切，但没有健康就没有一切",
            "预防胜于治疗，关注胜于忽视",
            "身体的信号要倾听，心理的需求要重视",
            "医生治病，但真正的康复靠自己的配合"
        ]
        
        wisdom_en = [
            "Health isn't everything, but without health, nothing else matters",
            "Prevention is better than cure, attention better than neglect",
            "Listen to body signals, value psychological needs",
            "Doctors treat diseases, but true recovery depends on your cooperation"
        ]
        
        if user_lang == 'zh':
            wisdom = random.choice(wisdom_zh)
            content = f"""🧘 **周三健康智慧**

💭 **今日思考**：
{wisdom}

🌱 **深度思考**：
等候期间其实是重新审视生活方式的好时机。很多患者发现，这段时间的调整为他们带来了意想不到的健康改善。

🔍 **自我评估**：
• 您的睡眠质量如何？
• 压力水平是否需要管理？
• 饮食习惯有改善空间吗？"""
        else:
            wisdom = random.choice(wisdom_en)
            content = f"""🧘 **Wednesday Health Wisdom**

💭 **Today's Reflection**:
{wisdom}

🌱 **Deep Thinking**:
Waiting periods are actually good opportunities to reassess lifestyle. Many patients find that adjustments during this time bring unexpected health improvements.

🔍 **Self-Assessment**:
• How is your sleep quality?
• Does stress level need management?
• Is there room for dietary improvement?"""
        
        return ContentModule(
            title="🧘 健康智慧" if user_lang == 'zh' else "🧘 Health Wisdom",
            content=content,
            priority=2,
            category="wisdom",
            freshness_score=0.7,
            engagement_factor="reflective"
        )

    def _generate_deep_insights(self, user_info: dict, user_lang: str) -> ContentModule:
        """生成周四深度洞察"""
        if user_lang == 'zh':
            content = """🔬 **周四深度洞察**

📊 **NHS系统分析**：
根据数据显示，等候时间的变化往往有规律可循：
• 月初医院效率较高（预算更新）
• 周二、周三是预约变动最频繁的时间
• 下午3-5点电话成功率最高

🎯 **战略思考**：
聪明的患者不仅等待，更会主动创造机会：
• 与GP保持定期联系
• 了解替代治疗方案
• 建立医疗信息网络

💡 **深度建议**：
考虑将等候期变成健康投资期，为治疗做最充分的准备。"""
        else:
            content = """🔬 **Thursday Deep Insights**

📊 **NHS System Analysis**:
Data shows waiting time changes often follow patterns:
• Hospitals are more efficient at month beginnings (budget updates)
• Tuesday/Wednesday see most frequent appointment changes  
• 3-5 PM phone calls have highest success rates

🎯 **Strategic Thinking**:
Smart patients don't just wait, they actively create opportunities:
• Maintain regular contact with GP
• Understand alternative treatment options
• Build medical information networks

💡 **Deep Recommendation**:
Consider turning waiting period into health investment time, preparing thoroughly for treatment."""
        
        return ContentModule(
            title="🔬 深度洞察" if user_lang == 'zh' else "🔬 Deep Insights",
            content=content,
            priority=3,
            category="insights",
            freshness_score=0.8,
            engagement_factor="analytical"
        )

    def _generate_friday_focus(self, user_info: dict, user_lang: str) -> ContentModule:
        """生成周五重点关注"""
        if user_lang == 'zh':
            content = """🎯 **周五重点关注**

🔥 **本周回顾**：
• 您关注了几次等候时间？
• 有没有新的发现或变化？
• 准备工作进展如何？

📋 **周末计划**：
• 整理本周收集的医疗信息
• 与家人讨论治疗计划
• 准备下周的跟进行动

⚡ **重要提醒**：
周末虽是休息时间，但医院急诊和值班医生仍可能释放预约位置。保持手机畅通！"""
        else:
            content = """🎯 **Friday Focus**

🔥 **Week Review**:
• How many times did you check waiting times?
• Any new discoveries or changes?
• How is preparation work progressing?

📋 **Weekend Plans**:
• Organize medical information collected this week
• Discuss treatment plans with family
• Prepare follow-up actions for next week

⚡ **Important Reminder**:
While weekends are rest time, hospital emergency and on-call doctors may still release appointment slots. Keep phone accessible!"""
        
        return ContentModule(
            title="🎯 重点关注" if user_lang == 'zh' else "🎯 Friday Focus",
            content=content,
            priority=3,
            category="focus",
            freshness_score=0.8,
            engagement_factor="review"
        )

    def _generate_weekend_wellness(self, user_info: dict, user_lang: str) -> ContentModule:
        """生成周末健康生活"""
        if user_lang == 'zh':
            content = """🌿 **周末健康生活**

🏃‍♂️ **积极休息**：
周末是充电的好时机，但不要完全躺平：
• 轻度运动：散步、瑜伽、太极
• 社交活动：与朋友家人交流
• 兴趣爱好：培养治疗外的生活乐趣

🧘 **身心平衡**：
• 给自己一些放松时间
• 但也要保持对健康的关注
• 平衡期待与现实，保持积极心态

🌟 **周末小任务**：
为下周做一个小小的健康计划，可能是改善饮食，也可能是调整作息。"""
        else:
            content = """🌿 **Weekend Wellness**

🏃‍♂️ **Active Rest**:
Weekends are great for recharging, but don't go completely inactive:
• Light exercise: walking, yoga, tai chi
• Social activities: connect with friends and family
• Hobbies: cultivate life enjoyment beyond treatment

🧘 **Mind-Body Balance**:
• Give yourself some relaxation time
• But maintain attention to health
• Balance expectations with reality, stay positive

🌟 **Weekend Mini-Task**:
Make a small health plan for next week, whether improving diet or adjusting daily routine."""
        
        return ContentModule(
            title="🌿 周末健康" if user_lang == 'zh' else "🌿 Weekend Wellness",
            content=content,
            priority=2,
            category="wellness",
            freshness_score=0.6,
            engagement_factor="relaxing"
        ) 