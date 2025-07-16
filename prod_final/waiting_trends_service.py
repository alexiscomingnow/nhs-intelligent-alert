#!/usr/bin/env python3
"""
NHS等候时间趋势分析服务
提供给Telegram Bot使用的趋势分析功能
"""

import sqlite3
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import statistics
from dataclasses import dataclass
from geographic_service import GeographicService

@dataclass
class TrendData:
    """趋势数据结构"""
    hospital_name: str
    specialty_name: str
    current_weeks: int
    previous_weeks: int
    trend_direction: str  # 'improving', 'worsening', 'stable'
    change_weeks: int
    percentage_change: float
    patient_count: int
    distance_km: Optional[float] = None  # 添加距离信息

@dataclass
class TrendSummary:
    """趋势摘要"""
    user_specialty: str
    total_hospitals: int
    improving_count: int
    worsening_count: int
    stable_count: int
    best_hospital: str
    best_wait_time: int
    worst_hospital: str
    worst_wait_time: int
    average_wait_time: float
    regional_trend: str
    within_range_count: int = 0
    outside_range_count: int = 0

class WaitingTrendsService:
    """等候时间趋势分析服务"""
    
    def __init__(self, db_path: str = 'nhs_alerts.db'):
        self.db_path = db_path
        self.geo_service = GeographicService(db_path)
    
    def get_user_trends(self, user_id: str, user_lang: str = 'en') -> str:
        """获取用户的等候时间趋势分析"""
        try:
            # 获取用户偏好
            user_prefs = self._get_user_preferences(user_id)
            if not user_prefs:
                return self._format_no_preferences_message(user_lang)
            
            specialty = user_prefs.get('specialty', '')
            postcode = user_prefs.get('postcode', '')
            radius_km = user_prefs.get('radius_km', 25)
            
            # 获取趋势数据
            trend_data = self._analyze_specialty_trends(specialty)
            if not trend_data:
                return self._format_no_data_message(specialty, user_lang)
            
            # 根据用户位置过滤趋势数据
            within_range, outside_range = self._filter_trends_by_location(
                trend_data, postcode, radius_km
            )
            
            # 生成趋势摘要
            summary = self._generate_trend_summary(within_range, outside_range, specialty)
            
            # 格式化输出
            return self._format_trend_message(summary, within_range, outside_range, user_lang)
            
        except Exception as e:
            print(f"获取趋势分析失败: {e}")
            return "❌ 趋势分析暂时不可用" if user_lang == 'zh' else "❌ Trend analysis temporarily unavailable"
    
    def _filter_trends_by_location(self, trend_data: List[TrendData], 
                                 user_postcode: str, radius_km: int) -> Tuple[List[TrendData], List[TrendData]]:
        """根据用户位置过滤趋势数据"""
        if not user_postcode:
            # 如果没有邮编，返回所有数据作为范围内数据
            return trend_data, []
        
        within_range, outside_range = self.geo_service.add_distance_info_to_trends(
            user_postcode, trend_data, radius_km
        )
        
        return within_range, outside_range
    
    def _get_user_preferences(self, user_id: str) -> Optional[Dict]:
        """获取用户偏好设置"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT specialty, postcode, radius_km, threshold_weeks
                FROM user_preferences 
                WHERE user_id = ? OR phone_number = ?
            """, (user_id, user_id))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'specialty': row[0],
                    'postcode': row[1], 
                    'radius_km': row[2] or 25,
                    'threshold_weeks': row[3] or 12
                }
            return None
            
        except Exception as e:
            print(f"获取用户偏好失败: {e}")
            return None
    
    def _get_specialty_patterns(self, specialty: str) -> List[str]:
        """获取专科的匹配模式"""
        specialty_mapping = {
            'Orthopedics': ['Trauma & Orthopaedics', 'Orthopaedics', 'Orthopedic'],
            'Cardiology': ['Cardiology', 'Cardiac', 'Cardiothoracic'],
            'ENT': ['ENT', 'Ear Nose', 'Otolaryngology'],
            'Dermatology': ['Dermatology', 'Skin'],
            'Ophthalmology': ['Ophthalmology', 'Eye'],
            'Neurology': ['Neurology', 'Neurosurgery', 'Neurological'],
            'Urology': ['Urology', 'Urological'],
            'Gastroenterology': ['Gastroenterology', 'Gastro'],
            'General Surgery': ['General Surgery', 'Surgery'],
            'Gynecology': ['Gynaecology', 'Gynecology', 'Obstetrics']
        }
        
        # 首先查找精确匹配
        if specialty in specialty_mapping:
            return specialty_mapping[specialty]
        
        # 然后查找模糊匹配
        for key, patterns in specialty_mapping.items():
            if specialty.lower() in key.lower() or key.lower() in specialty.lower():
                return patterns
        
        # 最后返回原始专科名称
        return [specialty]

    def _analyze_specialty_trends(self, specialty: str) -> List[TrendData]:
        """分析特定专科的趋势"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取最近两个期间的数据
            cursor.execute("""
                SELECT DISTINCT period FROM nhs_rtt_data 
                ORDER BY period DESC LIMIT 2
            """)
            periods = [row[0] for row in cursor.fetchall()]
            
            if len(periods) < 2:
                return []
            
            current_period, previous_period = periods[0], periods[1]
            
            # 改进专科匹配逻辑
            specialty_patterns = self._get_specialty_patterns(specialty)
            
            # 构建动态查询条件
            where_conditions = []
            params = [previous_period, current_period]
            
            for pattern in specialty_patterns:
                where_conditions.append("curr.specialty_name LIKE ?")
                params.append(f'%{pattern}%')
            
            where_clause = " OR ".join(where_conditions)
            
            # 获取当前和之前期间的数据
            cursor.execute(f"""
                SELECT 
                    curr.org_name,
                    curr.specialty_name,
                    curr.waiting_time_weeks as current_weeks,
                    curr.patient_count as current_patients,
                    prev.waiting_time_weeks as previous_weeks
                FROM nhs_rtt_data curr
                LEFT JOIN nhs_rtt_data prev ON 
                    curr.org_code = prev.org_code AND 
                    curr.specialty_code = prev.specialty_code AND
                    prev.period = ?
                WHERE curr.period = ? 
                AND ({where_clause})
                ORDER BY curr.waiting_time_weeks ASC
            """, params)
            
            rows = cursor.fetchall()
            conn.close()
            
            trend_data = []
            for row in rows:
                org_name, spec_name, current_weeks, patient_count, previous_weeks = row
                
                if previous_weeks is not None:
                    change_weeks = current_weeks - previous_weeks
                    percentage_change = ((current_weeks - previous_weeks) / previous_weeks) * 100 if previous_weeks > 0 else 0
                    
                    if change_weeks < -1:
                        trend_direction = 'improving'
                    elif change_weeks > 1:
                        trend_direction = 'worsening'
                    else:
                        trend_direction = 'stable'
                else:
                    change_weeks = 0
                    percentage_change = 0
                    trend_direction = 'stable'
                
                trend_data.append(TrendData(
                    hospital_name=org_name,
                    specialty_name=spec_name,
                    current_weeks=current_weeks,
                    previous_weeks=previous_weeks or current_weeks,
                    trend_direction=trend_direction,
                    change_weeks=change_weeks,
                    percentage_change=percentage_change,
                    patient_count=patient_count
                ))
            
            return trend_data
            
        except Exception as e:
            print(f"分析专科趋势失败: {e}")
            return []
    
    def _generate_trend_summary(self, within_range: List[TrendData], 
                              outside_range: List[TrendData], specialty: str) -> TrendSummary:
        """生成趋势摘要"""
        # 优先使用范围内的数据进行统计
        primary_data = within_range if within_range else outside_range
        all_data = within_range + outside_range
        
        if not primary_data:
            return TrendSummary(
                user_specialty=specialty,
                total_hospitals=0,
                improving_count=0,
                worsening_count=0,
                stable_count=0,
                best_hospital="无数据",
                best_wait_time=0,
                worst_hospital="无数据", 
                worst_wait_time=0,
                average_wait_time=0,
                regional_trend='stable',
                within_range_count=len(within_range),
                outside_range_count=len(outside_range)
            )
        
        total_hospitals = len(primary_data)
        improving_count = sum(1 for t in primary_data if t.trend_direction == 'improving')
        worsening_count = sum(1 for t in primary_data if t.trend_direction == 'worsening')
        stable_count = total_hospitals - improving_count - worsening_count
        
        # 找出最佳和最差医院（优先考虑范围内）
        best_hospital = min(primary_data, key=lambda x: x.current_weeks)
        worst_hospital = max(primary_data, key=lambda x: x.current_weeks)
        
        # 计算平均等候时间
        average_wait_time = statistics.mean([t.current_weeks for t in primary_data])
        
        # 判断区域趋势
        total_change = sum(t.change_weeks for t in primary_data)
        if total_change < -5:
            regional_trend = 'improving'
        elif total_change > 5:
            regional_trend = 'worsening'
        else:
            regional_trend = 'stable'
        
        return TrendSummary(
            user_specialty=specialty,
            total_hospitals=total_hospitals,
            improving_count=improving_count,
            worsening_count=worsening_count,
            stable_count=stable_count,
            best_hospital=best_hospital.hospital_name,
            best_wait_time=best_hospital.current_weeks,
            worst_hospital=worst_hospital.hospital_name,
            worst_wait_time=worst_hospital.current_weeks,
            average_wait_time=average_wait_time,
            regional_trend=regional_trend,
            within_range_count=len(within_range),
            outside_range_count=len(outside_range)
        )
    
    def _format_trend_message(self, summary: TrendSummary, within_range: List[TrendData], 
                            outside_range: List[TrendData], user_lang: str) -> str:
        """格式化趋势消息"""
        if user_lang == 'zh':
            return self._format_trend_message_zh(summary, within_range, outside_range)
        else:
            return self._format_trend_message_en(summary, within_range, outside_range)
    
    def _format_trend_message_zh(self, summary: TrendSummary, within_range: List[TrendData], 
                               outside_range: List[TrendData]) -> str:
        """格式化中文趋势消息"""
        # 趋势图标
        trend_icon = {
            'improving': '📈 改善中',
            'worsening': '📉 恶化中', 
            'stable': '➡️ 稳定'
        }
        
        message = f"""📊 **{summary.user_specialty} 等候时间趋势分析**

