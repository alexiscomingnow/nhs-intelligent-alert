"""
Admin Panel - Business Management Dashboard

提供完整的管理界面，支持：
- 租户管理
- 用户管理
- 订阅和计费管理
- 系统监控和分析
- 配置管理
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

class DashboardMetric(BaseModel):
    """仪表板指标"""
    name: str
    value: float
    unit: str
    change_percentage: Optional[float] = None
    trend: Optional[str] = None  # 'up', 'down', 'stable'

class TenantStats(BaseModel):
    """租户统计"""
    tenant_id: str
    name: str
    subscription_tier: str
    monthly_revenue: float
    active_users: int
    api_calls_this_month: int
    messages_sent_this_month: int
    last_activity: datetime

class UserActivity(BaseModel):
    """用户活动记录"""
    user_id: str
    activity_type: str
    timestamp: datetime
    details: Dict[str, Any]

class AdminPanel:
    """
    管理面板主类
    
    提供完整的业务管理功能
    """
    
    def __init__(self, config_manager, user_manager, notification_service, alert_engine):
        self.config_manager = config_manager
        self.user_manager = user_manager
        self.notification_service = notification_service
        self.alert_engine = alert_engine
        
        # 创建路由器
        self.router = APIRouter(prefix="/admin", tags=["admin"])
        self._setup_routes()
        
        # 模板引擎
        template_dir = Path(__file__).parent / "templates"
        template_dir.mkdir(exist_ok=True)
        self.templates = Jinja2Templates(directory=str(template_dir))
        
        # 创建默认模板
        self._create_default_templates()
    
    def _setup_routes(self):
        """设置管理路由"""
        
        @self.router.get("/", response_class=HTMLResponse)
        async def admin_dashboard(request: Request):
            """主仪表板"""
            metrics = await self._get_dashboard_metrics()
            recent_activities = await self._get_recent_activities()
            tenant_stats = await self._get_tenant_statistics()
            
            return self.templates.TemplateResponse("dashboard.html", {
                "request": request,
                "metrics": metrics,
                "activities": recent_activities,
                "tenant_stats": tenant_stats,
                "page_title": "Business Dashboard"
            })
        
        @self.router.get("/api/metrics")
        async def get_metrics_api():
            """获取仪表板指标API"""
            return await self._get_dashboard_metrics()
        
        @self.router.get("/tenants", response_class=HTMLResponse)
        async def tenants_page(request: Request):
            """租户管理页面"""
            tenants = await self._get_all_tenants()
            return self.templates.TemplateResponse("tenants.html", {
                "request": request,
                "tenants": tenants,
                "page_title": "Tenant Management"
            })
        
        @self.router.post("/tenants")
        async def create_tenant(
            name: str = Form(...),
            subscription_tier: str = Form(...),
            contact_email: str = Form(...),
            domain: Optional[str] = Form(None)
        ):
            """创建新租户"""
            tenant_data = {
                "name": name,
                "subscription_tier": subscription_tier,
                "contact_email": contact_email,
                "domain": domain,
                "created_at": datetime.utcnow(),
                "status": "active"
            }
            
            tenant_id = await self._create_tenant(tenant_data)
            return {"success": True, "tenant_id": tenant_id}
        
        @self.router.get("/users", response_class=HTMLResponse)
        async def users_page(request: Request, tenant_id: Optional[str] = None):
            """用户管理页面"""
            users = await self._get_users(tenant_id)
            tenants = await self._get_all_tenants()
            
            return self.templates.TemplateResponse("users.html", {
                "request": request,
                "users": users,
                "tenants": tenants,
                "selected_tenant": tenant_id,
                "page_title": "User Management"
            })
        
        @self.router.get("/analytics", response_class=HTMLResponse)
        async def analytics_page(request: Request):
            """分析页面"""
            analytics_data = await self._get_analytics_data()
            
            return self.templates.TemplateResponse("analytics.html", {
                "request": request,
                "analytics": analytics_data,
                "page_title": "Analytics & Reports"
            })
        
        @self.router.get("/api/analytics/revenue")
        async def revenue_analytics(days: int = 30):
            """收入分析API"""
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            return await self._get_revenue_analytics(start_date, end_date)
        
        @self.router.get("/api/analytics/usage")
        async def usage_analytics(tenant_id: Optional[str] = None, days: int = 30):
            """使用统计API"""
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            return await self._get_usage_analytics(tenant_id, start_date, end_date)
        
        @self.router.get("/configuration", response_class=HTMLResponse)
        async def configuration_page(request: Request):
            """配置管理页面"""
            configs = await self._get_all_configurations()
            
            return self.templates.TemplateResponse("configuration.html", {
                "request": request,
                "configurations": configs,
                "page_title": "System Configuration"
            })
        
        @self.router.post("/configuration/update")
        async def update_configuration(config_data: Dict[str, Any]):
            """更新配置"""
            await self._update_configuration(config_data)
            return {"success": True, "message": "Configuration updated"}
        
        @self.router.get("/monitoring", response_class=HTMLResponse)
        async def monitoring_page(request: Request):
            """系统监控页面"""
            system_health = await self._get_system_health()
            
            return self.templates.TemplateResponse("monitoring.html", {
                "request": request,
                "system_health": system_health,
                "page_title": "System Monitoring"
            })
        
        @self.router.get("/api/system/health")
        async def system_health_api():
            """系统健康检查API"""
            return await self._get_system_health()
    
    async def _get_dashboard_metrics(self) -> List[DashboardMetric]:
        """获取仪表板核心指标"""
        # 模拟数据 - 在实际实现中会从数据库获取
        return [
            DashboardMetric(
                name="Total Revenue",
                value=25680.00,
                unit="£",
                change_percentage=12.5,
                trend="up"
            ),
            DashboardMetric(
                name="Active Users",
                value=1542,
                unit="users",
                change_percentage=8.3,
                trend="up"
            ),
            DashboardMetric(
                name="Messages Sent",
                value=48392,
                unit="messages",
                change_percentage=-2.1,
                trend="down"
            ),
            DashboardMetric(
                name="API Calls",
                value=156789,
                unit="calls",
                change_percentage=15.8,
                trend="up"
            ),
            DashboardMetric(
                name="Active Tenants",
                value=23,
                unit="tenants",
                change_percentage=4.5,
                trend="up"
            ),
            DashboardMetric(
                name="System Uptime",
                value=99.8,
                unit="%",
                change_percentage=0.1,
                trend="stable"
            )
        ]
    
    async def _get_recent_activities(self) -> List[UserActivity]:
        """获取最近活动"""
        # 模拟数据
        return [
            UserActivity(
                user_id="user_123",
                activity_type="subscription_upgrade",
                timestamp=datetime.utcnow() - timedelta(minutes=15),
                details={"from": "basic", "to": "premium"}
            ),
            UserActivity(
                user_id="user_456",
                activity_type="alert_sent",
                timestamp=datetime.utcnow() - timedelta(minutes=32),
                details={"channel": "whatsapp", "alert_type": "waiting_time"}
            ),
            UserActivity(
                user_id="user_789",
                activity_type="user_registered",
                timestamp=datetime.utcnow() - timedelta(hours=1),
                details={"tenant": "gp_practice_1", "phone": "+44xxxxxxxxxx"}
            )
        ]
    
    async def _get_tenant_statistics(self) -> List[TenantStats]:
        """获取租户统计数据"""
        # 模拟数据
        return [
            TenantStats(
                tenant_id="tenant_1",
                name="London GP Practice",
                subscription_tier="Premium",
                monthly_revenue=299.00,
                active_users=245,
                api_calls_this_month=15620,
                messages_sent_this_month=3240,
                last_activity=datetime.utcnow() - timedelta(minutes=5)
            ),
            TenantStats(
                tenant_id="tenant_2",
                name="Private Health Clinic",
                subscription_tier="Enterprise",
                monthly_revenue=999.00,
                active_users=890,
                api_calls_this_month=45300,
                messages_sent_this_month=12150,
                last_activity=datetime.utcnow() - timedelta(minutes=12)
            )
        ]
    
    async def _get_all_tenants(self) -> List[Dict[str, Any]]:
        """获取所有租户"""
        # 在实际实现中会从数据库获取
        return [
            {
                "id": "tenant_1",
                "name": "London GP Practice",
                "subscription_tier": "Premium",
                "contact_email": "admin@londongp.nhs.uk",
                "domain": "londongp.nhs.uk",
                "status": "active",
                "created_at": "2024-01-15",
                "users_count": 245,
                "monthly_revenue": 299.00
            },
            {
                "id": "tenant_2", 
                "name": "Private Health Clinic",
                "subscription_tier": "Enterprise",
                "contact_email": "tech@privateclinic.com",
                "domain": "privateclinic.com",
                "status": "active",
                "created_at": "2024-02-01",
                "users_count": 890,
                "monthly_revenue": 999.00
            }
        ]
    
    async def _create_tenant(self, tenant_data: Dict[str, Any]) -> str:
        """创建新租户"""
        # 在实际实现中会保存到数据库
        tenant_id = f"tenant_{datetime.utcnow().timestamp()}"
        
        # 创建租户配置文件
        tenant_config = {
            **tenant_data,
            "id": tenant_id,
            "api_keys": {
                "primary": f"ak_{tenant_id}_{datetime.utcnow().timestamp()}",
                "secondary": f"sk_{tenant_id}_{datetime.utcnow().timestamp()}"
            },
            "limits": self._get_subscription_limits(tenant_data["subscription_tier"]),
            "customization": {
                "branding": {
                    "logo_url": "",
                    "primary_color": "#1e40af",
                    "secondary_color": "#64748b"
                },
                "whatsapp_template": "default"
            }
        }
        
        # 保存配置
        await self.config_manager.create_tenant_config(tenant_id, tenant_config)
        
        return tenant_id
    
    def _get_subscription_limits(self, tier: str) -> Dict[str, int]:
        """获取订阅层级限制"""
        limits = {
            "Free": {
                "max_users": 10,
                "max_alerts_per_month": 100,
                "max_api_calls_per_month": 1000,
                "max_messages_per_month": 50
            },
            "Basic": {
                "max_users": 100,
                "max_alerts_per_month": 1000,
                "max_api_calls_per_month": 10000,
                "max_messages_per_month": 500
            },
            "Premium": {
                "max_users": 1000,
                "max_alerts_per_month": 10000,
                "max_api_calls_per_month": 100000,
                "max_messages_per_month": 5000
            },
            "Enterprise": {
                "max_users": -1,  # unlimited
                "max_alerts_per_month": -1,
                "max_api_calls_per_month": -1,
                "max_messages_per_month": -1
            }
        }
        return limits.get(tier, limits["Free"])
    
    async def _get_users(self, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取用户列表"""
        # 模拟数据
        return [
            {
                "id": "user_123",
                "tenant_id": "tenant_1",
                "phone_number": "+44xxxxxxxxxx",
                "email": "patient@example.com",
                "subscription_tier": "Basic",
                "status": "active",
                "created_at": "2024-01-20",
                "last_activity": "2024-03-15 14:30:00",
                "alerts_this_month": 15,
                "messages_sent": 8
            }
        ]
    
    async def _get_analytics_data(self) -> Dict[str, Any]:
        """获取分析数据"""
        return {
            "revenue_trend": {
                "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
                "data": [12500, 15600, 18200, 22100, 24800, 25680]
            },
            "user_growth": {
                "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
                "data": [850, 962, 1145, 1287, 1456, 1542]
            },
            "message_volume": {
                "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                "data": [7200, 8100, 8900, 8700, 9200, 6800, 5900]
            },
            "top_tenants": [
                {"name": "Private Health Clinic", "revenue": 999.00, "users": 890},
                {"name": "London GP Practice", "revenue": 299.00, "users": 245},
                {"name": "Birmingham Medical Center", "revenue": 199.00, "users": 156}
            ]
        }
    
    async def _get_revenue_analytics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """获取收入分析"""
        # 实际实现中会查询数据库
        return {
            "total_revenue": 25680.00,
            "mrr": 8560.00,  # Monthly Recurring Revenue
            "arr": 102720.00,  # Annual Recurring Revenue
            "average_arpu": 16.65,  # Average Revenue Per User
            "churn_rate": 2.3,
            "breakdown_by_tier": {
                "Free": {"users": 320, "revenue": 0},
                "Basic": {"users": 892, "revenue": 1784.00},
                "Premium": {"users": 267, "revenue": 15021.00},
                "Enterprise": {"users": 63, "revenue": 8875.00}
            }
        }
    
    async def _get_usage_analytics(self, tenant_id: Optional[str], start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """获取使用统计"""
        return {
            "api_calls": 156789,
            "messages_sent": 48392,
            "alerts_triggered": 12456,
            "active_users": 1542,
            "peak_usage_hour": 14,  # 2 PM
            "channel_breakdown": {
                "whatsapp": 28734,
                "sms": 12658,
                "email": 7000
            }
        }
    
    async def _get_all_configurations(self) -> Dict[str, Any]:
        """获取所有配置"""
        return {
            "system": {
                "max_concurrent_users": 10000,
                "message_rate_limit": 1000,
                "api_rate_limit": 10000
            },
            "whatsapp": {
                "business_account_id": "12345678",
                "webhook_verify_token": "verify_token_here",
                "max_template_messages_per_day": 1000
            },
            "notifications": {
                "retry_attempts": 3,
                "retry_delay_seconds": 30,
                "fallback_enabled": True
            }
        }
    
    async def _update_configuration(self, config_data: Dict[str, Any]):
        """更新配置"""
        # 实际实现中会保存到配置文件或数据库
        await self.config_manager.update_config(config_data)
    
    async def _get_system_health(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        return {
            "status": "healthy",
            "uptime": "99.8%",
            "services": {
                "database": {"status": "healthy", "response_time": "12ms"},
                "whatsapp_api": {"status": "healthy", "response_time": "156ms"},
                "sms_service": {"status": "healthy", "response_time": "89ms"},
                "email_service": {"status": "healthy", "response_time": "234ms"}
            },
            "resources": {
                "cpu_usage": "35%",
                "memory_usage": "68%",
                "disk_usage": "45%"
            },
            "recent_errors": [
                {
                    "timestamp": "2024-03-15 14:25:00",
                    "service": "whatsapp_api",
                    "error": "Rate limit exceeded",
                    "count": 3
                }
            ]
        }
    
    def _create_default_templates(self):
        """创建默认HTML模板"""
        template_dir = Path(__file__).parent / "templates"
        
        # 基础模板
        base_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ page_title }} - NHS Alert System Admin</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="bg-gray-100">
    <nav class="bg-blue-900 text-white p-4">
        <div class="container mx-auto flex justify-between items-center">
            <h1 class="text-xl font-bold">NHS Alert System Admin</h1>
            <div class="space-x-4">
                <a href="/admin/" class="hover:text-blue-200">Dashboard</a>
                <a href="/admin/tenants" class="hover:text-blue-200">Tenants</a>
                <a href="/admin/users" class="hover:text-blue-200">Users</a>
                <a href="/admin/analytics" class="hover:text-blue-200">Analytics</a>
                <a href="/admin/monitoring" class="hover:text-blue-200">Monitoring</a>
            </div>
        </div>
    </nav>
    
    <main class="container mx-auto p-6">
        {% block content %}{% endblock %}
    </main>
