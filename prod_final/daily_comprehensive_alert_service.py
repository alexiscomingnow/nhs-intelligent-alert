#!/usr/bin/env python3
"""
NHS每日全面提醒服务
为每个用户提供个性化的等候时间分析、趋势预测和解决方案建议
"""

import sqlite3
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enhanced_waiting_trends_service import EnhancedWaitingTrendsService
from geographic_service import GeographicService

logger = logging.getLogger(__name__)

@dataclass
class DailyRecommendation:
    """每日推荐建议"""
    recommendation_type: str  # immediate_action, monitor, explore_alternatives, private_options
    title: str
    description: str
    priority: int  # 1=低, 5=高
    action_items: List[str]
    estimated_impact: str  # 预期效果
    time_frame: str  # 时间框架

@dataclass
class UserDailyAlert:
    """用户每日提醒"""
    user_id: str
    alert_date: datetime
    current_status: Dict
    trend_analysis: Dict
    recommendations: List[DailyRecommendation]
    key_insights: List[str]
    action_summary: str

class DailyComprehensiveAlertService:
    """每日全面提醒服务"""
    
    def __init__(self, db_path: str = 'nhs_alerts.db'):
        self.db_path = db_path
        self.trends_service = EnhancedWaitingTrendsService(db_path)
        self.geo_service = GeographicService(db_path)
        
        # 初始化日志
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    async def generate_daily_alerts_for_all_users(self) -> List[UserDailyAlert]:
        """为所有活跃用户生成每日提醒"""
        try:
            users = self._get_active_users()
            daily_alerts = []
            
            for user in users:
                try:
                    alert = await self.generate_user_daily_alert(user)
                    if alert:
                        daily_alerts.append(alert)
                        # 发送提醒
                        await self._send_daily_alert(user, alert)
                except Exception as e:
                    self.logger.error(f"为用户 {user['user_id']} 生成每日提醒失败: {e}")
                    continue
            
            return daily_alerts
            
        except Exception as e:
            self.logger.error(f"生成每日提醒失败: {e}")
            return []
    
    async def generate_user_daily_alert(self, user: Dict) -> Optional[UserDailyAlert]:
        """为单个用户生成每日提醒"""
        try:
            user_id = user['user_id']
            user_lang = user.get('language', 'en')
            
            # 1. 获取当前状态
            current_status = await self._get_user_current_status(user)
            
            # 2. 趋势分析
            trend_analysis = await self._analyze_user_trends(user)
            
            # 3. 生成个性化推荐
            recommendations = await self._generate_personalized_recommendations(user, current_status, trend_analysis)
            
            # 4. 提取关键洞察
            key_insights = await self._extract_key_insights(user, current_status, trend_analysis, recommendations)
            
            # 5. 生成行动摘要
            action_summary = self._create_action_summary(recommendations, user_lang)
            
            return UserDailyAlert(
                user_id=user_id,
                alert_date=datetime.now(),
                current_status=current_status,
                trend_analysis=trend_analysis,
                recommendations=recommendations,
                key_insights=key_insights,
                action_summary=action_summary
            )
            
        except Exception as e:
            self.logger.error(f"生成用户每日提醒失败: {e}")
            return None
    
    async def _get_user_current_status(self, user: Dict) -> Dict:
        """获取用户当前状态"""
        try:
            specialty = user.get('specialty', '')
            postcode = user.get('postcode', '')
            radius_km = user.get('radius_km', 25)
            threshold_weeks = user.get('threshold_weeks', 12)
            
            # 获取附近医院的等候时间
            hospitals = self.geo_service.find_nearby_hospitals_with_waiting_times(
                postcode, specialty, radius_km
            )
            
            if not hospitals:
                return {'status': 'no_data', 'message': '暂无相关数据'}
            
            # 分析当前状况
            min_wait = min(h.get('waiting_weeks', 999) for h in hospitals)
            avg_wait = sum(h.get('waiting_weeks', 0) for h in hospitals) / len(hospitals)
            max_wait = max(h.get('waiting_weeks', 0) for h in hospitals)
            
            # 找到最优选择
            best_options = sorted(hospitals, key=lambda x: x.get('waiting_weeks', 999))[:3]
            
            # 检查是否有符合阈值的选择
            threshold_options = [h for h in hospitals if h.get('waiting_weeks', 999) <= threshold_weeks]
            
            return {
                'status': 'available',
                'total_hospitals': len(hospitals),
                'min_wait_weeks': min_wait,
                'avg_wait_weeks': round(avg_wait, 1),
                'max_wait_weeks': max_wait,
                'best_options': best_options,
                'threshold_met': len(threshold_options) > 0,
                'threshold_options': threshold_options,
                'specialty': specialty,
                'search_radius': radius_km,
                'user_threshold': threshold_weeks
            }
            
        except Exception as e:
            self.logger.error(f"获取用户当前状态失败: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def _analyze_user_trends(self, user: Dict) -> Dict:
        """分析用户相关的趋势"""
        try:
            # 使用现有的趋势分析服务
            trends_text = self.trends_service.get_enhanced_user_trends(
                user['user_id'], 
                user.get('language', 'en')
            )
            
            # 提取数值化的趋势数据
            trend_data = self._extract_trend_metrics(user)
            
            return {
                'trend_summary': trends_text,
                'numerical_trends': trend_data,
                'analysis_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"分析用户趋势失败: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _extract_trend_metrics(self, user: Dict) -> Dict:
        """提取趋势指标"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            specialty = user.get('specialty', '')
            
            # 获取过去4周的数据变化
            cursor.execute("""
                SELECT org_name, waiting_time_weeks, created_at
                FROM nhs_rtt_data 
                WHERE specialty_name LIKE ? 
                AND created_at >= date('now', '-28 days')
                ORDER BY created_at DESC
            """, (f'%{specialty}%',))
            
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                return {'status': 'no_data'}
            
            # 分析趋势
            recent_data = {}
            for org_name, wait_weeks, created_at in rows:
                if org_name not in recent_data:
                    recent_data[org_name] = []
                recent_data[org_name].append({
                    'weeks': wait_weeks,
                    'date': created_at
                })
            
            # 计算变化
            trend_summary = {
                'improving_hospitals': 0,
                'worsening_hospitals': 0,
                'stable_hospitals': 0,
                'avg_change': 0,
                'significant_changes': []
            }
            
            total_change = 0
            hospital_count = 0
            
            for hospital, data_points in recent_data.items():
                if len(data_points) >= 2:
                    latest = data_points[0]['weeks']
                    previous = data_points[-1]['weeks']
                    change = latest - previous
                    
                    total_change += change
                    hospital_count += 1
                    
                    if change < -1:
                        trend_summary['improving_hospitals'] += 1
                    elif change > 1:
                        trend_summary['worsening_hospitals'] += 1
                    else:
                        trend_summary['stable_hospitals'] += 1
                    
                    if abs(change) >= 3:
                        trend_summary['significant_changes'].append({
                            'hospital': hospital,
                            'change': change,
                            'current_weeks': latest
                        })
            
            if hospital_count > 0:
                trend_summary['avg_change'] = round(total_change / hospital_count, 1)
            
            return trend_summary
            
        except Exception as e:
            self.logger.error(f"提取趋势指标失败: {e}")
            return {'status': 'error'}
    
    async def _generate_personalized_recommendations(self, user: Dict, current_status: Dict, trend_analysis: Dict) -> List[DailyRecommendation]:
        """生成个性化推荐建议"""
        try:
            recommendations = []
            user_lang = user.get('language', 'en')
            
            # 1. 即时行动建议
            immediate_actions = await self._generate_immediate_action_recommendations(user, current_status, user_lang)
            recommendations.extend(immediate_actions)
            
            # 2. 监控建议
            monitoring_recommendations = await self._generate_monitoring_recommendations(user, trend_analysis, user_lang)
            recommendations.extend(monitoring_recommendations)
            
            # 3. 替代方案建议
            alternative_recommendations = await self._generate_alternative_recommendations(user, current_status, user_lang)
            recommendations.extend(alternative_recommendations)
            
            # 4. 私立医疗选择
            private_recommendations = await self._generate_private_healthcare_recommendations(user, current_status, user_lang)
            recommendations.extend(private_recommendations)
            
            # 5. 健康管理建议
            health_management_recommendations = await self._generate_health_management_recommendations(user, user_lang)
            recommendations.extend(health_management_recommendations)
            
            # 按优先级排序
            recommendations.sort(key=lambda x: x.priority, reverse=True)
            
            return recommendations[:8]  # 限制最多8个推荐
            
        except Exception as e:
            self.logger.error(f"生成个性化推荐失败: {e}")
            return []
    
    async def _generate_immediate_action_recommendations(self, user: Dict, current_status: Dict, user_lang: str) -> List[DailyRecommendation]:
        """生成即时行动建议"""
        recommendations = []
        
        try:
            if current_status.get('threshold_met'):
                # 有符合阈值的选择
                threshold_options = current_status.get('threshold_options', [])
                best_option = threshold_options[0] if threshold_options else None
                
                if best_option and user_lang == 'zh':
                    recommendations.append(DailyRecommendation(
                        recommendation_type="immediate_action",
                        title="🎯 立即预约机会",
                        description=f"发现符合您设置的{current_status['user_threshold']}周阈值的医院选择！",
                        priority=5,
                        action_items=[
                            f"联系{best_option['provider_name']}预约{user['specialty']}",
                            f"准备转诊信和相关医疗记录",
                            f"确认具体预约时间和地点",
                            "询问具体治疗流程和注意事项"
                        ],
                        estimated_impact="可节省数周等候时间",
                        time_frame="立即行动"
                    ))
                elif best_option:
                    recommendations.append(DailyRecommendation(
                        recommendation_type="immediate_action",
                        title="🎯 Immediate Booking Opportunity",
                        description=f"Found options within your {current_status['user_threshold']}-week threshold!",
                        priority=5,
                        action_items=[
                            f"Contact {best_option['provider_name']} for {user['specialty']} appointment",
                            "Prepare referral letter and medical records",
                            "Confirm specific appointment time and location",
                            "Ask about treatment process and requirements"
                        ],
                        estimated_impact="Save several weeks of waiting time",
                        time_frame="Take action now"
                    ))
            
            elif current_status.get('min_wait_weeks', 999) <= current_status.get('user_threshold', 12) + 4:
                # 接近阈值的选择
                if user_lang == 'zh':
                    recommendations.append(DailyRecommendation(
                        recommendation_type="immediate_action",
                        title="⚡ 近期预约机会",
                        description=f"最短等候时间为{current_status['min_wait_weeks']}周，接近您的期望",
                        priority=4,
                        action_items=[
                            "联系候补名单，询问是否有取消的预约",
                            "考虑扩大搜索范围到更远的医院",
                            "与GP讨论加急转诊的可能性",
                            "准备完整的医疗资料以加快流程"
                        ],
                        estimated_impact="可能提前数周获得治疗",
                        time_frame="本周内行动"
                    ))
                else:
                    recommendations.append(DailyRecommendation(
                        recommendation_type="immediate_action",
                        title="⚡ Near-term Booking Opportunity",
                        description=f"Shortest wait is {current_status['min_wait_weeks']} weeks, close to your preference",
                        priority=4,
                        action_items=[
                            "Join cancellation lists for earlier appointments",
                            "Consider expanding search radius to more distant hospitals",
                            "Discuss urgent referral options with your GP",
                            "Prepare complete medical documentation to expedite process"
                        ],
                        estimated_impact="Potentially advance treatment by several weeks",
                        time_frame="Take action this week"
                    ))
            
        except Exception as e:
            self.logger.error(f"生成即时行动建议失败: {e}")
        
        return recommendations
    
    async def _generate_monitoring_recommendations(self, user: Dict, trend_analysis: Dict, user_lang: str) -> List[DailyRecommendation]:
        """生成监控建议"""
        recommendations = []
        
        try:
            trends = trend_analysis.get('numerical_trends', {})
            
            if trends.get('improving_hospitals', 0) > trends.get('worsening_hospitals', 0):
                # 整体趋势改善
                if user_lang == 'zh':
                    recommendations.append(DailyRecommendation(
                        recommendation_type="monitor",
                        title="📈 积极趋势监控",
                        description=f"有{trends.get('improving_hospitals', 0)}家医院等候时间在改善",
                        priority=3,
                        action_items=[
                            "密切关注改善最快的医院",
                            "设置更积极的阈值提醒",
                            "准备快速响应突然缩短的等候时间",
                            "考虑联系这些医院了解最新情况"
                        ],
                        estimated_impact="抓住等候时间快速下降的机会",
                        time_frame="持续监控，每周检查"
                    ))
                else:
                    recommendations.append(DailyRecommendation(
                        recommendation_type="monitor",
                        title="📈 Positive Trend Monitoring",
                        description=f"{trends.get('improving_hospitals', 0)} hospitals showing improving wait times",
                        priority=3,
                        action_items=[
                            "Closely monitor fastest-improving hospitals",
                            "Set more aggressive threshold alerts",
                            "Prepare to respond quickly to sudden wait time drops",
                            "Consider contacting these hospitals for latest updates"
                        ],
                        estimated_impact="Catch opportunities when wait times drop rapidly",
                        time_frame="Continuous monitoring, check weekly"
                    ))
            
            elif trends.get('significant_changes'):
                # 有显著变化
                significant_changes = trends['significant_changes']
                if user_lang == 'zh':
                    recommendations.append(DailyRecommendation(
                        recommendation_type="monitor",
                        title="🔍 重点变化监控",
                        description=f"发现{len(significant_changes)}家医院有显著等候时间变化",
                        priority=3,
                        action_items=[
                            "重点关注变化最大的医院",
                            "分析变化原因（新政策、资源调整等）",
                            "预测未来趋势发展方向",
                            "调整个人等候策略"
                        ],
                        estimated_impact="基于数据做出更明智的选择",
                        time_frame="每周深度分析"
                    ))
                else:
                    recommendations.append(DailyRecommendation(
                        recommendation_type="monitor",
                        title="🔍 Significant Change Monitoring",
                        description=f"Found {len(significant_changes)} hospitals with significant wait time changes",
                        priority=3,
                        action_items=[
                            "Focus on hospitals with largest changes",
                            "Analyze reasons for changes (new policies, resource adjustments)",
                            "Predict future trend developments",
                            "Adjust personal waiting strategy"
                        ],
                        estimated_impact="Make smarter choices based on data",
                        time_frame="Weekly deep analysis"
                    ))
            
        except Exception as e:
            self.logger.error(f"生成监控建议失败: {e}")
        
        return recommendations
    
    async def _generate_alternative_recommendations(self, user: Dict, current_status: Dict, user_lang: str) -> List[DailyRecommendation]:
        """生成替代方案建议"""
        recommendations = []
        
        try:
            # 建议扩大搜索范围
            if current_status.get('total_hospitals', 0) < 5:
                if user_lang == 'zh':
                    recommendations.append(DailyRecommendation(
                        recommendation_type="explore_alternatives",
                        title="🌍 扩大搜索范围",
                        description=f"当前搜索范围内仅有{current_status.get('total_hospitals', 0)}家医院",
                        priority=3,
                        action_items=[
                            f"将搜索半径从{current_status.get('search_radius', 25)}公里扩大到50公里",
                            "考虑伦敦以外的专科中心",
                            "研究苏格兰、威尔士的医疗选择",
                            "了解跨境医疗的可能性"
                        ],
                        estimated_impact="发现更多更快的治疗选择",
                        time_frame="本周扩大搜索"
                    ))
                else:
                    recommendations.append(DailyRecommendation(
                        recommendation_type="explore_alternatives",
                        title="🌍 Expand Search Area",
                        description=f"Only {current_status.get('total_hospitals', 0)} hospitals in current search area",
                        priority=3,
                        action_items=[
                            f"Expand search radius from {current_status.get('search_radius', 25)}km to 50km",
                            "Consider specialist centres outside London",
                            "Research options in Scotland, Wales",
                            "Explore cross-border healthcare possibilities"
                        ],
                        estimated_impact="Discover more and faster treatment options",
                        time_frame="Expand search this week"
                    ))
            
            # 建议相关专科
            specialty = user.get('specialty', '')
            related_specialties = self._get_related_specialties(specialty)
            
            if related_specialties and user_lang == 'zh':
                recommendations.append(DailyRecommendation(
                    recommendation_type="explore_alternatives",
                    title="🔀 相关专科选择",
                    description=f"考虑{specialty}的相关专科，可能有更短等候时间",
                    priority=2,
                    action_items=[
                        f"了解{', '.join(related_specialties[:3])}等相关专科",
                        "与GP讨论转诊到相关专科的可能性",
                        "研究相关专科的治疗方法差异",
                        "比较不同专科的等候时间"
                    ],
                    estimated_impact="通过相关专科获得更快治疗",
                    time_frame="与GP讨论（2周内）"
                ))
            elif related_specialties:
                recommendations.append(DailyRecommendation(
                    recommendation_type="explore_alternatives",
                    title="🔀 Related Specialty Options",
                    description=f"Consider related specialties to {specialty} which may have shorter waits",
                    priority=2,
                    action_items=[
                        f"Research {', '.join(related_specialties[:3])} and other related specialties",
                        "Discuss referral to related specialties with your GP",
                        "Compare treatment approaches between specialties",
                        "Compare waiting times across different specialties"
                    ],
                    estimated_impact="Achieve faster treatment through related specialties",
                    time_frame="Discuss with GP (within 2 weeks)"
                ))
            
        except Exception as e:
            self.logger.error(f"生成替代方案建议失败: {e}")
        
        return recommendations
    
    async def _generate_private_healthcare_recommendations(self, user: Dict, current_status: Dict, user_lang: str) -> List[DailyRecommendation]:
        """生成私立医疗建议"""
        recommendations = []
        
        try:
            min_wait = current_status.get('min_wait_weeks', 999)
            
            if min_wait > 8:  # 如果NHS等候时间超过8周
                if user_lang == 'zh':
                    recommendations.append(DailyRecommendation(
                        recommendation_type="private_options",
                        title="🏥 私立医疗考虑",
                        description=f"NHS最短等候{min_wait}周，私立医疗可能更快",
                        priority=3,
                        action_items=[
                            "研究主要私立医疗机构（Spire, BMI, Nuffield等）",
                            "了解私立医疗保险选择",
                            "比较私立医疗费用和NHS等候时间成本",
                            "考虑医疗贷款或分期付款选择",
                            "查询是否有慈善机构资助计划"
                        ],
                        estimated_impact="可能将等候时间缩短至2-4周",
                        time_frame="本月内研究评估"
                    ))
                else:
                    recommendations.append(DailyRecommendation(
                        recommendation_type="private_options",
                        title="🏥 Private Healthcare Consideration",
                        description=f"NHS shortest wait is {min_wait} weeks, private care may be faster",
                        priority=3,
                        action_items=[
                            "Research major private healthcare providers (Spire, BMI, Nuffield, etc.)",
                            "Explore private health insurance options",
                            "Compare private costs vs NHS waiting time costs",
                            "Consider medical loans or payment plans",
                            "Check for charity funding programs"
                        ],
                        estimated_impact="Could reduce waiting time to 2-4 weeks",
                        time_frame="Research and evaluate this month"
                    ))
            
            if user_lang == 'zh':
                recommendations.append(DailyRecommendation(
                    recommendation_type="private_options",
                    title="💰 医疗费用规划",
                    description="制定医疗费用应急计划",
                    priority=2,
                    action_items=[
                        "建立医疗应急基金",
                        "了解HSA/医疗储蓄账户",
                        "研究医疗保险追加选择",
                        "考虑海外医疗旅游选择",
                        "了解公司医疗福利"
                    ],
                    estimated_impact="为未来医疗需求做好财务准备",
                    time_frame="长期规划（3-6个月）"
                ))
            else:
                recommendations.append(DailyRecommendation(
                    recommendation_type="private_options",
                    title="💰 Healthcare Financial Planning",
                    description="Develop medical expense contingency plan",
                    priority=2,
                    action_items=[
                        "Build medical emergency fund",
                        "Explore HSA/medical savings accounts",
                        "Research supplementary health insurance",
                        "Consider medical tourism options abroad",
                        "Review employer medical benefits"
                    ],
                    estimated_impact="Prepare financially for future medical needs",
                    time_frame="Long-term planning (3-6 months)"
                ))
            
        except Exception as e:
            self.logger.error(f"生成私立医疗建议失败: {e}")
        
        return recommendations
    
    async def _generate_health_management_recommendations(self, user: Dict, user_lang: str) -> List[DailyRecommendation]:
        """生成健康管理建议"""
        recommendations = []
        
        try:
            specialty = user.get('specialty', '').lower()
            
            # 基于专科提供针对性建议
            if 'cardiology' in specialty or '心脏' in specialty:
                if user_lang == 'zh':
                    recommendations.append(DailyRecommendation(
                        recommendation_type="health_management",
                        title="❤️ 心脏健康维护",
                        description="在等候期间保护和改善心脏健康",
                        priority=4,
                        action_items=[
                            "采用地中海饮食模式",
                            "每天至少30分钟中等强度运动",
                            "监控血压和胆固醇水平",
                            "戒烟限酒，管理压力",
                            "定期与GP回顾病情变化"
                        ],
                        estimated_impact="可能改善病情，减少手术需要",
                        time_frame="立即开始，持续进行"
                    ))
                else:
                    recommendations.append(DailyRecommendation(
                        recommendation_type="health_management",
                        title="❤️ Cardiac Health Maintenance",
                        description="Protect and improve heart health while waiting",
                        priority=4,
                        action_items=[
                            "Adopt Mediterranean diet pattern",
                            "Minimum 30 minutes moderate exercise daily",
                            "Monitor blood pressure and cholesterol levels",
                            "Quit smoking, limit alcohol, manage stress",
                            "Regular GP reviews of condition changes"
                        ],
                        estimated_impact="May improve condition, potentially reduce surgery need",
                        time_frame="Start immediately, continue ongoing"
                    ))
            
            elif 'orthopaedics' in specialty or '骨科' in specialty:
                if user_lang == 'zh':
                    recommendations.append(DailyRecommendation(
                        recommendation_type="health_management",
                        title="🦴 骨科预康复",
                        description="等候期间保持和改善关节功能",
                        priority=4,
                        action_items=[
                            "进行物理治疗师指导的锻炼",
                            "保持健康体重减轻关节负担",
                            "使用热敷、冷敷缓解疼痛",
                            "学习正确的姿势和活动方式",
                            "考虑营养补充剂（维生素D、钙）"
                        ],
                        estimated_impact="减少疼痛，改善术后恢复",
                        time_frame="等候期间持续进行"
                    ))
                else:
                    recommendations.append(DailyRecommendation(
                        recommendation_type="health_management",
                        title="🦴 Orthopaedic Pre-habilitation",
                        description="Maintain and improve joint function while waiting",
                        priority=4,
                        action_items=[
                            "Follow physiotherapist-guided exercises",
                            "Maintain healthy weight to reduce joint stress",
                            "Use heat/cold therapy for pain relief",
                            "Learn proper posture and movement techniques",
                            "Consider nutritional supplements (Vitamin D, Calcium)"
                        ],
                        estimated_impact="Reduce pain, improve post-surgery recovery",
                        time_frame="Continue throughout waiting period"
                    ))
            
            # 通用健康建议
            if user_lang == 'zh':
                recommendations.append(DailyRecommendation(
                    recommendation_type="health_management",
                    title="🧘 整体健康优化",
                    description="利用等候时间全面提升健康状态",
                    priority=2,
                    action_items=[
                        "建立规律的睡眠计划（7-9小时）",
                        "练习冥想或正念减压",
                        "保持社交联系，寻求情感支持",
                        "学习疾病相关知识，成为积极患者",
                        "记录症状日记，为就诊做准备"
                    ],
                    estimated_impact="提高生活质量，更好应对治疗",
                    time_frame="融入日常生活"
                ))
            else:
                recommendations.append(DailyRecommendation(
                    recommendation_type="health_management",
                    title="🧘 Holistic Health Optimization",
                    description="Use waiting time to comprehensively improve health status",
                    priority=2,
                    action_items=[
                        "Establish regular sleep schedule (7-9 hours)",
                        "Practice meditation or mindfulness for stress reduction",
                        "Maintain social connections, seek emotional support",
                        "Learn about your condition, become an active patient",
                        "Keep symptom diary to prepare for appointments"
                    ],
                    estimated_impact="Improve quality of life, better treatment outcomes",
                    time_frame="Integrate into daily life"
                ))
            
        except Exception as e:
            self.logger.error(f"生成健康管理建议失败: {e}")
        
        return recommendations
    
    def _get_related_specialties(self, specialty: str) -> List[str]:
        """获取相关专科"""
        specialty_relations = {
            'Cardiology': ['Cardiothoracic Surgery', 'Vascular Surgery', 'Internal Medicine'],
            'Orthopaedics': ['Rheumatology', 'Pain Management', 'Neurosurgery'],
            'Trauma & Orthopaedics': ['Orthopaedics', 'Plastic Surgery', 'Rehabilitation'],
            'Neurology': ['Neurosurgery', 'Psychiatry', 'Rehabilitation'],
            'Gastroenterology': ['General Surgery', 'Hepatology', 'Nutrition'],
            'Urology': ['Nephrology', 'General Surgery', 'Oncology'],
            'ENT': ['Audiology', 'Plastic Surgery', 'Neurology'],
            'Ophthalmology': ['Neurology', 'Diabetes', 'Rheumatology'],
            'Dermatology': ['Plastic Surgery', 'Allergy', 'Rheumatology'],
            'Gynaecology': ['Endocrinology', 'Urology', 'General Surgery']
        }
        
        return specialty_relations.get(specialty, [])
    
    async def _extract_key_insights(self, user: Dict, current_status: Dict, trend_analysis: Dict, recommendations: List[DailyRecommendation]) -> List[str]:
        """提取关键洞察"""
        insights = []
        user_lang = user.get('language', 'en')
        
        try:
            # 1. 等候时间洞察
            min_wait = current_status.get('min_wait_weeks', 999)
            avg_wait = current_status.get('avg_wait_weeks', 999)
            threshold = current_status.get('user_threshold', 12)
            
            if current_status.get('threshold_met'):
                if user_lang == 'zh':
                    insights.append(f"🎯 好消息！有医院等候时间符合您的{threshold}周期望")
                else:
                    insights.append(f"🎯 Good news! Hospitals available within your {threshold}-week expectation")
            
            elif min_wait <= threshold + 4:
                if user_lang == 'zh':
                    insights.append(f"⚡ 最短等候{min_wait}周，接近您的期望，值得密切关注")
                else:
                    insights.append(f"⚡ Shortest wait is {min_wait} weeks, close to your expectation, worth monitoring closely")
            
            # 2. 趋势洞察
            trends = trend_analysis.get('numerical_trends', {})
            if trends.get('improving_hospitals', 0) > 0:
                if user_lang == 'zh':
                    insights.append(f"📈 积极信号：{trends['improving_hospitals']}家医院等候时间在缩短")
                else:
                    insights.append(f"📈 Positive signal: {trends['improving_hospitals']} hospitals showing shorter wait times")
            
            # 3. 行动洞察
            high_priority_recommendations = [r for r in recommendations if r.priority >= 4]
            if high_priority_recommendations:
                if user_lang == 'zh':
                    insights.append(f"🚀 建议优先关注：{high_priority_recommendations[0].title}")
                else:
                    insights.append(f"🚀 Priority focus recommended: {high_priority_recommendations[0].title}")
            
            # 4. 数据质量洞察
            total_hospitals = current_status.get('total_hospitals', 0)
            if total_hospitals < 3:
                if user_lang == 'zh':
                    insights.append("🌍 考虑扩大搜索范围以获得更多选择")
                else:
                    insights.append("🌍 Consider expanding search area for more options")
            
            # 5. 时间管理洞察
            if min_wait > 20:
                if user_lang == 'zh':
                    insights.append("⏰ 长期等候预期，建议制定完整的健康管理计划")
                else:
                    insights.append("⏰ Long wait expected, recommend comprehensive health management plan")
            
        except Exception as e:
            self.logger.error(f"提取关键洞察失败: {e}")
        
        return insights[:5]  # 限制最多5个洞察
    
    def _create_action_summary(self, recommendations: List[DailyRecommendation], user_lang: str) -> str:
        """创建行动摘要"""
        try:
            if not recommendations:
                return "暂无特定建议" if user_lang == 'zh' else "No specific recommendations"
            
            # 按优先级分组
            high_priority = [r for r in recommendations if r.priority >= 4]
            medium_priority = [r for r in recommendations if r.priority == 3]
            low_priority = [r for r in recommendations if r.priority <= 2]
            
            if user_lang == 'zh':
                summary_parts = []
                
                if high_priority:
                    summary_parts.append(f"🔥 优先行动（{len(high_priority)}项）：{', '.join([r.title for r in high_priority])}")
                
                if medium_priority:
                    summary_parts.append(f"📋 重要关注（{len(medium_priority)}项）：{', '.join([r.title for r in medium_priority])}")
                
                if low_priority:
                    summary_parts.append(f"💡 长期规划（{len(low_priority)}项）：{', '.join([r.title for r in low_priority])}")
                
                return " | ".join(summary_parts)
            else:
                summary_parts = []
                
                if high_priority:
                    summary_parts.append(f"🔥 Priority Actions ({len(high_priority)}): {', '.join([r.title for r in high_priority])}")
                
                if medium_priority:
                    summary_parts.append(f"📋 Important Focus ({len(medium_priority)}): {', '.join([r.title for r in medium_priority])}")
                
                if low_priority:
                    summary_parts.append(f"💡 Long-term Planning ({len(low_priority)}): {', '.join([r.title for r in low_priority])}")
                
                return " | ".join(summary_parts)
        
        except Exception as e:
            self.logger.error(f"创建行动摘要失败: {e}")
            return "Error creating summary" if user_lang == 'en' else "创建摘要时出错"
    
    def _get_active_users(self) -> List[Dict]:
        """获取活跃用户"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT user_id, phone_number, postcode, specialty, threshold_weeks, radius_km, language
                FROM user_preferences 
                WHERE status = 'active'
            """)
            
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
                    'language': row[6] or 'en'
                })
            
            return users
            
        except Exception as e:
            self.logger.error(f"获取活跃用户失败: {e}")
            return []
    
    async def _send_daily_alert(self, user: Dict, alert: UserDailyAlert):
        """发送每日提醒"""
        try:
            # 这里集成Telegram或WhatsApp发送
            user_lang = user.get('language', 'en')
            message = self._format_daily_alert_message(alert, user_lang)
            
            # 发送逻辑（需要集成实际的通知服务）
            self.logger.info(f"每日提醒已准备发送给用户 {user['user_id']}")
            print(f"\n=== 每日提醒 - 用户 {user['user_id']} ===")
            print(message)
            print("=" * 50)
            
        except Exception as e:
            self.logger.error(f"发送每日提醒失败: {e}")
    
    def _format_daily_alert_message(self, alert: UserDailyAlert, user_lang: str) -> str:
        """格式化每日提醒消息"""
        try:
            if user_lang == 'zh':
                message = f"""🌅 **NHS每日健康助手** - {alert.alert_date.strftime('%Y年%m月%d日')}

📊 **今日状况摘要**
{self._format_current_status_zh(alert.current_status)}

🔍 **关键洞察**
{chr(10).join([f"• {insight}" for insight in alert.key_insights])}

🎯 **今日推荐行动**
{self._format_recommendations_zh(alert.recommendations[:3])}

📈 **趋势分析**
{alert.trend_analysis.get('trend_summary', '暂无趋势数据')[:200]}...

💡 **行动摘要**
{alert.action_summary}

---
💬 随时问我："等候时间如何？"或"有什么新建议？"
"""
            else:
                message = f"""🌅 **NHS Daily Health Assistant** - {alert.alert_date.strftime('%B %d, %Y')}

📊 **Today's Status Summary**
{self._format_current_status_en(alert.current_status)}

🔍 **Key Insights**
{chr(10).join([f"• {insight}" for insight in alert.key_insights])}

🎯 **Today's Recommended Actions**
{self._format_recommendations_en(alert.recommendations[:3])}

📈 **Trend Analysis**
{alert.trend_analysis.get('trend_summary', 'No trend data available')[:200]}...

💡 **Action Summary**
{alert.action_summary}

---
💬 Ask me anytime: "How are waiting times?" or "Any new recommendations?"
"""
            
            return message
            
        except Exception as e:
            self.logger.error(f"格式化每日提醒消息失败: {e}")
            return "Error formatting message" if user_lang == 'en' else "格式化消息时出错"
    
    def _format_current_status_zh(self, status: Dict) -> str:
        """格式化当前状况（中文）"""
        if status.get('status') != 'available':
            return "暂无相关数据"
        
        return f"""• 搜索范围：{status['search_radius']}公里内{status['total_hospitals']}家医院
• 最短等候：{status['min_wait_weeks']}周
• 平均等候：{status['avg_wait_weeks']}周
• 您的期望：{status['user_threshold']}周 {'✅ 有符合选择' if status['threshold_met'] else '❌ 暂无符合'}"""
    
    def _format_current_status_en(self, status: Dict) -> str:
        """格式化当前状况（英文）"""
        if status.get('status') != 'available':
            return "No relevant data available"
        
        return f"""• Search range: {status['total_hospitals']} hospitals within {status['search_radius']}km
• Shortest wait: {status['min_wait_weeks']} weeks
• Average wait: {status['avg_wait_weeks']} weeks
• Your expectation: {status['user_threshold']} weeks {'✅ Options available' if status['threshold_met'] else '❌ None available'}"""
    
    def _format_recommendations_zh(self, recommendations: List[DailyRecommendation]) -> str:
        """格式化推荐（中文）"""
        if not recommendations:
            return "今日暂无特殊推荐"
        
        formatted = []
        for i, rec in enumerate(recommendations, 1):
            priority_icon = "🔥" if rec.priority >= 4 else "📋" if rec.priority == 3 else "💡"
            formatted.append(f"{i}. {priority_icon} **{rec.title}**\n   {rec.description}")
        
        return "\n\n".join(formatted)
    
    def _format_recommendations_en(self, recommendations: List[DailyRecommendation]) -> str:
        """格式化推荐（英文）"""
        if not recommendations:
            return "No special recommendations today"
        
        formatted = []
        for i, rec in enumerate(recommendations, 1):
            priority_icon = "🔥" if rec.priority >= 4 else "📋" if rec.priority == 3 else "💡"
            formatted.append(f"{i}. {priority_icon} **{rec.title}**\n   {rec.description}")
        
        return "\n\n".join(formatted)

# 测试函数
async def test_daily_service():
    """测试每日提醒服务"""
    service = DailyComprehensiveAlertService()
    alerts = await service.generate_daily_alerts_for_all_users()
    print(f"Generated {len(alerts)} daily alerts")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_daily_service()) 