🏥 **您的区域内** ({summary.within_range_count} 家医院)
• 平均等候: {summary.average_wait_time:.1f} 周
• 区域趋势: {trend_icon[summary.regional_trend]}

📈 **变化统计**
• 🟢 改善: {summary.improving_count} 家医院
• 🔴 恶化: {summary.worsening_count} 家医院  
• 🟡 稳定: {summary.stable_count} 家医院

⭐ **推荐医院**
🏆 **最短等候**: {summary.best_hospital}
⏰ 等候时间: {summary.best_wait_time} 周"""

        if within_range and getattr(within_range[0], 'distance_km', None):
            message += f"\n📍 距离: {within_range[0].distance_km} 公里"

        message += f"""

📋 **您区域内的医院** (按等候时间排序):
"""
        
        # 添加范围内医院的详细信息
        if within_range:
            for i, trend in enumerate(within_range[:5]):  # 显示前5个
                change_icon = "🟢" if trend.trend_direction == 'improving' else "🔴" if trend.trend_direction == 'worsening' else "🟡"
                change_text = f"{'↓' if trend.change_weeks < 0 else '↑' if trend.change_weeks > 0 else '='}{abs(trend.change_weeks)}周" if trend.change_weeks != 0 else "稳定"
                
                message += f"\n{i+1}. **{trend.hospital_name}**"
                message += f"\n   ⏰ {trend.current_weeks}周 {change_icon} {change_text}"
                if trend.change_weeks != 0:
                    message += f" ({trend.percentage_change:+.1f}%)"
                if hasattr(trend, 'distance_km') and trend.distance_km:
                    message += f"\n   📍 {trend.distance_km} 公里"
                message += f"\n   👥 {trend.patient_count} 人等候\n"
        else:
            message += "\n❌ 您的设定范围内暂无该专科数据"
        
        # 如果有范围外的医院，提供选项
        if outside_range:
            message += f"\n\n🌍 **范围外选项** ({len(outside_range)} 家医院)"
            message += "\n💡 考虑扩大搜索范围以获得更多选择："
            
            # 显示最好的3个范围外选项
            for i, trend in enumerate(sorted(outside_range, key=lambda x: x.current_weeks)[:3]):
                message += f"\n• **{trend.hospital_name}**: {trend.current_weeks}周"
                if hasattr(trend, 'distance_km') and trend.distance_km:
                    message += f" (距离: {trend.distance_km} 公里)"
        
        if within_range:
            best_option = min(within_range, key=lambda x: x.current_weeks)
            worst_option = max(within_range, key=lambda x: x.current_weeks)
            savings = worst_option.current_weeks - best_option.current_weeks
            if savings > 0:
                message += f"\n\n💡 **建议**: 选择 {best_option.hospital_name} 可以节省 {savings} 周等候时间"
        
        return message
    
    def _format_trend_message_en(self, summary: TrendSummary, within_range: List[TrendData], 
                               outside_range: List[TrendData]) -> str:
        """格式化英文趋势消息"""
        trend_icon = {
            'improving': '📈 Improving',
            'worsening': '📉 Worsening',
            'stable': '➡️ Stable'
        }
        
        message = f"""📊 **{summary.user_specialty} Waiting Time Trends**

