"""
智能提醒引擎 - 支持规则配置和多维度数据分析

特性：
1. 灵活的规则配置系统
2. 多维度数据分析 (趋势、阈值、对比)
3. 个性化提醒策略
4. 提醒去重和频率控制
5. A/B测试支持
6. 多租户规则隔离
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import pandas as pd
import numpy as np
from collections import defaultdict

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """提醒严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertType(Enum):
    """提醒类型"""
    THRESHOLD = "threshold"  # 阈值提醒
    TREND = "trend"         # 趋势提醒
    ANOMALY = "anomaly"     # 异常提醒
    COMPARISON = "comparison"  # 对比提醒
    OPPORTUNITY = "opportunity"  # 机会提醒

@dataclass
class AlertRule:
    """提醒规则配置"""
    id: str
    name: str
    description: str
    type: AlertType
    severity: AlertSeverity
    enabled: bool = True
    
    # 规则条件
    conditions: Dict[str, Any] = field(default_factory=dict)
    
    # 目标用户/群体
    target_criteria: Dict[str, Any] = field(default_factory=dict)
    
    # 提醒频率控制
    cooldown_minutes: int = 60
    max_alerts_per_day: int = 5
    
    # 个性化设置
    personalization: Dict[str, Any] = field(default_factory=dict)
    
    # A/B测试配置
    ab_test_group: Optional[str] = None
    
    # 租户ID
    tenant_id: Optional[str] = None
    
    # 时间设置
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class AlertContext:
    """提醒上下文数据"""
    user_id: str
    tenant_id: Optional[str] = None
    user_profile: Dict[str, Any] = field(default_factory=dict)
    current_data: Dict[str, Any] = field(default_factory=dict)
    historical_data: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass 
class AlertResult:
    """提醒结果"""
    rule_id: str
    user_id: str
    triggered: bool
    severity: AlertSeverity
    title: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    # 个性化内容
    personalized_message: Optional[str] = None
    recommended_actions: List[Dict[str, Any]] = field(default_factory=list)

class RuleEvaluator(ABC):
    """规则评估器抽象基类"""
    
    @abstractmethod
    async def evaluate(self, rule: AlertRule, context: AlertContext) -> Optional[AlertResult]:
        """评估规则是否触发"""
        pass
    
    @abstractmethod
    def supports_rule_type(self, rule_type: AlertType) -> bool:
        """检查是否支持该规则类型"""
        pass

class ThresholdEvaluator(RuleEvaluator):
    """阈值提醒评估器"""
    
    async def evaluate(self, rule: AlertRule, context: AlertContext) -> Optional[AlertResult]:
        """评估阈值规则"""
        conditions = rule.conditions
        current_data = context.current_data
        
        # 获取监控字段和阈值
        field = conditions.get('field')
        threshold = conditions.get('threshold')
        operator = conditions.get('operator', 'gt')  # gt, lt, gte, lte, eq
        
        if not field or threshold is None:
            logger.warning(f"Invalid threshold rule {rule.id}: missing field or threshold")
            return None
        
        if field not in current_data:
            logger.warning(f"Field {field} not found in current data for rule {rule.id}")
            return None
        
        current_value = current_data[field]
        
        # 数值转换
        try:
            if isinstance(current_value, str):
                current_value = float(current_value.replace(',', ''))
            current_value = float(current_value)
            threshold = float(threshold)
        except (ValueError, TypeError):
            logger.warning(f"Invalid numeric values for rule {rule.id}: {current_value}, {threshold}")
            return None
        
        # 阈值比较
        triggered = False
        if operator == 'gt':
            triggered = current_value > threshold
        elif operator == 'lt':
            triggered = current_value < threshold
        elif operator == 'gte':
            triggered = current_value >= threshold
        elif operator == 'lte':
            triggered = current_value <= threshold
        elif operator == 'eq':
            triggered = abs(current_value - threshold) < 0.001
        
        if not triggered:
            return None
        
        # 生成提醒
        message = self._generate_threshold_message(rule, current_value, threshold, operator)
        
        return AlertResult(
            rule_id=rule.id,
            user_id=context.user_id,
            triggered=True,
            severity=rule.severity,
            title=rule.name,
            message=message,
            data={
                'field': field,
                'current_value': current_value,
                'threshold': threshold,
                'operator': operator
            }
        )
    
    def _generate_threshold_message(self, rule: AlertRule, current_value: float, threshold: float, operator: str) -> str:
        """生成阈值提醒消息"""
        field = rule.conditions.get('field', 'value')
        
        if operator in ['gt', 'gte']:
            return f"{field}已达到{current_value}，超过阈值{threshold}"
        elif operator in ['lt', 'lte']:
            return f"{field}降至{current_value}，低于阈值{threshold}"
        else:
            return f"{field}为{current_value}，触发阈值条件"
    
    def supports_rule_type(self, rule_type: AlertType) -> bool:
        return rule_type == AlertType.THRESHOLD

