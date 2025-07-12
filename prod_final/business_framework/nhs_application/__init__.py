"""
NHS应用模块 - 基于通用框架的NHS特定实现

组件：
- NHS数据处理器
- 等候时间分析器
- 医院推荐算法
- 患者偏好管理
- 预约提醒系统
- GP Connect集成
"""

from .nhs_data_processor import NHSDataProcessor
from .waiting_time_analyzer import WaitingTimeAnalyzer
from .hospital_recommender import HospitalRecommender
from .patient_service import PatientService
from .appointment_scheduler import AppointmentScheduler

__all__ = [
    'NHSDataProcessor',
    'WaitingTimeAnalyzer', 
    'HospitalRecommender',
    'PatientService',
    'AppointmentScheduler'
] 