🏥 **Within Your Area** ({summary.within_range_count} hospitals)
• Average wait: {summary.average_wait_time:.1f} weeks
• Regional trend: {trend_icon[summary.regional_trend]}

📈 **Change Statistics**
• 🟢 Improving: {summary.improving_count} hospitals
• 🔴 Worsening: {summary.worsening_count} hospitals
• 🟡 Stable: {summary.stable_count} hospitals

⭐ **Recommendations**
🏆 **Shortest Wait**: {summary.best_hospital}
⏰ Wait time: {summary.best_wait_time} weeks"""

        if within_range and getattr(within_range[0], 'distance_km', None):
            message += f"\n📍 Distance: {within_range[0].distance_km} km"

        message += f"""

📋 **Hospitals in Your Area** (sorted by wait time):
"""
        
        # Add hospitals within range
        if within_range:
            for i, trend in enumerate(within_range[:5]):  # Show top 5
                change_icon = "🟢" if trend.trend_direction == 'improving' else "🔴" if trend.trend_direction == 'worsening' else "🟡"
                change_text = f"{'↓' if trend.change_weeks < 0 else '↑' if trend.change_weeks > 0 else '='}{abs(trend.change_weeks)}wks" if trend.change_weeks != 0 else "stable"
                
                message += f"\n{i+1}. **{trend.hospital_name}**"
                message += f"\n   ⏰ {trend.current_weeks}wks {change_icon} {change_text}"
                if trend.change_weeks != 0:
                    message += f" ({trend.percentage_change:+.1f}%)"
                if hasattr(trend, 'distance_km') and trend.distance_km:
                    message += f"\n   📍 {trend.distance_km} km"
                message += f"\n   👥 {trend.patient_count} waiting\n"
        else:
            message += "\n❌ No data available for this specialty in your range"
        
        # Show outside range options if available
        if outside_range:
            message += f"\n\n🌍 **Outside Range Options** ({len(outside_range)} hospitals)"
            message += "\n💡 Consider expanding your search radius for more options:"
            
            # Show best 3 outside range options
            for i, trend in enumerate(sorted(outside_range, key=lambda x: x.current_weeks)[:3]):
                message += f"\n• **{trend.hospital_name}**: {trend.current_weeks}wks"
                if hasattr(trend, 'distance_km') and trend.distance_km:
                    message += f" (distance: {trend.distance_km} km)"
        
        if within_range:
            best_option = min(within_range, key=lambda x: x.current_weeks)
            worst_option = max(within_range, key=lambda x: x.current_weeks)
            savings = worst_option.current_weeks - best_option.current_weeks
            if savings > 0:
                message += f"\n\n💡 **Tip**: Choose {best_option.hospital_name} to save {savings} weeks"
        
        return message
    
    def _format_no_preferences_message(self, user_lang: str) -> str:
        """格式化无偏好设置消息"""
        if user_lang == 'zh':
            return """❌ **未找到用户偏好设置**

请先完成设置：
1. 发送 'setup' 开始配置
2. 选择您关注的专科
3. 输入您的邮编
4. 设定搜索范围

设置完成后即可查看趋势分析！"""
        else:
            return """❌ **User preferences not found**

Please complete setup first:
1. Send 'setup' to start configuration
2. Choose your specialty of interest
3. Enter your postcode
4. Set your search radius

Once setup is complete, you can view trend analysis!"""
    
    def _format_no_data_message(self, specialty: str, user_lang: str) -> str:
        """格式化无数据消息"""
        if user_lang == 'zh':
            return f"""❌ **{specialty} 专科数据不足**

可能原因：
• 该专科名称不匹配数据库
• 最近没有更新的数据
• 您的区域暂无此专科数据

建议：
• 尝试其他专科名称
• 扩大搜索范围
• 稍后再试"""
        else:
            return f"""❌ **Insufficient data for {specialty}**

Possible reasons:
• Specialty name doesn't match database
• No recent data updates
• No data for this specialty in your area

Suggestions:
• Try alternative specialty names
• Expand search radius
• Try again later""" 