class TrendEvaluator(RuleEvaluator):
    """趋势提醒评估器"""
    
    async def evaluate(self, rule: AlertRule, context: AlertContext) -> Optional[AlertResult]:
        """评估趋势规则"""
        conditions = rule.conditions
        historical_data = context.historical_data
        current_data = context.current_data
        
        field = conditions.get('field')
        trend_type = conditions.get('trend_type', 'increase')  # increase, decrease, stable
        period_days = conditions.get('period_days', 7)
        min_change_percent = conditions.get('min_change_percent', 5.0)
        
        if not field or not historical_data:
            return None
        
        # 获取历史趋势数据
        cutoff_date = datetime.now() - timedelta(days=period_days)
        recent_data = [
            d for d in historical_data 
            if d.get('timestamp') and datetime.fromisoformat(d['timestamp']) >= cutoff_date
        ]
        
        if len(recent_data) < 2:
            return None
        
        # 计算趋势
        values = []
        for data_point in recent_data:
            if field in data_point:
                try:
                    value = float(str(data_point[field]).replace(',', ''))
                    values.append(value)
                except (ValueError, TypeError):
                    continue
        
        if len(values) < 2:
            return None
        
        # 线性趋势分析
        x = np.arange(len(values))
        y = np.array(values)
        slope = np.polyfit(x, y, 1)[0]
        
        # 计算变化百分比
        start_value = values[0]
        end_value = values[-1]
        if start_value != 0:
            change_percent = ((end_value - start_value) / start_value) * 100
        else:
            change_percent = 0
        
        # 判断趋势
        triggered = False
        if trend_type == 'increase' and slope > 0 and change_percent >= min_change_percent:
            triggered = True
        elif trend_type == 'decrease' and slope < 0 and abs(change_percent) >= min_change_percent:
            triggered = True
        elif trend_type == 'stable' and abs(change_percent) < min_change_percent:
            triggered = True
        
        if not triggered:
            return None
        
        message = self._generate_trend_message(rule, change_percent, period_days, trend_type)
        
        return AlertResult(
            rule_id=rule.id,
            user_id=context.user_id,
            triggered=True,
            severity=rule.severity,
            title=rule.name,
            message=message,
            data={
                'field': field,
                'trend_type': trend_type,
                'change_percent': change_percent,
                'period_days': period_days,
                'slope': slope
            }
        )
    
    def _generate_trend_message(self, rule: AlertRule, change_percent: float, period_days: int, trend_type: str) -> str:
        """生成趋势提醒消息"""
        field = rule.conditions.get('field', 'value')
        
        if trend_type == 'increase':
            return f"{field}在过去{period_days}天内上升了{change_percent:.1f}%"
        elif trend_type == 'decrease':
            return f"{field}在过去{period_days}天内下降了{abs(change_percent):.1f}%"
        else:
            return f"{field}在过去{period_days}天内保持稳定"
    
    def supports_rule_type(self, rule_type: AlertType) -> bool:
        return rule_type == AlertType.TREND