</body>
</html>'''
        
        # 仪表板模板
        dashboard_template = '''{% extends "base.html" %}
{% block content %}
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
    {% for metric in metrics %}
    <div class="bg-white p-6 rounded-lg shadow">
        <h3 class="text-sm font-medium text-gray-500">{{ metric.name }}</h3>
        <div class="mt-2 flex items-baseline">
            <span class="text-3xl font-semibold text-gray-900">
                {% if metric.unit == "£" %}£{% endif %}{{ metric.value }}{% if metric.unit != "£" %}{{ metric.unit }}{% endif %}
            </span>
            {% if metric.change_percentage %}
            <span class="ml-2 text-sm font-medium {% if metric.trend == 'up' %}text-green-600{% elif metric.trend == 'down' %}text-red-600{% else %}text-gray-500{% endif %}">
                {{ metric.change_percentage }}%
            </span>
            {% endif %}
        </div>
    </div>
    {% endfor %}
</div>

<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <div class="bg-white p-6 rounded-lg shadow">
        <h3 class="text-lg font-medium mb-4">Recent Activities</h3>
        <div class="space-y-3">
            {% for activity in activities %}
            <div class="flex items-center justify-between py-2 border-b">
                <div>
                    <span class="font-medium">{{ activity.activity_type.replace('_', ' ').title() }}</span>
                    <span class="text-gray-500 text-sm ml-2">{{ activity.user_id }}</span>
                </div>
                <span class="text-gray-400 text-sm">{{ activity.timestamp.strftime('%H:%M') }}</span>
            </div>
            {% endfor %}
        </div>
    </div>
    
    <div class="bg-white p-6 rounded-lg shadow">
        <h3 class="text-lg font-medium mb-4">Top Tenants</h3>
        <div class="space-y-3">
            {% for tenant in tenant_stats %}
            <div class="flex items-center justify-between py-2 border-b">
                <div>
                    <span class="font-medium">{{ tenant.name }}</span>
                    <span class="text-gray-500 text-sm ml-2">{{ tenant.active_users }} users</span>
                </div>
                <span class="text-green-600 font-medium">£{{ tenant.monthly_revenue }}</span>
            </div>
            {% endfor %}
        </div>
    </div>
</div>
{% endblock %}'''
        
        # 写入模板文件
        with open(template_dir / "base.html", "w", encoding="utf-8") as f:
            f.write(base_template)
        
        with open(template_dir / "dashboard.html", "w", encoding="utf-8") as f:
            f.write(dashboard_template)
        
        # 其他模板可以类似创建... 