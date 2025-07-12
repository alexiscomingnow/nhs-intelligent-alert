"""
NHS数据处理器 - 基于通用DataProcessor的NHS特定实现

特性：
1. NHS RTT数据处理
2. 专科代码映射
3. 等候时间趋势分析
4. 数据质量监控
5. 自动数据更新
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from ..core.data_processor import DataProcessor, DataSource, ProcessingResult

logger = logging.getLogger(__name__)

@dataclass
class NHSSpecialty:
    """NHS专科信息"""
    code: str
    name: str
    category: str
    description: str = ""
    typical_wait_weeks: Optional[int] = None

@dataclass 
class NHSProvider:
    """NHS医疗提供者信息"""
    code: str
    name: str
    location: str
    trust_name: str = ""
    coordinates: Optional[Dict[str, float]] = None
    contact_info: Dict[str, str] = field(default_factory=dict)

class NHSDataProcessor(DataProcessor):
    """
    NHS数据处理器
    
    扩展通用DataProcessor，添加NHS特定功能：
    - RTT数据专业处理
    - 专科代码标准化
    - 等候时间预测
    - 地理位置增强
    """
    
    def __init__(self, database_manager, config_manager):
        super().__init__(database_manager, config_manager)
        
        # NHS特定配置
        self.nhs_config = self._load_nhs_config()
        
        # 专科映射
        self.specialty_mapping = self._load_specialty_mapping()
        
        # 提供者信息
        self.provider_mapping = self._load_provider_mapping()
        
        # 注册NHS数据源
        self._register_nhs_sources()
    
    def _load_nhs_config(self) -> Dict[str, Any]:
        """加载NHS特定配置"""
        return {
            'rtt_thresholds': {
                '18_weeks': 18,
                '52_weeks': 52
            },
            'specialty_categories': {
                'surgical': ['100', '101', '110', '120', '130'],
                'medical': ['300', '301', '302', '320', '330'],
                'diagnostic': ['400', '401', '410']
            },
            'priority_specialties': ['120', '330', '400'],  # 心脏外科、急诊科、诊断影像
            'data_quality_rules': {
                'min_records_per_provider': 5,
                'max_wait_weeks': 200,
                'required_fields': ['provider_org_code', 'treatment_function_code', 'rtt_part_type']
            }
        }
    
    def _load_specialty_mapping(self) -> Dict[str, NHSSpecialty]:
        """加载专科代码映射"""
        # 基于NHS数据字典的专科映射
        specialties = {
            '100': NHSSpecialty('100', 'General Surgery', 'surgical', '普通外科', 12),
            '101': NHSSpecialty('101', 'Urology', 'surgical', '泌尿外科', 14),
            '110': NHSSpecialty('110', 'Trauma & Orthopaedics', 'surgical', '创伤与骨科', 18),
            '120': NHSSpecialty('120', 'ENT', 'surgical', '耳鼻喉科', 10),
            '130': NHSSpecialty('130', 'Ophthalmology', 'surgical', '眼科', 16),
            
            '300': NHSSpecialty('300', 'General Medicine', 'medical', '内科', 8),
            '301': NHSSpecialty('301', 'Gastroenterology', 'medical', '消化内科', 10),
            '302': NHSSpecialty('302', 'Endocrinology', 'medical', '内分泌科', 12),
            '320': NHSSpecialty('320', 'Cardiology', 'medical', '心脏内科', 6),
            '330': NHSSpecialty('330', 'Dermatology', 'medical', '皮肤科', 14),
            
            '400': NHSSpecialty('400', 'Neurology', 'medical', '神经内科', 16),
            '401': NHSSpecialty('401', 'Clinical Oncology', 'medical', '肿瘤科', 4),
            '410': NHSSpecialty('410', 'Rheumatology', 'medical', '风湿免疫科', 12)
        }
        
        return specialties
    
    def _load_provider_mapping(self) -> Dict[str, NHSProvider]:
        """加载医疗提供者映射"""
        # 这里应该从数据库或配置文件加载
        # 简化示例
        providers = {
            'RGT01': NHSProvider('RGT01', 'Cambridge University Hospitals', 'Cambridge', 'Cambridge University Hospitals NHS Foundation Trust'),
            'RGT02': NHSProvider('RGT02', 'Addenbrooke\'s Hospital', 'Cambridge', 'Cambridge University Hospitals NHS Foundation Trust'),
            'R1H': NHSProvider('R1H', 'Oxford University Hospitals', 'Oxford', 'Oxford University Hospitals NHS Foundation Trust'),
            'RD1': NHSProvider('RD1', 'Imperial College Healthcare', 'London', 'Imperial College Healthcare NHS Trust')
        }
        
        return providers
    
    def _register_nhs_sources(self):
        """注册NHS数据源"""
        # NHS England RTT数据源
        nhs_rtt_source = DataSource(
            name="nhs_england_rtt",
            type="csv",
            url="https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/rtt-data-2024-25/",
            config={
                'discovery_strategies': ['html', 'playwright', 'smart_url'],
                'link_selectors': [
                    'a[href*="rtt"][href$=".csv"]',
                    'a[href*="RTT"][href$=".csv"]',
                    'a[href*="provider"][href$=".csv"]'
                ],
                'csv_priority': ['provider', 'extract', 'rtt'],
                'url_patterns': [
                    'https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/{year}/{month:02d}/{year}{month:02d}31-RTT-{month_name}-{year}-full-extract.csv',
                ],
                'date_range_months': 6,
                'table_name': 'nhs_rtt_data',
                'transformation': {
                    'normalize_columns': True,
                    'column_types': {
                        'period': 'str',
                        'provider_org_code': 'str',
                        'provider_org_name': 'str',
                        'treatment_function_code': 'str',
                        'treatment_function_name': 'str'
                    },
                    'remove_duplicates': True,
                    'null_strategy': 'keep'
                }
            },
            refresh_interval=86400,  # 每日检查
            discovery_strategies=['html', 'playwright', 'smart_url']
        )
        
        self.register_data_source(nhs_rtt_source)
        
        # MyPlannedCare API数据源
        myplannedcare_source = DataSource(
            name="myplannedcare_api",
            type="api",
            url="https://api.myplannedcare.nhs.uk/api/v1/trusts",
            config={
                'headers': {
                    'Accept': 'application/json',
                    'User-Agent': 'NHS-Alert-System/1.0'
                },
                'response_format': 'json',
                'table_name': 'myplannedcare_data',
                'transformation': {
                    'normalize_columns': True
                }
            },
            refresh_interval=604800,  # 每周检查
            discovery_strategies=['api']
        )
        
        self.register_data_source(myplannedcare_source)
    
    async def process_nhs_rtt_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """处理NHS RTT数据"""
        logger.info(f"Processing NHS RTT data: {len(data)} records")
        
        # 数据清洗
        data = self._clean_nhs_data(data)
        
        # 专科代码标准化
        data = self._standardize_specialties(data)
        
        # 等候时间计算
        data = self._calculate_waiting_metrics(data)
        
        # 地理位置增强
        data = self._enhance_geographic_data(data)
        
        # 数据质量检查
        quality_score = self._assess_data_quality(data)
        logger.info(f"Data quality score: {quality_score:.2f}")
        
        return data
    
    def _clean_nhs_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """清洗NHS数据"""
        original_count = len(data)
        
        # 移除无效记录
        data = data.dropna(subset=['provider_org_code', 'treatment_function_code'])
        
        # 标准化代码格式
        if 'provider_org_code' in data.columns:
            data['provider_org_code'] = data['provider_org_code'].astype(str).str.upper().str.strip()
        
        if 'treatment_function_code' in data.columns:
            data['treatment_function_code'] = data['treatment_function_code'].astype(str).str.strip()
        
        # 清理数值字段
        numeric_fields = [col for col in data.columns if 'week' in col.lower() or 'total' in col.lower()]
        for field in numeric_fields:
            if field in data.columns:
                data[field] = pd.to_numeric(data[field], errors='coerce')
        
        # 移除异常值
        max_wait = self.nhs_config['data_quality_rules']['max_wait_weeks']
        for field in numeric_fields:
            if 'week' in field.lower() and field in data.columns:
                data = data[data[field] <= max_wait]
        
        cleaned_count = len(data)
        logger.info(f"Data cleaning: {original_count} -> {cleaned_count} records ({original_count - cleaned_count} removed)")
        
        return data
    
    def _standardize_specialties(self, data: pd.DataFrame) -> pd.DataFrame:
        """标准化专科代码"""
        if 'treatment_function_code' not in data.columns:
            return data
        
        # 添加专科信息
        data['specialty_category'] = data['treatment_function_code'].map(
            lambda x: self.specialty_mapping.get(str(x), NHSSpecialty('unknown', 'Unknown', 'other')).category
        )
        
        data['specialty_description'] = data['treatment_function_code'].map(
            lambda x: self.specialty_mapping.get(str(x), NHSSpecialty('unknown', 'Unknown', 'other')).description
        )
        
        data['typical_wait_weeks'] = data['treatment_function_code'].map(
            lambda x: self.specialty_mapping.get(str(x), NHSSpecialty('unknown', 'Unknown', 'other')).typical_wait_weeks
        )
        
        # 标记优先专科
        data['is_priority_specialty'] = data['treatment_function_code'].isin(
            self.nhs_config['priority_specialties']
        )
        
        return data
    
    def _calculate_waiting_metrics(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算等候时间指标"""
        # 计算总等候人数
        wait_columns = [col for col in data.columns if 'week' in col.lower() and col != 'typical_wait_weeks']
        
        if wait_columns:
            data['total_waiting'] = data[wait_columns].sum(axis=1, skipna=True)
        
        # 计算超过18周的比例
        over_18_weeks_cols = [col for col in wait_columns if self._extract_weeks_from_column(col) > 18]
        if over_18_weeks_cols:
            data['over_18_weeks'] = data[over_18_weeks_cols].sum(axis=1, skipna=True)
            data['over_18_weeks_rate'] = data['over_18_weeks'] / data['total_waiting'].replace(0, np.nan)
        
        # 计算超过52周的比例
        over_52_weeks_cols = [col for col in wait_columns if self._extract_weeks_from_column(col) > 52]
        if over_52_weeks_cols:
            data['over_52_weeks'] = data[over_52_weeks_cols].sum(axis=1, skipna=True)
            data['over_52_weeks_rate'] = data['over_52_weeks'] / data['total_waiting'].replace(0, np.nan)
        
        # 计算中位数等候时间估算
        data['estimated_median_wait'] = self._estimate_median_wait(data, wait_columns)
        
        return data
    
    def _extract_weeks_from_column(self, column_name: str) -> int:
        """从列名提取周数"""
        import re
        
        # 查找数字模式
        matches = re.findall(r'\d+', column_name)
        if matches:
            return int(matches[0])
        
        return 0
    
    def _estimate_median_wait(self, data: pd.DataFrame, wait_columns: List[str]) -> pd.Series:
        """估算中位数等候时间"""
        # 简化的中位数估算算法
        median_waits = []
        
        for _, row in data.iterrows():
            total = row['total_waiting'] if 'total_waiting' in row else 0
            if total == 0:
                median_waits.append(0)
                continue
            
            cumulative = 0
            target = total / 2
            
            for col in sorted(wait_columns, key=self._extract_weeks_from_column):
                cumulative += row[col] if not pd.isna(row[col]) else 0
                if cumulative >= target:
                    median_waits.append(self._extract_weeks_from_column(col))
                    break
            else:
                # 如果没有找到中位数，使用最大值
                max_weeks = max([self._extract_weeks_from_column(col) for col in wait_columns])
                median_waits.append(max_weeks)
        
        return pd.Series(median_waits, index=data.index)
    
    def _enhance_geographic_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """增强地理位置数据"""
        if 'provider_org_code' not in data.columns:
            return data
        
        # 添加提供者信息
        data['provider_location'] = data['provider_org_code'].map(
            lambda x: self.provider_mapping.get(x, NHSProvider('unknown', 'Unknown', 'Unknown')).location
        )
        
        data['trust_name'] = data['provider_org_code'].map(
            lambda x: self.provider_mapping.get(x, NHSProvider('unknown', 'Unknown', 'Unknown')).trust_name
        )
        
        # 这里可以添加更多地理位置处理
        # 例如：邮编查找、距离计算等
        
        return data
    
    def _assess_data_quality(self, data: pd.DataFrame) -> float:
        """评估数据质量"""
        quality_rules = self.nhs_config['data_quality_rules']
        score = 1.0
        
        # 检查必填字段完整性
        required_fields = quality_rules['required_fields']
        for field in required_fields:
            if field in data.columns:
                completeness = data[field].notna().mean()
                score *= completeness
        
        # 检查每个提供者的记录数
        if 'provider_org_code' in data.columns:
            min_records = quality_rules['min_records_per_provider']
            provider_counts = data['provider_org_code'].value_counts()
            adequate_providers = (provider_counts >= min_records).mean()
            score *= adequate_providers
        
        # 检查数值合理性
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if data[col].notna().sum() > 0:
                # 检查负值
                non_negative_rate = (data[col] >= 0).mean()
                score *= non_negative_rate
        
        return score
    
    async def generate_waiting_time_report(self, provider_code: Optional[str] = None, 
                                         specialty_code: Optional[str] = None) -> Dict[str, Any]:
        """生成等候时间报告"""
        # 从数据库查询最新数据
        query_conditions = {}
        if provider_code:
            query_conditions['provider_org_code'] = provider_code
        if specialty_code:
            query_conditions['treatment_function_code'] = specialty_code
        
        # 这里应该实现数据库查询逻辑
        # data = await self.db.query_latest_rtt_data(query_conditions)
        
        # 模拟数据
        data = pd.DataFrame({
            'provider_org_code': ['RGT01', 'R1H'],
            'provider_org_name': ['Cambridge University Hospitals', 'Oxford University Hospitals'],
            'treatment_function_code': ['120', '330'],
            'treatment_function_name': ['ENT', 'Dermatology'],
            'total_waiting': [1500, 800],
            'over_18_weeks': [300, 200],
            'over_52_weeks': [50, 30],
            'estimated_median_wait': [16, 20]
        })
        
        # 生成统计报告
        report = {
            'generated_at': datetime.now().isoformat(),
            'filters': {
                'provider_code': provider_code,
                'specialty_code': specialty_code
            },
            'summary': {
                'total_records': len(data),
                'total_waiting': data['total_waiting'].sum(),
                'avg_median_wait': data['estimated_median_wait'].mean(),
                'over_18_weeks_rate': data['over_18_weeks'].sum() / data['total_waiting'].sum() if data['total_waiting'].sum() > 0 else 0,
                'over_52_weeks_rate': data['over_52_weeks'].sum() / data['total_waiting'].sum() if data['total_waiting'].sum() > 0 else 0
            },
            'by_provider': data.groupby('provider_org_code').agg({
                'total_waiting': 'sum',
                'estimated_median_wait': 'mean',
                'over_18_weeks': 'sum',
                'over_52_weeks': 'sum'
            }).to_dict('index'),
            'by_specialty': data.groupby('treatment_function_code').agg({
                'total_waiting': 'sum',
                'estimated_median_wait': 'mean',
                'over_18_weeks': 'sum',
                'over_52_weeks': 'sum'
            }).to_dict('index')
        }
        
        return report
    
    def get_nhs_stats(self) -> Dict[str, Any]:
        """获取NHS处理统计"""
        base_stats = self.get_processing_stats()
        
        nhs_stats = {
            'specialties_mapped': len(self.specialty_mapping),
            'providers_mapped': len(self.provider_mapping),
            'priority_specialties': len(self.nhs_config['priority_specialties'])
        }
        
        return {**base_stats, **nhs_stats} 