class ComparisonEvaluator(RuleEvaluator):
    """对比提醒评估器 - 用于NHS医院等候时间对比"""
    
    async def evaluate(self, rule: AlertRule, context: AlertContext) -> Optional[AlertResult]:
        """评估对比规则"""
        conditions = rule.conditions
        current_data = context.current_data
        
        field = conditions.get('field')
        comparison_type = conditions.get('comparison_type', 'regional')  # regional, national, peer
        min_improvement = conditions.get('min_improvement', 20.0)  # 最小改善百分比
        
        if not field or field not in current_data:
            return None
        
        current_value = self._parse_numeric_value(current_data[field])
        if current_value is None:
            return None
        
        # 获取对比数据
        comparison_data = await self._get_comparison_data(context, comparison_type, field)
        if not comparison_data:
            return None
        
        # 寻找更好的选择
        better_options = []
        for option in comparison_data:
            option_value = self._parse_numeric_value(option.get(field))
            if option_value is None:
                continue
            
            improvement = ((current_value - option_value) / current_value) * 100
            if improvement >= min_improvement:
                better_options.append({
                    'name': option.get('name', 'Unknown'),
                    'value': option_value,
                    'improvement': improvement,
                    'distance': option.get('distance', 'Unknown'),
                    'location': option.get('location', '')
                })
        
        if not better_options:
            return None
        
        # 按改善程度排序
        better_options.sort(key=lambda x: x['improvement'], reverse=True)
        
        message = self._generate_comparison_message(rule, current_value, better_options[:3])
        
        return AlertResult(
            rule_id=rule.id,
            user_id=context.user_id,
            triggered=True,
            severity=rule.severity,
            title=rule.name,
            message=message,
            data={
                'field': field,
                'current_value': current_value,
                'better_options': better_options[:3],
                'comparison_type': comparison_type
            },
            recommended_actions=[
                {
                    'type': 'transfer',
                    'text': f"考虑转至{option['name']}",
                    'url': f"/transfer?to={option['name']}"
                } for option in better_options[:2]
            ]
        )
    
    async def _get_comparison_data(self, context: AlertContext, comparison_type: str, field: str) -> List[Dict[str, Any]]:
        """获取对比数据"""
        # 这里应该从数据库查询对比数据
        # 基于用户位置、专科等条件筛选
        user_profile = context.user_profile
        
        # 模拟返回对比数据
        return [
            {
                'name': 'Hospital A',
                'location': 'Location A',
                field: '15',
                'distance': '10km'
            },
            {
                'name': 'Hospital B', 
                'location': 'Location B',
                field: '20',
                'distance': '25km'
            }
        ]
    
    def _parse_numeric_value(self, value: Any) -> Optional[float]:
        """解析数值"""
        try:
            if isinstance(value, str):
                value = value.replace(',', '').replace('weeks', '').replace('周', '').strip()
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _generate_comparison_message(self, rule: AlertRule, current_value: float, better_options: List[Dict]) -> str:
        """生成对比提醒消息"""
        field = rule.conditions.get('field', 'waiting_time')
        
        if not better_options:
            return f"当前{field}为{current_value}，暂无更好选择"
        
        best_option = better_options[0]
        message = f"当前{field}为{current_value}周，{best_option['name']}仅需{best_option['value']}周"
        
        if len(better_options) > 1:
            message += f"，另有{len(better_options)-1}个更快选择"
        
        return message
    
    def supports_rule_type(self, rule_type: AlertType) -> bool:
        return rule_type == AlertType.COMPARISON

