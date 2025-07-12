"""
患者服务 - NHS特定的用户管理和服务

特性：
1. 患者档案管理
2. NHS偏好设置
3. 等候时间订阅
4. 个性化推荐
5. 隐私保护
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from ..core.user_manager import UserManager, UserProfile, SubscriptionTier
from ..core.alert_engine import AlertEngine, AlertRule, AlertType, AlertSeverity, AlertContext

logger = logging.getLogger(__name__)

class AlertFrequency(Enum):
    """提醒频率"""
    IMMEDIATE = "immediate"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

@dataclass
class PatientProfile(UserProfile):
    """患者档案 - 扩展用户档案"""
    
    # NHS特定信息
    nhs_number: Optional[str] = None  # 加密存储
    gp_practice_code: Optional[str] = None
    
    # 地理位置
    postcode: Optional[str] = None
    preferred_travel_distance: int = 50  # 公里
    
    # 医疗偏好
    preferred_hospitals: List[str] = field(default_factory=list)
    medical_specialties: List[str] = field(default_factory=list)
    current_conditions: List[str] = field(default_factory=list)
    
    # 等候偏好
    max_acceptable_wait_weeks: int = 18
    consider_private_options: bool = False
    
    # 通知偏好
    alert_frequency: AlertFrequency = AlertFrequency.WEEKLY
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "08:00"
    
    # 可达性需求
    mobility_requirements: List[str] = field(default_factory=list)  # wheelchair, parking, transport
    language_preference: str = "en"
    interpreter_required: bool = False

@dataclass
class WaitingTimeSubscription:
    """等候时间订阅"""
    id: str
    patient_id: str
    
    # 监控条件
    specialty_codes: List[str] = field(default_factory=list)
    provider_codes: List[str] = field(default_factory=list)  # 空列表表示所有提供者
    max_distance_km: int = 50
    
    # 提醒条件
    alert_threshold_weeks: int = 18
    improvement_threshold_weeks: int = 4  # 等候时间改善多少周时提醒
    
    # 订阅设置
    frequency: AlertFrequency = AlertFrequency.WEEKLY
    enabled: bool = True
    
    # 时间信息
    created_at: datetime = field(default_factory=datetime.now)
    last_alert_sent: Optional[datetime] = None

class PatientService:
    """
    患者服务
    
    提供NHS患者特定的服务功能：
    - 患者档案管理
    - 等候时间订阅
    - 个性化提醒
    - 医院推荐
    """
    
    def __init__(self, user_manager: UserManager, alert_engine: AlertEngine, config_manager):
        self.user_manager = user_manager
        self.alert_engine = alert_engine
        self.config = config_manager
        
        # 订阅管理
        self.subscriptions: Dict[str, List[WaitingTimeSubscription]] = {}
        
        # NHS特定配置
        self.nhs_config = self._load_nhs_config()
        
        # 初始化默认提醒规则
        asyncio.create_task(self._init_default_alert_rules())
    
    def _load_nhs_config(self) -> Dict[str, Any]:
        """加载NHS特定配置"""
        return {
            'default_alert_thresholds': {
                'urgent_specialties': ['120', '400', '401'],  # ENT, 神经科, 肿瘤科
                'urgent_threshold_weeks': 4,
                'standard_threshold_weeks': 18,
                'long_wait_threshold_weeks': 52
            },
            'private_insurance_providers': [
                'BUPA', 'AXA', 'Vitality', 'Aviva'
            ],
            'accessibility_features': {
                'wheelchair': ['wheelchair_access', 'disabled_parking'],
                'parking': ['patient_parking', 'free_parking'],
                'transport': ['public_transport', 'hospital_shuttle']
            }
        }
    
    async def create_patient(self, patient_data: Dict[str, Any], tenant_id: Optional[str] = None) -> PatientProfile:
        """创建患者档案"""
        
        # 验证NHS号码格式（如果提供）
        if 'nhs_number' in patient_data and patient_data['nhs_number']:
            if not self._validate_nhs_number(patient_data['nhs_number']):
                raise ValueError("Invalid NHS number format")
        
        # 验证邮编格式
        if 'postcode' in patient_data and patient_data['postcode']:
            patient_data['postcode'] = self._normalize_postcode(patient_data['postcode'])
        
        # 创建基础用户
        user_profile = await self.user_manager.create_user(patient_data, tenant_id)
        
        # 创建患者特定档案
        patient_profile = PatientProfile(**user_profile.__dict__, **patient_data)
        
        # 保存患者扩展信息
        await self._save_patient_profile(patient_profile)
        
        # 创建默认等候时间订阅
        if patient_profile.medical_specialties:
            await self.create_waiting_time_subscription(
                patient_id=patient_profile.user_id,
                specialty_codes=patient_profile.medical_specialties,
                max_distance_km=patient_profile.preferred_travel_distance
            )
        
        logger.info(f"Created patient profile: {patient_profile.user_id}")
        return patient_profile
    
    async def get_patient(self, patient_id: str) -> Optional[PatientProfile]:
        """获取患者档案"""
        # 获取基础用户信息
        user_profile = await self.user_manager.get_user(patient_id)
        if not user_profile:
            return None
        
        # 获取患者扩展信息
        patient_data = await self._load_patient_profile(patient_id)
        
        if patient_data:
            return PatientProfile(**user_profile.__dict__, **patient_data)
        else:
            # 如果没有患者扩展信息，使用基础用户信息创建
            return PatientProfile(**user_profile.__dict__)
    
    async def update_patient_preferences(self, patient_id: str, preferences: Dict[str, Any]) -> PatientProfile:
        """更新患者偏好"""
        patient = await self.get_patient(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")
        
        # 更新偏好
        for key, value in preferences.items():
            if hasattr(patient, key):
                setattr(patient, key, value)
        
        patient.updated_at = datetime.now()
        
        # 保存更新
        await self._save_patient_profile(patient)
        
        # 更新相关订阅
        await self._update_subscriptions_for_preferences(patient_id, preferences)
        
        logger.info(f"Updated patient preferences: {patient_id}")
        return patient
    
    async def create_waiting_time_subscription(self, patient_id: str, specialty_codes: List[str], 
                                             provider_codes: Optional[List[str]] = None,
                                             max_distance_km: int = 50,
                                             alert_threshold_weeks: int = 18) -> WaitingTimeSubscription:
        """创建等候时间订阅"""
        
        subscription = WaitingTimeSubscription(
            id=f"sub_{patient_id}_{datetime.now().timestamp()}",
            patient_id=patient_id,
            specialty_codes=specialty_codes,
            provider_codes=provider_codes or [],
            max_distance_km=max_distance_km,
            alert_threshold_weeks=alert_threshold_weeks
        )
        
        # 保存订阅
        if patient_id not in self.subscriptions:
            self.subscriptions[patient_id] = []
        
        self.subscriptions[patient_id].append(subscription)
        await self._save_subscription_to_db(subscription)
        
        # 创建对应的提醒规则
        await self._create_alert_rules_for_subscription(subscription)
        
        logger.info(f"Created waiting time subscription: {subscription.id}")
        return subscription
    
    async def get_patient_subscriptions(self, patient_id: str) -> List[WaitingTimeSubscription]:
        """获取患者的等候时间订阅"""
        if patient_id not in self.subscriptions:
            # 从数据库加载
            subscriptions = await self._load_subscriptions_from_db(patient_id)
            self.subscriptions[patient_id] = subscriptions
        
        return self.subscriptions.get(patient_id, [])
    
    async def update_subscription(self, subscription_id: str, updates: Dict[str, Any]) -> WaitingTimeSubscription:
        """更新等候时间订阅"""
        # 查找订阅
        subscription = None
        patient_id = None
        
        for pid, subs in self.subscriptions.items():
            for sub in subs:
                if sub.id == subscription_id:
                    subscription = sub
                    patient_id = pid
                    break
            if subscription:
                break
        
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")
        
        # 更新字段
        for key, value in updates.items():
            if hasattr(subscription, key):
                setattr(subscription, key, value)
        
        # 保存更新
        await self._save_subscription_to_db(subscription)
        
        # 更新提醒规则
        await self._update_alert_rules_for_subscription(subscription)
        
        return subscription
    
    async def process_patient_alerts(self, patient_id: str) -> List[Dict[str, Any]]:
        """处理患者提醒"""
        patient = await self.get_patient(patient_id)
        if not patient:
            return []
        
        # 构建提醒上下文
        context = AlertContext(
            user_id=patient_id,
            tenant_id=patient.tenant_id,
            user_profile=self._build_user_profile_dict(patient),
            current_data=await self._get_current_waiting_data(patient),
            historical_data=await self._get_historical_waiting_data(patient)
        )
        
        # 评估提醒
        alerts = await self.alert_engine.evaluate_user_alerts(patient_id, context)
        
        # 转换为患者友好格式
        patient_alerts = []
        for alert in alerts:
            patient_alert = await self._format_patient_alert(alert, patient)
            patient_alerts.append(patient_alert)
        
        return patient_alerts
    
    def _validate_nhs_number(self, nhs_number: str) -> bool:
        """验证NHS号码格式"""
        # 移除空格和连字符
        clean_number = ''.join(filter(str.isdigit, nhs_number))
        
        # NHS号码应该是10位数字
        if len(clean_number) != 10:
            return False
        
        # 简化的校验算法（实际NHS使用模10校验）
        try:
            digits = [int(d) for d in clean_number]
            check_sum = sum(d * (10 - i) for i, d in enumerate(digits[:-1]))
            check_digit = (11 - (check_sum % 11)) % 11
            
            # 校验位不能是10
            if check_digit == 10:
                return False
            
            return check_digit == digits[-1]
            
        except (ValueError, IndexError):
            return False
    
    def _normalize_postcode(self, postcode: str) -> str:
        """标准化邮编格式"""
        # 移除空格并转大写
        clean_postcode = postcode.replace(' ', '').upper()
        
        # 添加标准空格格式 (e.g., "CB21QT" -> "CB2 1QT")
        if len(clean_postcode) >= 5:
            return f"{clean_postcode[:-3]} {clean_postcode[-3:]}"
        
        return clean_postcode
    
    async def _init_default_alert_rules(self):
        """初始化默认提醒规则"""
        try:
            # 紧急专科等候时间提醒
            urgent_rule = AlertRule(
                id="nhs_urgent_specialty_wait",
                name="紧急专科等候时间提醒",
                description="当紧急专科等候时间超过4周时提醒",
                type=AlertType.THRESHOLD,
                severity=AlertSeverity.HIGH,
                conditions={
                    'field': 'estimated_median_wait',
                    'threshold': 4,
                    'operator': 'gt',
                    'specialty_filter': self.nhs_config['default_alert_thresholds']['urgent_specialties']
                },
                target_criteria={
                    'medical_specialties': self.nhs_config['default_alert_thresholds']['urgent_specialties']
                }
            )
            
            await self.alert_engine.create_rule(urgent_rule.__dict__)
            
            # 标准等候时间提醒
            standard_rule = AlertRule(
                id="nhs_standard_wait_threshold",
                name="标准等候时间提醒",
                description="当等候时间超过18周时提醒",
                type=AlertType.THRESHOLD,
                severity=AlertSeverity.MEDIUM,
                conditions={
                    'field': 'estimated_median_wait',
                    'threshold': 18,
                    'operator': 'gt'
                }
            )
            
            await self.alert_engine.create_rule(standard_rule.__dict__)
            
            # 等候时间改善提醒
            improvement_rule = AlertRule(
                id="nhs_wait_time_improvement",
                name="等候时间改善提醒",
                description="当附近医院等候时间显著改善时提醒",
                type=AlertType.COMPARISON,
                severity=AlertSeverity.LOW,
                conditions={
                    'field': 'estimated_median_wait',
                    'comparison_type': 'regional',
                    'min_improvement': 20.0
                }
            )
            
            await self.alert_engine.create_rule(improvement_rule.__dict__)
            
        except Exception as e:
            logger.error(f"Failed to initialize default alert rules: {e}")
    
    def _build_user_profile_dict(self, patient: PatientProfile) -> Dict[str, Any]:
        """构建用户档案字典"""
        return {
            'postcode': patient.postcode,
            'medical_specialties': patient.medical_specialties,
            'preferred_hospitals': patient.preferred_hospitals,
            'max_acceptable_wait_weeks': patient.max_acceptable_wait_weeks,
            'preferred_travel_distance': patient.preferred_travel_distance,
            'consider_private_options': patient.consider_private_options,
            'mobility_requirements': patient.mobility_requirements,
            'has_private_insurance': patient.has_private_insurance
        }
    
    async def _get_current_waiting_data(self, patient: PatientProfile) -> Dict[str, Any]:
        """获取当前等候时间数据"""
        # 这里应该查询最新的NHS数据
        # 基于患者的专科和位置返回相关数据
        
        # 模拟返回数据
        return {
            'estimated_median_wait': 16,
            'over_18_weeks_rate': 0.25,
            'over_52_weeks_rate': 0.05,
            'nearest_hospital': 'Cambridge University Hospitals',
            'nearest_hospital_wait': 14
        }
    
    async def _get_historical_waiting_data(self, patient: PatientProfile) -> List[Dict[str, Any]]:
        """获取历史等候时间数据"""
        # 这里应该查询历史NHS数据
        # 返回最近几个月的趋势数据
        
        # 模拟返回数据
        historical_data = []
        for i in range(6):
            date = datetime.now() - timedelta(days=30 * i)
            historical_data.append({
                'timestamp': date.isoformat(),
                'estimated_median_wait': 16 + i,
                'over_18_weeks_rate': 0.25 + (i * 0.02)
            })
        
        return historical_data
    
    async def _format_patient_alert(self, alert, patient: PatientProfile) -> Dict[str, Any]:
        """格式化患者提醒"""
        # 根据患者偏好格式化提醒消息
        formatted_alert = {
            'id': alert.rule_id,
            'title': alert.title,
            'message': alert.personalized_message or alert.message,
            'severity': alert.severity.value,
            'created_at': alert.created_at.isoformat(),
            'data': alert.data,
            'actions': alert.recommended_actions
        }
        
        # 添加患者特定的行动建议
        if patient.consider_private_options and alert.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]:
            formatted_alert['actions'].append({
                'type': 'private_consultation',
                'text': '查看私立医疗选择',
                'url': '/private-options'
            })
        
        return formatted_alert
    
    async def _create_alert_rules_for_subscription(self, subscription: WaitingTimeSubscription):
        """为订阅创建提醒规则"""
        # 为每个订阅创建定制的提醒规则
        rule = AlertRule(
            id=f"subscription_{subscription.id}",
            name=f"订阅提醒 - {subscription.id}",
            description=f"为患者订阅创建的等候时间提醒",
            type=AlertType.THRESHOLD,
            severity=AlertSeverity.MEDIUM,
            conditions={
                'field': 'estimated_median_wait',
                'threshold': subscription.alert_threshold_weeks,
                'operator': 'gt',
                'specialty_filter': subscription.specialty_codes,
                'provider_filter': subscription.provider_codes
            },
            target_criteria={
                'user_id': subscription.patient_id
            },
            cooldown_minutes=60 * 24,  # 每日最多一次
            max_alerts_per_day=1
        )
        
        await self.alert_engine.create_rule(rule.__dict__)
    
    async def _update_alert_rules_for_subscription(self, subscription: WaitingTimeSubscription):
        """更新订阅对应的提醒规则"""
        rule_id = f"subscription_{subscription.id}"
        
        updates = {
            'conditions': {
                'field': 'estimated_median_wait',
                'threshold': subscription.alert_threshold_weeks,
                'operator': 'gt',
                'specialty_filter': subscription.specialty_codes,
                'provider_filter': subscription.provider_codes
            },
            'enabled': subscription.enabled
        }
        
        try:
            await self.alert_engine.update_rule(rule_id, updates)
        except ValueError:
            # 规则不存在，创建新的
            await self._create_alert_rules_for_subscription(subscription)
    
    async def _update_subscriptions_for_preferences(self, patient_id: str, preferences: Dict[str, Any]):
        """根据偏好更新订阅"""
        subscriptions = await self.get_patient_subscriptions(patient_id)
        
        for subscription in subscriptions:
            updates = {}
            
            if 'preferred_travel_distance' in preferences:
                updates['max_distance_km'] = preferences['preferred_travel_distance']
            
            if 'max_acceptable_wait_weeks' in preferences:
                updates['alert_threshold_weeks'] = preferences['max_acceptable_wait_weeks']
            
            if 'alert_frequency' in preferences:
                updates['frequency'] = preferences['alert_frequency']
            
            if updates:
                await self.update_subscription(subscription.id, updates)
    
    async def _save_patient_profile(self, patient: PatientProfile):
        """保存患者档案到数据库"""
        # 实现数据库保存逻辑
        pass
    
    async def _load_patient_profile(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """从数据库加载患者档案"""
        # 实现数据库查询逻辑
        return None
    
    async def _save_subscription_to_db(self, subscription: WaitingTimeSubscription):
        """保存订阅到数据库"""
        # 实现数据库保存逻辑
        pass
    
    async def _load_subscriptions_from_db(self, patient_id: str) -> List[WaitingTimeSubscription]:
        """从数据库加载订阅"""
        # 实现数据库查询逻辑
        return []
    
    def get_stats(self) -> Dict[str, Any]:
        """获取患者服务统计"""
        total_subscriptions = sum(len(subs) for subs in self.subscriptions.values())
        active_subscriptions = sum(
            len([sub for sub in subs if sub.enabled]) 
            for subs in self.subscriptions.values()
        )
        
        return {
            'total_patients': len(self.subscriptions),
            'total_subscriptions': total_subscriptions,
            'active_subscriptions': active_subscriptions,
            'specialties_monitored': len(set().union(*[
                sub.specialty_codes for subs in self.subscriptions.values() 
                for sub in subs
            ]))
        } 