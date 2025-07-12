"""
API网关 - FastAPI RESTful API服务

特性：
1. RESTful API设计
2. 多租户支持
3. 认证和授权
4. API限流
5. 自动文档生成
6. 错误处理
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
import json
import jwt
from passlib.context import CryptContext

from fastapi import FastAPI, HTTPException, Depends, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from ..core.config_manager import ConfigManager
from ..core.user_manager import UserManager
from ..core.notification_service import NotificationService
from ..core.alert_engine import AlertEngine
from ..nhs_application.patient_service import PatientService

logger = logging.getLogger(__name__)

# Pydantic模型定义
class PatientCreateRequest(BaseModel):
    """患者创建请求"""
    phone_number: Optional[str] = None
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    postcode: Optional[str] = None
    nhs_number: Optional[str] = None
    medical_specialties: List[str] = Field(default_factory=list)
    preferred_travel_distance: int = Field(50, ge=1, le=500)
    max_acceptable_wait_weeks: int = Field(18, ge=1, le=100)
    language_preference: str = "en"
    
class PatientUpdateRequest(BaseModel):
    """患者更新请求"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    postcode: Optional[str] = None
    medical_specialties: Optional[List[str]] = None
    preferred_travel_distance: Optional[int] = Field(None, ge=1, le=500)
    max_acceptable_wait_weeks: Optional[int] = Field(None, ge=1, le=100)
    consider_private_options: Optional[bool] = None

class SubscriptionCreateRequest(BaseModel):
    """订阅创建请求"""
    specialty_codes: List[str] = Field(..., min_items=1)
    provider_codes: List[str] = Field(default_factory=list)
    max_distance_km: int = Field(50, ge=1, le=500)
    alert_threshold_weeks: int = Field(18, ge=1, le=100)

class AlertResponse(BaseModel):
    """提醒响应"""
    id: str
    title: str
    message: str
    severity: str
    created_at: str
    data: Dict[str, Any]
    actions: List[Dict[str, Any]]