class AlertEngine:
    """
    智能提醒引擎
    
    功能：
    - 多维度规则评估
    - 个性化提醒生成
    - 频率控制和去重
    - A/B测试支持
    - 多租户支持
    """
    
    def __init__(self, database_manager, config_manager):
        self.db = database_manager
        self.config = config_manager
        
        # 注册评估器
        self.evaluators: Dict[AlertType, RuleEvaluator] = {
            AlertType.THRESHOLD: ThresholdEvaluator(),
            AlertType.TREND: TrendEvaluator(),
            AlertType.COMPARISON: ComparisonEvaluator()
        }
        
        # 规则缓存
        self.rules_cache: Dict[str, List[AlertRule]] = {}
        self.cache_expiry: Dict[str, datetime] = {}
        
        # 提醒历史记录 (用于频率控制)
        self.alert_history: Dict[str, List[datetime]] = defaultdict(list)
        
        # 统计信息
        self.stats = {
            'rules_evaluated': 0,
            'alerts_triggered': 0,
            'alerts_suppressed': 0
        }
    
    def register_evaluator(self, rule_type: AlertType, evaluator: RuleEvaluator):
        """注册自定义评估器"""
        self.evaluators[rule_type] = evaluator
        logger.info(f"Registered evaluator for rule type: {rule_type}")
    
    async def create_rule(self, rule_data: Dict[str, Any]) -> AlertRule:
        """创建新规则"""
        rule = AlertRule(**rule_data)
        
        # 保存到数据库
        await self._save_rule_to_db(rule)
        
        # 清除缓存
        self._clear_rules_cache(rule.tenant_id)
        
        logger.info(f"Created new alert rule: {rule.id}")
        return rule
    
    async def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> AlertRule:
        """更新规则"""
        rule = await self._load_rule_from_db(rule_id)
        if not rule:
            raise ValueError(f"Rule {rule_id} not found")
        
        # 更新字段
        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        
        rule.updated_at = datetime.now()
        
        # 保存到数据库
        await self._save_rule_to_db(rule)
        
        # 清除缓存
        self._clear_rules_cache(rule.tenant_id)
        
        logger.info(f"Updated alert rule: {rule_id}")
        return rule
    
    async def evaluate_user_alerts(self, user_id: str, context: AlertContext) -> List[AlertResult]:
        """
        为用户评估所有适用的提醒规则
        """
        tenant_id = context.tenant_id
        
        # 获取适用的规则
        rules = await self._get_applicable_rules(user_id, tenant_id, context.user_profile)
        
        results = []
        
        for rule in rules:
            self.stats['rules_evaluated'] += 1
            
            # 检查频率限制
            if self._is_suppressed_by_frequency(user_id, rule):
                self.stats['alerts_suppressed'] += 1
                continue
            
            # 评估规则
            if rule.type in self.evaluators:
                evaluator = self.evaluators[rule.type]
                try:
                    result = await evaluator.evaluate(rule, context)
                    if result:
                        # 个性化处理
                        result = await self._personalize_alert(result, context)
                        
                        # 记录提醒历史
                        self._record_alert_history(user_id, rule)
                        
                        results.append(result)
                        self.stats['alerts_triggered'] += 1
                        
                        logger.info(f"Alert triggered: {rule.id} for user {user_id}")
                
                except Exception as e:
                    logger.error(f"Rule evaluation failed: {rule.id} - {e}")
            
            else:
                logger.warning(f"No evaluator for rule type: {rule.type}")
        
        return results
    
    async def _get_applicable_rules(self, user_id: str, tenant_id: Optional[str], user_profile: Dict[str, Any]) -> List[AlertRule]:
        """获取适用于用户的规则"""
        cache_key = f"{tenant_id or 'global'}:{user_id}"
        
        # 检查缓存
        if cache_key in self.rules_cache:
            if cache_key in self.cache_expiry and datetime.now() < self.cache_expiry[cache_key]:
                return self.rules_cache[cache_key]
        
        # 从数据库加载规则
        all_rules = await self._load_rules_from_db(tenant_id)
        
        # 筛选适用规则
        applicable_rules = []
        for rule in all_rules:
            if not rule.enabled:
                continue
            
            # 检查目标条件
            if self._matches_target_criteria(user_profile, rule.target_criteria):
                applicable_rules.append(rule)
        
        # 缓存结果
        self.rules_cache[cache_key] = applicable_rules
        self.cache_expiry[cache_key] = datetime.now() + timedelta(minutes=30)
        
        return applicable_rules
    
    def _matches_target_criteria(self, user_profile: Dict[str, Any], target_criteria: Dict[str, Any]) -> bool:
        """检查用户是否匹配目标条件"""
        if not target_criteria:
            return True  # 无条件则匹配所有用户
        
        for key, expected_value in target_criteria.items():
            user_value = user_profile.get(key)
            
            if isinstance(expected_value, list):
                if user_value not in expected_value:
                    return False
            elif isinstance(expected_value, dict):
                # 支持范围条件 {"min": 18, "max": 65}
                if 'min' in expected_value and user_value < expected_value['min']:
                    return False
                if 'max' in expected_value and user_value > expected_value['max']:
                    return False
            else:
                if user_value != expected_value:
                    return False
        
        return True
    
    def _is_suppressed_by_frequency(self, user_id: str, rule: AlertRule) -> bool:
        """检查是否被频率限制抑制"""
        history_key = f"{user_id}:{rule.id}"
        now = datetime.now()
        
        # 清理过期历史记录
        cutoff_time = now - timedelta(minutes=rule.cooldown_minutes)
        daily_cutoff = now - timedelta(days=1)
        
        self.alert_history[history_key] = [
            t for t in self.alert_history[history_key] 
            if t > cutoff_time
        ]
        
        # 检查冷却时间
        if self.alert_history[history_key]:
            last_alert = max(self.alert_history[history_key])
            if now - last_alert < timedelta(minutes=rule.cooldown_minutes):
                return True
        
        # 检查每日限制
        daily_alerts = [
            t for t in self.alert_history[history_key] 
            if t > daily_cutoff
        ]
        
        if len(daily_alerts) >= rule.max_alerts_per_day:
            return True
        
        return False
    
    def _record_alert_history(self, user_id: str, rule: AlertRule):
        """记录提醒历史"""
        history_key = f"{user_id}:{rule.id}"
        self.alert_history[history_key].append(datetime.now())
    
    async def _personalize_alert(self, alert: AlertResult, context: AlertContext) -> AlertResult:
        """个性化提醒内容"""
        user_profile = context.user_profile
        
        # 根据用户偏好调整消息
        preferred_language = user_profile.get('language', 'en')
        communication_style = user_profile.get('communication_style', 'formal')
        
        # 这里可以集成AI模型来生成个性化消息
        if communication_style == 'casual':
            alert.personalized_message = self._make_message_casual(alert.message)
        elif communication_style == 'urgent':
            alert.personalized_message = self._make_message_urgent(alert.message)
        
        # 添加个性化推荐行动
        alert.recommended_actions = await self._generate_personalized_actions(alert, context)
        
        return alert
    
    def _make_message_casual(self, message: str) -> str:
        """将消息转换为轻松语调"""
        # 简单的语调转换，实际应用中可使用NLP模型
        casual_prefixes = ["嗨！", "好消息：", "提醒一下："]
        return f"{casual_prefixes[0]}{message}"
    
    def _make_message_urgent(self, message: str) -> str:
        """将消息转换为紧急语调"""
        return f"🚨 紧急提醒：{message}"
    
    async def _generate_personalized_actions(self, alert: AlertResult, context: AlertContext) -> List[Dict[str, Any]]:
        """生成个性化推荐行动"""
        actions = []
        user_profile = context.user_profile
        
        # 基于用户偏好和提醒类型生成行动建议
        if alert.rule_id.startswith('nhs_'):
            # NHS相关提醒的个性化行动
            if user_profile.get('has_private_insurance'):
                actions.append({
                    'type': 'private_consultation',
                    'text': '查看私立医疗选择',
                    'url': '/private-options'
                })
            
            if user_profile.get('mobility', 'normal') == 'limited':
                actions.append({
                    'type': 'local_options',
                    'text': '查找附近医疗选择',
                    'url': '/nearby-options'
                })
        
        return actions
    
    async def _save_rule_to_db(self, rule: AlertRule):
        """保存规则到数据库"""
        # 这里应该实现数据库存储逻辑
        pass
    
    async def _load_rule_from_db(self, rule_id: str) -> Optional[AlertRule]:
        """从数据库加载规则"""
        # 这里应该实现数据库查询逻辑
        return None
    
    async def _load_rules_from_db(self, tenant_id: Optional[str]) -> List[AlertRule]:
        """从数据库加载所有规则"""
        # 这里应该实现数据库查询逻辑
        return []
    
    def _clear_rules_cache(self, tenant_id: Optional[str]):
        """清除规则缓存"""
        keys_to_remove = [
            key for key in self.rules_cache.keys() 
            if key.startswith(f"{tenant_id or 'global'}:")
        ]
        
        for key in keys_to_remove:
            self.rules_cache.pop(key, None)
            self.cache_expiry.pop(key, None)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取引擎统计信息"""
        return {
            **self.stats,
            'active_rules_count': sum(len(rules) for rules in self.rules_cache.values()),
            'cached_tenants': len(set(key.split(':')[0] for key in self.rules_cache.keys())),
            'alert_history_entries': sum(len(history) for history in self.alert_history.values())
        } 