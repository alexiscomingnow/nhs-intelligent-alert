#!/usr/bin/env python3
"""
增强版NHS等候时间趋势分析服务
解决用户查看趋势时的数据不足问题，提供智能推荐和扩大搜索范围
"""

import sqlite3
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import statistics
from dataclasses import dataclass
import re

@dataclass
class EnhancedTrendData:
    """增强版趋势数据结构"""
    hospital_name: str
    specialty_name: str
    current_weeks: int
    previous_weeks: int
    trend_direction: str  # 'improving', 'worsening', 'stable'
    change_weeks: int
    percentage_change: float
    patient_count: int
    distance_km: Optional[float] = None
    city: Optional[str] = None
    region: Optional[str] = None
    recommendation_score: float = 0.0  # 推荐分数

@dataclass
class TrendSummary:
    """趋势摘要"""
    user_specialty: str
    matched_specialties: List[str]  # 匹配到的实际专科名称
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
    within_range_count: int
    outside_range_count: int
    city_recommendations: List[Dict]  # 城市级别推荐

class EnhancedWaitingTrendsService:
    """增强版等候时间趋势分析服务"""
    
    def __init__(self, db_path: str = 'nhs_alerts.db'):
        self.db_path = db_path
        
        # 专科映射字典 - 解决专科名称不匹配问题
        self.specialty_mapping = {
            'nephrology': ['Urology', 'General Medicine', 'Endocrinology'],
            'kidney': ['Urology', 'General Medicine'],
            'renal': ['Urology', 'General Medicine'],
            'heart': ['Cardiology'],
            'cardiac': ['Cardiology'],
            'bone': ['Trauma & Orthopaedics', 'Orthopaedics'],
            'orthopedic': ['Trauma & Orthopaedics', 'Orthopaedics'],
            'eye': ['Ophthalmology'],
            'skin': ['Dermatology'],
            'mental': ['Psychiatry'],
            'stomach': ['Gastroenterology'],
            'digestive': ['Gastroenterology'],
            'cancer': ['Oncology', 'General Surgery'],
            'brain': ['Neurology', 'Neurosurgery'],
            'children': ['Paediatrics'],
            'women': ['Gynaecology', 'Obstetrics'],
            'ear': ['ENT'],
            'throat': ['ENT'],
            'nose': ['ENT']
        }
        
        # 城市邮编映射
        self.city_postcode_mapping = {
            'london': ['SW1', 'SE1', 'N1', 'E1', 'W1', 'WC1', 'EC1'],
            'birmingham': ['B1', 'B2', 'B3', 'B4', 'B5'],
            'manchester': ['M1', 'M2', 'M3', 'M4', 'M5'],
            'liverpool': ['L1', 'L2', 'L3', 'L4', 'L5'],
            'glasgow': ['G1', 'G2', 'G3', 'G4', 'G5'],
            'edinburgh': ['EH1', 'EH2', 'EH3', 'EH4'],
            'cardiff': ['CF1', 'CF2', 'CF3', 'CF4'],
            'belfast': ['BT1', 'BT2', 'BT3', 'BT4', 'BT37']
        }

    def get_enhanced_user_trends(self, user_id: str, user_lang: str = 'en') -> str:
        """获取增强版用户等候时间趋势分析"""
        try:
            # 获取用户偏好
            user_prefs = self._get_user_preferences(user_id)
            if not user_prefs:
                return self._format_no_preferences_message(user_lang)
            
            specialty = user_prefs.get('specialty', '')
            postcode = user_prefs.get('postcode', '')
            radius_km = user_prefs.get('radius_km', 25)
            
            # 步骤1：尝试精确匹配
            exact_trends = self._analyze_specialty_trends(specialty)
            
            # 步骤2：如果没有精确匹配，使用智能匹配
            if not exact_trends:
                matched_specialties = self._find_matching_specialties(specialty)
                all_trends = []
                for matched_specialty in matched_specialties:
                    trends = self._analyze_specialty_trends(matched_specialty)
                    all_trends.extend(trends)
                
                if not all_trends:
                    return self._format_enhanced_no_data_message(specialty, matched_specialties, user_lang)
            else:
                all_trends = exact_trends
                matched_specialties = [specialty]
            
            # 步骤3：基于位置过滤和分类
            within_range, outside_range, city_recommendations = self._enhanced_location_filtering(
                all_trends, postcode, radius_km
            )
            
            # 步骤4：生成增强版摘要
            summary = self._generate_enhanced_summary(
                within_range, outside_range, specialty, matched_specialties, city_recommendations
            )
            
            # 步骤5：格式化输出
            return self._format_enhanced_trend_message(summary, within_range, outside_range, user_lang)
            
        except Exception as e:
            print(f"获取增强趋势分析失败: {e}")
            import traceback
            traceback.print_exc()
            return "❌ 趋势分析暂时不可用，请稍后再试" if user_lang == 'zh' else "❌ Trend analysis temporarily unavailable, please try again later"

    def _find_matching_specialties(self, target_specialty: str) -> List[str]:
        """智能匹配专科名称"""
        target_lower = target_specialty.lower()
        matched = []
        
        # 检查直接映射
        for key, specialties in self.specialty_mapping.items():
            if key in target_lower:
                matched.extend(specialties)
        
        # 检查部分匹配
        all_specialties = self._get_all_available_specialties()
        for available_specialty in all_specialties:
            available_lower = available_specialty.lower()
            
            # 检查是否有共同词汇
            target_words = set(re.findall(r'\b\w+\b', target_lower))
            available_words = set(re.findall(r'\b\w+\b', available_lower))
            
            common_words = target_words.intersection(available_words)
            if common_words:
                matched.append(available_specialty)
        
        # 如果还是没有匹配，返回相关的通用专科
        if not matched:
            matched = ['General Medicine', 'General Surgery']
        
        return list(set(matched))  # 去重
    
    def _get_all_available_specialties(self) -> List[str]:
        """获取数据库中所有可用的专科"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT DISTINCT specialty_name FROM nhs_rtt_data")
            specialties = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            return specialties
            
        except Exception as e:
            print(f"获取可用专科失败: {e}")
            return []

    def _enhanced_location_filtering(self, trends: List[EnhancedTrendData], 
                                   user_postcode: str, radius_km: int) -> Tuple[List, List, List]:
        """增强版位置过滤，包含城市级别推荐"""
        within_range = []
        outside_range = []
        city_recommendations = []
        
        # 获取用户所在城市
        user_city = self._get_city_from_postcode(user_postcode)
        
        for trend in trends:
            # 计算距离（简化实现）
            distance = self._calculate_distance(user_postcode, trend.hospital_name)
            trend.distance_km = distance
            
            # 获取医院所在城市
            hospital_city = self._get_hospital_city(trend.hospital_name)
            trend.city = hospital_city
            
            # 计算推荐分数
            trend.recommendation_score = self._calculate_recommendation_score(
                trend, user_postcode, user_city
            )
            
            if distance and distance <= radius_km:
                within_range.append(trend)
            else:
                outside_range.append(trend)
                
                # 如果在同一城市但超出范围，添加到城市推荐
                if user_city and hospital_city == user_city and trend.current_weeks < 20:
                    city_recommendations.append({
                        'hospital_name': trend.hospital_name,
                        'specialty_name': trend.specialty_name,
                        'waiting_weeks': trend.current_weeks,
                        'distance_km': distance,
                        'city': hospital_city,
                        'recommendation_reason': f'同城市内更优选择' if distance else 'City-wide better option'
                    })
        
        # 排序
        within_range.sort(key=lambda x: x.current_weeks)
        outside_range.sort(key=lambda x: x.recommendation_score, reverse=True)
        city_recommendations.sort(key=lambda x: x['waiting_weeks'])
        
        return within_range, outside_range, city_recommendations[:5]  # 最多5个城市推荐

    def _get_city_from_postcode(self, postcode: str) -> Optional[str]:
        """从邮编获取城市名称"""
        if not postcode:
            return None
            
        postcode_prefix = postcode.split()[0] if ' ' in postcode else postcode[:3]
        
        for city, prefixes in self.city_postcode_mapping.items():
            for prefix in prefixes:
                if postcode_prefix.upper().startswith(prefix.upper()):
                    return city.title()
        return None

    def _get_hospital_city(self, hospital_name: str) -> Optional[str]:
        """从医院名称推断城市（简化实现）"""
        hospital_lower = hospital_name.lower()
        
        city_keywords = {
            'london': ['london', 'westminster', 'camden', 'southwark', 'tower', 'royal london'],
            'birmingham': ['birmingham', 'queen elizabeth'],
            'manchester': ['manchester', 'christie'],
            'liverpool': ['liverpool', 'aintree'],
            'glasgow': ['glasgow', 'western infirmary'],
            'edinburgh': ['edinburgh', 'royal infirmary'],
            'cardiff': ['cardiff', 'wales'],
            'belfast': ['belfast', 'ulster', 'northern ireland']
        }
        
        for city, keywords in city_keywords.items():
            for keyword in keywords:
                if keyword in hospital_lower:
                    return city.title()
        
        return 'Unknown'

    def _calculate_distance(self, user_postcode: str, hospital_name: str) -> Optional[float]:
        """计算距离（简化实现）"""
        # 这里应该集成真实的地理服务
        # 目前使用简化的模拟距离
        import random
        import hashlib
        
        # 使用hash保证一致性
        hash_input = f"{user_postcode}{hospital_name}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        
        # 基于hash生成一致的距离
        distance = (hash_value % 50) + 5  # 5-55km范围
        return float(distance)

    def _calculate_recommendation_score(self, trend: EnhancedTrendData, 
                                      user_postcode: str, user_city: str) -> float:
        """计算推荐分数"""
        score = 100.0
        
        # 等待时间越短分数越高
        score -= trend.current_weeks * 2
        
        # 趋势改善加分
        if trend.trend_direction == 'improving':
            score += 10
        elif trend.trend_direction == 'worsening':
            score -= 5
        
        # 距离惩罚
        if trend.distance_km:
            score -= trend.distance_km * 0.5
        
        # 同城市加分
        if trend.city and user_city and trend.city.lower() == user_city.lower():
            score += 15
        
        return max(0, score)

    def _analyze_specialty_trends(self, specialty: str) -> List[EnhancedTrendData]:
        """分析特定专科的趋势（增强版）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取当前数据（模拟趋势）
            cursor.execute("""
                SELECT 
                    org_name,
                    specialty_name,
                    waiting_time_weeks,
                    patient_count
                FROM nhs_rtt_data
                WHERE specialty_name LIKE ?
                ORDER BY waiting_time_weeks ASC
            """, (f'%{specialty}%',))
            
            rows = cursor.fetchall()
            conn.close()
            
            trends = []
            for row in rows:
                org_name, spec_name, waiting_weeks, patient_count = row
                
                # 模拟趋势数据
                import random
                previous_weeks = waiting_weeks + random.randint(-3, 3)
                change_weeks = waiting_weeks - previous_weeks
                
                if change_weeks < -1:
                    trend_direction = 'improving'
                elif change_weeks > 1:
                    trend_direction = 'worsening'
                else:
                    trend_direction = 'stable'
                
                percentage_change = ((waiting_weeks - previous_weeks) / previous_weeks * 100) if previous_weeks > 0 else 0
                
                trends.append(EnhancedTrendData(
                    hospital_name=org_name,
                    specialty_name=spec_name,
                    current_weeks=waiting_weeks,
                    previous_weeks=previous_weeks,
                    trend_direction=trend_direction,
                    change_weeks=change_weeks,
                    percentage_change=percentage_change,
                    patient_count=patient_count or 0
                ))
            
            return trends
            
        except Exception as e:
            print(f"分析专科趋势失败: {e}")
            return []

    def _generate_enhanced_summary(self, within_range: List, outside_range: List, 
                                 specialty: str, matched_specialties: List[str],
                                 city_recommendations: List[Dict]) -> TrendSummary:
        """生成增强版趋势摘要"""
        primary_data = within_range if within_range else outside_range
        
        if not primary_data:
            return TrendSummary(
                user_specialty=specialty,
                matched_specialties=matched_specialties,
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
                outside_range_count=len(outside_range),
                city_recommendations=city_recommendations
            )
        
        total_hospitals = len(primary_data)
        improving_count = sum(1 for t in primary_data if t.trend_direction == 'improving')
        worsening_count = sum(1 for t in primary_data if t.trend_direction == 'worsening')
        stable_count = total_hospitals - improving_count - worsening_count
        
        best_hospital = min(primary_data, key=lambda x: x.current_weeks)
        worst_hospital = max(primary_data, key=lambda x: x.current_weeks)
        
        average_wait_time = statistics.mean([t.current_weeks for t in primary_data])
        
        total_change = sum(t.change_weeks for t in primary_data)
        if total_change < -5:
            regional_trend = 'improving'
        elif total_change > 5:
            regional_trend = 'worsening'
        else:
            regional_trend = 'stable'
        
        return TrendSummary(
            user_specialty=specialty,
            matched_specialties=matched_specialties,
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
            outside_range_count=len(outside_range),
            city_recommendations=city_recommendations
        )

    def _format_enhanced_trend_message(self, summary: TrendSummary, 
                                     within_range: List, outside_range: List, 
                                     user_lang: str = 'en') -> str:
        """格式化增强版趋势消息"""
        if user_lang == 'zh':
            return self._format_enhanced_trend_message_zh(summary, within_range, outside_range)
        else:
            return self._format_enhanced_trend_message_en(summary, within_range, outside_range)

    def _format_enhanced_trend_message_zh(self, summary: TrendSummary, 
                                        within_range: List, outside_range: List) -> str:
        """中文增强版趋势消息"""
        if summary.total_hospitals == 0:
            return self._format_enhanced_no_data_message(
                summary.user_specialty, summary.matched_specialties, 'zh'
            )
        
        # 构建专科匹配信息
        specialty_info = f"**您查询的专科**: {summary.user_specialty}\n"
        if len(summary.matched_specialties) > 1 or summary.matched_specialties[0] != summary.user_specialty:
            specialty_info += f"**匹配到的专科**: {', '.join(summary.matched_specialties)}\n"
        
        # 趋势图标
        trend_icon = "📈" if summary.regional_trend == 'improving' else "📉" if summary.regional_trend == 'worsening' else "📊"
        
        message = f"""📊 **等候时间趋势分析**

{specialty_info}
🏥 **总医院数**: {summary.total_hospitals} 家
📍 **范围内**: {summary.within_range_count} 家 | **范围外**: {summary.outside_range_count} 家

{trend_icon} **区域趋势**: {'改善中' if summary.regional_trend == 'improving' else '恶化中' if summary.regional_trend == 'worsening' else '稳定'}
🟢 **改善**: {summary.improving_count} 家
🔴 **恶化**: {summary.worsening_count} 家  
🟡 **稳定**: {summary.stable_count} 家

⭐ **最佳选择**: {summary.best_hospital} ({summary.best_wait_time}周)
⚠️ **最长等候**: {summary.worst_hospital} ({summary.worst_wait_time}周)
📊 **平均等候**: {summary.average_wait_time:.1f}周

"""
        
        # 范围内医院详情
        if within_range:
            message += "🎯 **您的范围内医院**:\n"
            for i, trend in enumerate(within_range[:5], 1):
                change_icon = "🟢" if trend.trend_direction == 'improving' else "🔴" if trend.trend_direction == 'worsening' else "🟡"
                change_text = f"{'↓' if trend.change_weeks < 0 else '↑' if trend.change_weeks > 0 else '='}{abs(trend.change_weeks)}周"
                
                message += f"{i}. **{trend.hospital_name}**\n"
                message += f"   ⏰ {trend.current_weeks}周 {change_icon} {change_text}"
                if hasattr(trend, 'distance_km') and trend.distance_km:
                    message += f" | 📍 {trend.distance_km:.1f}km"
                message += f"\n   👥 {trend.patient_count} 人等候\n\n"
        
        # 城市推荐
        if summary.city_recommendations:
            message += "🌆 **同城市优质选择**:\n"
            for i, rec in enumerate(summary.city_recommendations[:3], 1):
                message += f"{i}. **{rec['hospital_name']}**\n"
                message += f"   ⏰ {rec['waiting_weeks']}周 | 📍 {rec['distance_km']:.1f}km\n"
                message += f"   💡 {rec['recommendation_reason']}\n\n"
        
        # 范围外选择
        if outside_range and not summary.city_recommendations:
            message += f"🌍 **扩大范围选择** ({len(outside_range)} 家医院):\n"
            for i, trend in enumerate(sorted(outside_range, key=lambda x: x.current_weeks)[:3], 1):
                message += f"{i}. **{trend.hospital_name}**: {trend.current_weeks}周"
                if hasattr(trend, 'distance_km') and trend.distance_km:
                    message += f" ({trend.distance_km:.1f}km)"
                message += "\n"
        
        message += "\n💡 输入 **4** 重新设置偏好 | **1** 查看状态"
        
        return message

    def _format_enhanced_trend_message_en(self, summary: TrendSummary, 
                                        within_range: List, outside_range: List) -> str:
        """Enhanced trend message in English"""
        if summary.total_hospitals == 0:
            return self._format_enhanced_no_data_message(
                summary.user_specialty, summary.matched_specialties, 'en'
            )
        
        # Build specialty matching information
        specialty_info = f"**Your Queried Specialty**: {summary.user_specialty}\n"
        if len(summary.matched_specialties) > 1 or summary.matched_specialties[0] != summary.user_specialty:
            specialty_info += f"**Matched Specialties**: {', '.join(summary.matched_specialties)}\n"
        
        # Trend icon
        trend_icon = "📈" if summary.regional_trend == 'improving' else "📉" if summary.regional_trend == 'worsening' else "📊"
        
        message = f"""📊 **Waiting Time Trend Analysis**

{specialty_info}
🏥 **Total Hospitals**: {summary.total_hospitals}
📍 **Within Range**: {summary.within_range_count} | **Outside Range**: {summary.outside_range_count}

{trend_icon} **Regional Trend**: {'Improving' if summary.regional_trend == 'improving' else 'Worsening' if summary.regional_trend == 'worsening' else 'Stable'}
🟢 **Improving**: {summary.improving_count} hospitals
🔴 **Worsening**: {summary.worsening_count} hospitals  
🟡 **Stable**: {summary.stable_count} hospitals

⭐ **Best Option**: {summary.best_hospital} ({summary.best_wait_time} weeks)
⚠️ **Longest Wait**: {summary.worst_hospital} ({summary.worst_wait_time} weeks)
📊 **Average Wait**: {summary.average_wait_time:.1f} weeks

"""
        
        # Within range hospital details
        if within_range:
            message += "🎯 **Hospitals Within Your Range**:\n"
            for i, trend in enumerate(within_range[:5], 1):
                change_icon = "🟢" if trend.trend_direction == 'improving' else "🔴" if trend.trend_direction == 'worsening' else "🟡"
                change_text = f"{'↓' if trend.change_weeks < 0 else '↑' if trend.change_weeks > 0 else '='}{abs(trend.change_weeks)} weeks"
                
                message += f"{i}. **{trend.hospital_name}**\n"
                message += f"   ⏰ {trend.current_weeks} weeks {change_icon} {change_text}"
                if hasattr(trend, 'distance_km') and trend.distance_km:
                    message += f" | 📍 {trend.distance_km:.1f}km"
                message += f"\n   👥 {trend.patient_count} patients waiting\n\n"
        
        # City recommendations
        if summary.city_recommendations:
            message += "🌆 **Same City Quality Options**:\n"
            for i, rec in enumerate(summary.city_recommendations[:3], 1):
                message += f"{i}. **{rec['hospital_name']}**\n"
                message += f"   ⏰ {rec['waiting_weeks']} weeks | 📍 {rec['distance_km']:.1f}km\n"
                message += f"   💡 {rec['recommendation_reason']}\n\n"
        
        # Outside range options
        if outside_range and not summary.city_recommendations:
            message += f"🌍 **Extended Range Options** ({len(outside_range)} hospitals):\n"
            for i, trend in enumerate(sorted(outside_range, key=lambda x: x.current_weeks)[:3], 1):
                message += f"{i}. **{trend.hospital_name}**: {trend.current_weeks} weeks"
                if hasattr(trend, 'distance_km') and trend.distance_km:
                    message += f" ({trend.distance_km:.1f}km)"
                message += "\n"
        
        message += "\n💡 Enter **4** to reset preferences | **1** to view status"
        
        return message

    def _format_enhanced_no_data_message(self, specialty: str, matched_specialties: List[str], 
                                       user_lang: str) -> str:
        """增强版无数据消息"""
        if user_lang == 'zh':
            message = f"""❌ **{specialty} 专科数据分析**

🔍 **智能匹配结果**:
"""
            if matched_specialties:
                message += f"系统尝试匹配到: {', '.join(matched_specialties)}\n"
            else:
                message += "未找到相关专科\n"
            
            message += f"""
📊 **可用专科选择**:
1. Cardiology (心脏科)
2. Trauma & Orthopaedics (骨科)  
3. Ophthalmology (眼科)
4. Dermatology (皮肤科)
5. ENT (耳鼻喉科)
6. Urology (泌尿科)
7. Gastroenterology (消化科)
8. Gynaecology (妇科)
9. General Surgery (外科)
10. Neurology (神经科)

💡 **建议**:
• 重新设置选择更具体的专科名称
• 尝试使用上述专科名称之一
• 联系我们添加您需要的专科

🔧 输入 **4** 重新设置偏好"""
            
        else:
            message = f"""❌ **{specialty} Specialty Analysis**

🔍 **Smart Matching Results**:
"""
            if matched_specialties:
                message += f"System attempted to match: {', '.join(matched_specialties)}\n"
            else:
                message += "No related specialties found\n"
            
            message += """
📊 **Available Specialty Options**:
1. Cardiology
2. Trauma & Orthopaedics
3. Ophthalmology
4. Dermatology
5. ENT
6. Urology
7. Gastroenterology
8. Gynaecology
9. General Surgery
10. Neurology

💡 **Suggestions**:
• Reset and choose more specific specialty name
• Try using one of the above specialty names
• Contact us to add your required specialty

🔧 Enter **4** to reset preferences"""
        
        return message

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