"""
通用数据处理器 - 基于当前NHS ETL实现的通用化扩展

特性：
1. 支持多种数据源 (API, CSV, JSON, XML等)
2. 可插拔的数据发现算法
3. 智能数据清洗和验证
4. 增量更新和去重
5. 数据质量监控
6. 可配置的数据转换管道
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import pandas as pd
import json
import hashlib
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class DataSource:
    """数据源配置"""
    name: str
    type: str  # 'csv', 'api', 'json', 'xml', 'database'
    url: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    refresh_interval: int = 3600  # 秒
    last_updated: Optional[datetime] = None
    discovery_strategies: List[str] = field(default_factory=list)

@dataclass
class ProcessingResult:
    """数据处理结果"""
    success: bool
    records_processed: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    data_quality_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class DataDiscoveryStrategy(ABC):
    """数据发现策略抽象基类"""
    
    @abstractmethod
    async def discover(self, source: DataSource) -> List[str]:
        """发现数据源URL"""
        pass
    
    @abstractmethod
    def get_priority(self) -> int:
        """获取策略优先级 (数字越小优先级越高)"""
        pass

class EnhancedHTMLStrategy(DataDiscoveryStrategy):
    """增强HTML解析策略 - 基于NHS实现"""
    
    def __init__(self, session=None):
        self.session = session
    
    async def discover(self, source: DataSource) -> List[str]:
        """通过HTML解析发现数据链接"""
        from bs4 import BeautifulSoup
        import aiohttp
        
        urls = []
        config = source.config
        
        headers = {
            'User-Agent': config.get('user_agent', 
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        }
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(source.url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # 根据配置查找链接
                        selectors = config.get('link_selectors', ['a[href$=".csv"]', 'a[href$=".xlsx"]'])
                        
                        for selector in selectors:
                            links = soup.select(selector)
                            for link in links:
                                href = link.get('href')
                                if href:
                                    if href.startswith('/'):
                                        href = f"{source.url.rstrip('/')}{href}"
                                    elif not href.startswith('http'):
                                        href = f"{source.url.rstrip('/')}/{href}"
                                    urls.append(href)
                        
                        logger.info(f"HTML strategy found {len(urls)} URLs for {source.name}")
                        
        except Exception as e:
            logger.error(f"HTML discovery failed for {source.name}: {e}")
        
        return urls
    
    def get_priority(self) -> int:
        return 1

class PlaywrightStrategy(DataDiscoveryStrategy):
    """Playwright浏览器自动化策略"""
    
    async def discover(self, source: DataSource) -> List[str]:
        """通过浏览器自动化发现数据链接"""
        try:
            from playwright.async_api import async_playwright
            
            urls = []
            config = source.config
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                await page.goto(source.url, timeout=30000)
                await page.wait_for_load_state('networkidle')
                
                # 查找下载链接
                selectors = config.get('link_selectors', ['a[href*=".csv"]', 'a[href*=".xlsx"]'])
                
                for selector in selectors:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        href = await element.get_attribute('href')
                        if href:
                            if href.startswith('/'):
                                href = f"{source.url.rstrip('/')}{href}"
                            elif not href.startswith('http'):
                                href = f"{source.url.rstrip('/')}/{href}"
                            urls.append(href)
                
                await browser.close()
                
                logger.info(f"Playwright strategy found {len(urls)} URLs for {source.name}")
                
        except ImportError:
            logger.warning("Playwright not available, skipping browser strategy")
        except Exception as e:
            logger.error(f"Playwright discovery failed for {source.name}: {e}")
        
        return urls
    
    def get_priority(self) -> int:
        return 2

class SmartURLStrategy(DataDiscoveryStrategy):
    """智能URL构造策略"""
    
    async def discover(self, source: DataSource) -> List[str]:
        """通过智能URL构造发现数据"""
        urls = []
        config = source.config
        
        base_patterns = config.get('url_patterns', [])
        date_range = config.get('date_range_months', 6)
        
        current_date = datetime.now()
        
        for months_back in range(date_range):
            test_date = current_date - timedelta(days=30 * months_back)
            
            for pattern in base_patterns:
                # 替换日期占位符
                test_url = pattern.format(
                    year=test_date.year,
                    month=test_date.month,
                    month_name=test_date.strftime('%B'),
                    month_short=test_date.strftime('%b')
                )
                urls.append(test_url)
        
        logger.info(f"Smart URL strategy generated {len(urls)} URLs for {source.name}")
        return urls
    
    def get_priority(self) -> int:
        return 3

class DataTransformer(ABC):
    """数据转换器抽象基类"""
    
    @abstractmethod
    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """转换数据"""
        pass

class StandardDataTransformer(DataTransformer):
    """标准数据转换器"""
    
    def transform(self, data: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """执行标准数据转换"""
        
        # 列名标准化
        if config.get('normalize_columns', True):
            data.columns = data.columns.str.lower().str.replace(' ', '_').str.replace('[^a-z0-9_]', '', regex=True)
        
        # 数据类型转换
        type_mappings = config.get('column_types', {})
        for col, dtype in type_mappings.items():
            if col in data.columns:
                try:
                    data[col] = data[col].astype(dtype)
                except Exception as e:
                    logger.warning(f"Failed to convert {col} to {dtype}: {e}")
        
        # 数据清洗
        if config.get('remove_duplicates', True):
            initial_count = len(data)
            data = data.drop_duplicates()
            removed = initial_count - len(data)
            if removed > 0:
                logger.info(f"Removed {removed} duplicate rows")
        
        # 空值处理
        null_strategy = config.get('null_strategy', 'keep')
        if null_strategy == 'drop':
            data = data.dropna()
        elif null_strategy == 'fill':
            fill_values = config.get('fill_values', {})
            data = data.fillna(fill_values)
        
        return data

class DataProcessor:
    """
    通用数据处理器
    
    基于NHS ETL实现的通用化扩展，支持：
    - 多种数据源发现策略
    - 可配置的数据转换管道
    - 增量更新和去重
    - 数据质量监控
    - 异步并发处理
    """
    
    def __init__(self, database_manager, config_manager):
        self.db = database_manager
        self.config = config_manager
        
        # 初始化发现策略
        self.discovery_strategies = {
            'html': EnhancedHTMLStrategy(),
            'playwright': PlaywrightStrategy(), 
            'smart_url': SmartURLStrategy()
        }
        
        # 初始化转换器
        self.transformer = StandardDataTransformer()
        
        # 数据源注册表
        self.data_sources: Dict[str, DataSource] = {}
        
        # 处理统计
        self.processing_stats = {}
    
    def register_data_source(self, source: DataSource):
        """注册数据源"""
        self.data_sources[source.name] = source
        logger.info(f"Registered data source: {source.name}")
    
    def register_discovery_strategy(self, name: str, strategy: DataDiscoveryStrategy):
        """注册自定义发现策略"""
        self.discovery_strategies[name] = strategy
        logger.info(f"Registered discovery strategy: {name}")
    
    async def discover_data_urls(self, source: DataSource) -> List[str]:
        """
        发现数据URLs - 基于NHS多策略实现
        """
        all_urls = []
        
        # 按优先级排序策略
        strategies = source.discovery_strategies or ['html', 'playwright', 'smart_url']
        sorted_strategies = sorted(
            [(name, self.discovery_strategies[name]) for name in strategies if name in self.discovery_strategies],
            key=lambda x: x[1].get_priority()
        )
        
        for strategy_name, strategy in sorted_strategies:
            try:
                urls = await strategy.discover(source)
                all_urls.extend(urls)
                
                if urls:
                    logger.info(f"Strategy '{strategy_name}' found {len(urls)} URLs for {source.name}")
                
            except Exception as e:
                logger.error(f"Strategy '{strategy_name}' failed for {source.name}: {e}")
        
        # 去重并验证
        unique_urls = list(set(all_urls))
        validated_urls = await self._validate_urls(unique_urls)
        
        logger.info(f"Total {len(validated_urls)} valid URLs discovered for {source.name}")
        return validated_urls
    
    async def _validate_urls(self, urls: List[str]) -> List[str]:
        """验证URL可用性"""
        import aiohttp
        
        valid_urls = []
        
        async with aiohttp.ClientSession() as session:
            for url in urls:
                try:
                    async with session.head(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            valid_urls.append(url)
                        else:
                            logger.warning(f"URL validation failed: {url} (status: {response.status})")
                            
                except Exception as e:
                    logger.warning(f"URL validation error: {url} - {e}")
        
        return valid_urls
    
    async def process_data_source(self, source_name: str, force_refresh: bool = False) -> ProcessingResult:
        """
        处理单个数据源
        """
        if source_name not in self.data_sources:
            return ProcessingResult(success=False, errors=[f"Data source '{source_name}' not found"])
        
        source = self.data_sources[source_name]
        
        if not source.enabled:
            return ProcessingResult(success=False, errors=[f"Data source '{source_name}' is disabled"])
        
        # 检查是否需要刷新
        if not force_refresh and source.last_updated:
            time_since_update = datetime.now() - source.last_updated
            if time_since_update.total_seconds() < source.refresh_interval:
                logger.info(f"Data source '{source_name}' is up to date, skipping")
                return ProcessingResult(success=True, records_skipped=1)
        
        start_time = datetime.now()
        result = ProcessingResult(success=False)
        
        try:
            # 发现数据URLs
            logger.info(f"Starting data discovery for source: {source_name}")
            urls = await self.discover_data_urls(source)
            
            if not urls:
                result.errors.append(f"No valid data URLs found for {source_name}")
                return result
            
            # 处理数据
            for url in urls[:3]:  # 限制处理前3个最新的URL
                try:
                    data_result = await self._process_data_url(url, source)
                    
                    result.records_processed += data_result.records_processed
                    result.records_inserted += data_result.records_inserted
                    result.records_updated += data_result.records_updated
                    result.warnings.extend(data_result.warnings)
                    
                    if data_result.success:
                        break  # 成功处理一个URL即可
                        
                except Exception as e:
                    error_msg = f"Failed to process URL {url}: {e}"
                    logger.error(error_msg)
                    result.errors.append(error_msg)
            
            # 更新状态
            source.last_updated = datetime.now()
            result.success = result.records_processed > 0
            result.processing_time = (datetime.now() - start_time).total_seconds()
            
            # 计算数据质量分数
            result.data_quality_score = self._calculate_data_quality_score(result)
            
            logger.info(f"Processed {result.records_processed} records for {source_name}")
            
        except Exception as e:
            error_msg = f"Data processing failed for {source_name}: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)
        
        # 更新统计
        self.processing_stats[source_name] = result
        
        return result
    
    async def _process_data_url(self, url: str, source: DataSource) -> ProcessingResult:
        """处理单个数据URL"""
        result = ProcessingResult(success=False)
        
        try:
            # 下载数据
            if url.endswith('.zip'):
                data = await self._load_zip_data(url, source.config)
            elif url.endswith(('.csv', '.xlsx')):
                data = await self._load_file_data(url, source.config)
            else:
                result.errors.append(f"Unsupported file type: {url}")
                return result
            
            if data is None or data.empty:
                result.errors.append(f"No data loaded from {url}")
                return result
            
            result.records_processed = len(data)
            
            # 数据转换
            data = self.transformer.transform(data, source.config.get('transformation', {}))
            
            # 数据加载到数据库
            load_result = await self._load_to_database(data, source)
            result.records_inserted = load_result.get('inserted', 0)
            result.records_updated = load_result.get('updated', 0)
            
            result.success = True
            
        except Exception as e:
            result.errors.append(f"Error processing {url}: {e}")
        
        return result
    
    async def _load_zip_data(self, url: str, config: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """加载ZIP文件数据 - 基于NHS实现"""
        import zipfile
        import io
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        zip_content = await response.read()
                        
                        with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_file:
                            # 查找CSV文件，优先级：provider > extract > rtt > 任意CSV
                            csv_files = [f for f in zip_file.namelist() if f.endswith('.csv')]
                            
                            if not csv_files:
                                logger.warning(f"No CSV files found in {url}")
                                return None
                            
                            # 按优先级排序
                            priority_keywords = config.get('csv_priority', ['provider', 'extract', 'rtt'])
                            
                            for keyword in priority_keywords:
                                for csv_file in csv_files:
                                    if keyword.lower() in csv_file.lower():
                                        logger.info(f"Loading priority CSV: {csv_file}")
                                        with zip_file.open(csv_file) as f:
                                            return pd.read_csv(f, encoding='utf-8')
                            
                            # 使用第一个CSV文件
                            csv_file = csv_files[0]
                            logger.info(f"Loading first available CSV: {csv_file}")
                            with zip_file.open(csv_file) as f:
                                return pd.read_csv(f, encoding='utf-8')
                    
        except Exception as e:
            logger.error(f"Failed to load ZIP data from {url}: {e}")
            
        return None
    
    async def _load_file_data(self, url: str, config: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """加载文件数据"""
        try:
            if url.endswith('.csv'):
                return pd.read_csv(url, encoding='utf-8')
            elif url.endswith('.xlsx'):
                return pd.read_excel(url)
        except Exception as e:
            logger.error(f"Failed to load file data from {url}: {e}")
        
        return None
    
    async def _load_to_database(self, data: pd.DataFrame, source: DataSource) -> Dict[str, int]:
        """加载数据到数据库"""
        table_name = source.config.get('table_name', source.name.lower())
        
        # 这里需要根据具体的数据库实现来完成
        # 基于NHS实现，支持JSONB存储和重复检测
        
        inserted = 0
        updated = 0
        
        try:
            # 生成数据哈希用于去重
            data['data_hash'] = data.apply(
                lambda row: hashlib.md5(str(row.to_dict()).encode()).hexdigest(), 
                axis=1
            )
            
            # 批量插入/更新
            for _, row in data.iterrows():
                # 这里应该调用数据库管理器的方法
                # await self.db.upsert_record(table_name, row.to_dict())
                inserted += 1
            
        except Exception as e:
            logger.error(f"Database load failed: {e}")
            raise
        
        return {"inserted": inserted, "updated": updated}
    
    def _calculate_data_quality_score(self, result: ProcessingResult) -> float:
        """计算数据质量分数"""
        if result.records_processed == 0:
            return 0.0
        
        # 基础分数
        base_score = 0.8
        
        # 错误惩罚
        error_penalty = len(result.errors) * 0.1
        
        # 警告惩罚
        warning_penalty = len(result.warnings) * 0.05
        
        # 成功率奖励
        success_bonus = (result.records_inserted + result.records_updated) / result.records_processed * 0.2
        
        score = base_score + success_bonus - error_penalty - warning_penalty
        return max(0.0, min(1.0, score))
    
    async def process_all_sources(self, force_refresh: bool = False) -> Dict[str, ProcessingResult]:
        """处理所有数据源"""
        results = {}
        
        # 并发处理所有启用的数据源
        tasks = []
        for source_name, source in self.data_sources.items():
            if source.enabled:
                task = asyncio.create_task(
                    self.process_data_source(source_name, force_refresh)
                )
                tasks.append((source_name, task))
        
        # 等待所有任务完成
        for source_name, task in tasks:
            try:
                result = await task
                results[source_name] = result
            except Exception as e:
                logger.error(f"Task failed for {source_name}: {e}")
                results[source_name] = ProcessingResult(
                    success=False, 
                    errors=[f"Processing task failed: {e}"]
                )
        
        return results
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        total_sources = len(self.data_sources)
        enabled_sources = sum(1 for s in self.data_sources.values() if s.enabled)
        
        recent_results = list(self.processing_stats.values())
        successful_runs = sum(1 for r in recent_results if r.success)
        
        return {
            "total_sources": total_sources,
            "enabled_sources": enabled_sources,
            "recent_success_rate": successful_runs / max(1, len(recent_results)),
            "total_records_processed": sum(r.records_processed for r in recent_results),
            "average_processing_time": sum(r.processing_time for r in recent_results) / max(1, len(recent_results)),
            "average_quality_score": sum(r.data_quality_score for r in recent_results) / max(1, len(recent_results))
        } 