class APIError(BaseModel):
    """API错误响应"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None

class RateLimiter:
    """API限流器"""
    
    def __init__(self):
        self.requests: Dict[str, List[datetime]] = {}
        self.limits = {
            'default': {'requests': 100, 'window': 3600},  # 100 requests per hour
            'premium': {'requests': 1000, 'window': 3600},  # 1000 requests per hour
            'admin': {'requests': 10000, 'window': 3600}    # 10000 requests per hour
        }
    
    def is_allowed(self, key: str, tier: str = 'default') -> bool:
        """检查是否允许请求"""
        now = datetime.now()
        limit_config = self.limits.get(tier, self.limits['default'])
        
        if key not in self.requests:
            self.requests[key] = []
        
        # 清理过期请求
        cutoff_time = now - timedelta(seconds=limit_config['window'])
        self.requests[key] = [req_time for req_time in self.requests[key] if req_time > cutoff_time]
        
        # 检查限制
        if len(self.requests[key]) >= limit_config['requests']:
            return False
        
        # 记录请求
        self.requests[key].append(now)
        return True

class APIGateway:
    """
    API网关
    
    提供完整的RESTful API服务，支持：
    - 患者管理
    - 订阅管理
    - 提醒查询
    - 数据报告
    - 管理功能
    """
    
    def __init__(self, config_manager: ConfigManager, user_manager: UserManager, 
                 notification_service: NotificationService, alert_engine: AlertEngine,
                 patient_service: PatientService):
        
        self.config = config_manager
        self.user_manager = user_manager
        self.notification_service = notification_service
        self.alert_engine = alert_engine
        self.patient_service = patient_service
        
        # 初始化FastAPI应用
        self.app = FastAPI(
            title="NHS Alert System API",
            description="NHS等候时间提醒系统API",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # 认证
        self.security = HTTPBearer()
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # 限流器
        self.rate_limiter = RateLimiter()
        
        # 配置中间件
        self._setup_middleware()
        
        # 注册路由
        self._register_routes()
        
        # 错误处理
        self._setup_error_handlers()
    
    def _setup_middleware(self):
        """配置中间件"""
        # CORS中间件
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # 生产环境应该限制
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 限流中间件
        @self.app.middleware("http")
        async def rate_limit_middleware(request: Request, call_next):
            client_ip = request.client.host
            auth_header = request.headers.get("authorization")
            
            # 确定用户层级
            tier = 'default'
            if auth_header:
                try:
                    user = await self._get_current_user(auth_header)
                    if user:
                        subscription = await self.user_manager.get_user_subscription(user.user_id)
                        if subscription:
                            tier = subscription.tier.value
                except:
                    pass
            
            # 检查限流
            if not self.rate_limiter.is_allowed(client_ip, tier):
                return JSONResponse(
                    status_code=429,
                    content={"error": "rate_limit_exceeded", "message": "Too many requests"}
                )
            
            response = await call_next(request)
            return response
        
        # 请求日志中间件
        @self.app.middleware("http")
        async def logging_middleware(request: Request, call_next):
            start_time = datetime.now()
            
            response = await call_next(request)
            
            process_time = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"{request.method} {request.url.path} - "
                f"Status: {response.status_code} - "
                f"Time: {process_time:.3f}s"
            )
            
            return response
    
    def _register_routes(self):
        """注册API路由"""
        
        # 健康检查
        @self.app.get("/health")
        async def health_check():
            """健康检查端点"""
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}
        
        # 患者管理路由
        @self.app.post("/api/v1/patients", response_model=Dict[str, Any])
        async def create_patient(
            request: PatientCreateRequest,
            current_user = Depends(self._get_current_user_dependency)
        ):
            """创建患者档案"""
            try:
                patient = await self.patient_service.create_patient(
                    request.dict(exclude_unset=True),
                    tenant_id=getattr(current_user, 'tenant_id', None)
                )
                return {"success": True, "patient_id": patient.user_id}
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/api/v1/patients/{patient_id}")
        async def get_patient(
            patient_id: str,
            current_user = Depends(self._get_current_user_dependency)
        ):
            """获取患者档案"""
            # 权限检查：只能访问自己的档案或管理员
            if patient_id != current_user.user_id and current_user.role.value != 'admin':
                raise HTTPException(status_code=403, detail="Access denied")
            
            patient = await self.patient_service.get_patient(patient_id)
            if not patient:
                raise HTTPException(status_code=404, detail="Patient not found")
            
            # 移除敏感信息
            patient_dict = patient.__dict__.copy()
            if 'nhs_number' in patient_dict:
                patient_dict['nhs_number'] = '****'
            
            return patient_dict
        
        @self.app.put("/api/v1/patients/{patient_id}")
        async def update_patient(
            patient_id: str,
            request: PatientUpdateRequest,
            current_user = Depends(self._get_current_user_dependency)
        ):
            """更新患者档案"""
            if patient_id != current_user.user_id and current_user.role.value != 'admin':
                raise HTTPException(status_code=403, detail="Access denied")
            
            try:
                patient = await self.patient_service.update_patient_preferences(
                    patient_id, 
                    request.dict(exclude_unset=True)
                )
                return {"success": True, "updated_at": patient.updated_at.isoformat()}
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        # 订阅管理路由
        @self.app.post("/api/v1/patients/{patient_id}/subscriptions")
        async def create_subscription(
            patient_id: str,
            request: SubscriptionCreateRequest,
            current_user = Depends(self._get_current_user_dependency)
        ):
            """创建等候时间订阅"""
            if patient_id != current_user.user_id and current_user.role.value != 'admin':
                raise HTTPException(status_code=403, detail="Access denied")
            
            try:
                subscription = await self.patient_service.create_waiting_time_subscription(
                    patient_id=patient_id,
                    **request.dict()
                )
                return {"success": True, "subscription_id": subscription.id}
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/api/v1/patients/{patient_id}/subscriptions")
        async def get_subscriptions(
            patient_id: str,
            current_user = Depends(self._get_current_user_dependency)
        ):
            """获取患者订阅列表"""
            if patient_id != current_user.user_id and current_user.role.value != 'admin':
                raise HTTPException(status_code=403, detail="Access denied")
            
            subscriptions = await self.patient_service.get_patient_subscriptions(patient_id)
            return [sub.__dict__ for sub in subscriptions]
        
        # 提醒查询路由
        @self.app.get("/api/v1/patients/{patient_id}/alerts", response_model=List[AlertResponse])
        async def get_patient_alerts(
            patient_id: str,
            current_user = Depends(self._get_current_user_dependency)
        ):
            """获取患者提醒"""
            if patient_id != current_user.user_id and current_user.role.value != 'admin':
                raise HTTPException(status_code=403, detail="Access denied")
            
            alerts = await self.patient_service.process_patient_alerts(patient_id)
            return alerts
        
        # 数据报告路由
        @self.app.get("/api/v1/reports/waiting-times")
        async def get_waiting_time_report(
            provider_code: Optional[str] = None,
            specialty_code: Optional[str] = None,
            current_user = Depends(self._get_current_user_dependency)
        ):
            """获取等候时间报告"""
            # 这里可以添加权限检查
            from ..nhs_application.nhs_data_processor import NHSDataProcessor
            
            # 需要获取NHS数据处理器实例
            # report = await nhs_processor.generate_waiting_time_report(provider_code, specialty_code)
            
            # 模拟报告数据
            report = {
                "generated_at": datetime.now().isoformat(),
                "filters": {
                    "provider_code": provider_code,
                    "specialty_code": specialty_code
                },
                "summary": {
                    "total_records": 100,
                    "avg_median_wait": 16.5,
                    "over_18_weeks_rate": 0.25
                }
            }
            
            return report
        
        # 管理路由
        @self.app.get("/api/v1/admin/stats")
        async def get_system_stats(
            current_user = Depends(self._get_admin_user_dependency)
        ):
            """获取系统统计信息"""
            return {
                "users": self.user_manager.get_stats(),
                "notifications": self.notification_service.get_stats(),
                "alerts": self.alert_engine.get_stats(),
                "patients": self.patient_service.get_stats()
            }
        
        @self.app.post("/api/v1/admin/tenants")
        async def create_tenant(
            tenant_data: Dict[str, Any],
            current_user = Depends(self._get_admin_user_dependency)
        ):
            """创建租户"""
            try:
                tenant = self.config.create_tenant(tenant_data)
                return {"success": True, "tenant_id": tenant.tenant_id}
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
    
    def _setup_error_handlers(self):
        """设置错误处理器"""
        
        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content=APIError(
                    error="http_error",
                    message=exc.detail
                ).dict()
            )
        
        @self.app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            logger.error(f"Unhandled exception: {exc}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content=APIError(
                    error="internal_error",
                    message="Internal server error"
                ).dict()
            )
    
    async def _get_current_user(self, authorization: str):
        """获取当前用户"""
        try:
            # 移除"Bearer "前缀
            if authorization.startswith("Bearer "):
                token = authorization[7:]
            else:
                token = authorization
            
            # 解析JWT token
            business_config = self.config.get_business_config()
            secret_key = business_config.apis.get('jwt_secret', 'your-secret-key')
            
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])
            user_id = payload.get("user_id")
            
            if not user_id:
                return None
            
            # 获取用户信息
            user = await self.user_manager.get_user(user_id)
            return user
            
        except jwt.PyJWTError:
            return None
        except Exception:
            return None
    
    def _get_current_user_dependency(self):
        """获取当前用户依赖"""
        async def dependency(credentials: HTTPAuthorizationCredentials = Depends(self.security)):
            user = await self._get_current_user(credentials.credentials)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return user
        return dependency
    
    def _get_admin_user_dependency(self):
        """获取管理员用户依赖"""
        async def dependency(current_user = Depends(self._get_current_user_dependency())):
            if current_user.role.value not in ['admin', 'super_admin']:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required"
                )
            return current_user
        return dependency
    
    async def generate_access_token(self, user_id: str, expires_delta: Optional[timedelta] = None) -> str:
        """生成访问令牌"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=24)
        
        to_encode = {"user_id": user_id, "exp": expire}
        
        business_config = self.config.get_business_config()
        secret_key = business_config.apis.get('jwt_secret', 'your-secret-key')
        
        encoded_jwt = jwt.encode(to_encode, secret_key, algorithm="HS256")
        return encoded_jwt
    
    def run(self, host: str = "0.0.0.0", port: int = 8000, debug: bool = False):
        """运行API服务器"""
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            debug=debug,
            log_level="info" if not debug else "debug"
        ) 