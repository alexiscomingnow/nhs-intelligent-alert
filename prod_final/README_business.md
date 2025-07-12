# NHS Alert System - Business Framework

一个通用的、可复用的商业化框架，基于NHS等候时间提醒系统的实际需求开发。该框架可以轻松适配到其他数据驱动的通知和提醒业务场景。

## 🎯 核心特性

### 通用业务框架
- **模块化设计** - 每个组件独立，可单独使用或组合
- **可配置架构** - 通过配置文件适配不同业务场景
- **可扩展插件** - 支持自定义数据源、通知渠道和业务规则
- **多租户支持** - 支持白标解决方案和SaaS模式

### 核心功能组件
- **数据处理引擎** - 智能数据发现、清洗和转换
- **智能提醒引擎** - 规则引擎支持多维度分析和个性化提醒
- **多渠道通知** - WhatsApp、SMS、Email统一管理
- **用户管理系统** - 订阅管理、计费集成、使用统计
- **RESTful API** - 完整的API服务和管理后台

### NHS特定实现
- **NHS数据集成** - 自动发现和处理NHS England RTT数据
- **等候时间分析** - 趋势分析、异常检测、对比推荐
- **患者服务** - NHS号码验证、邮编解析、专科映射
- **WhatsApp Flow** - 友好的患者交互界面

## 🏗️ 架构设计

```
├── business_framework/          # 通用业务框架
│   ├── core/                   # 核心组件
│   │   ├── config_manager.py   # 配置管理
│   │   ├── data_processor.py   # 数据处理引擎
│   │   ├── alert_engine.py     # 智能提醒引擎
│   │   ├── notification_service.py # 通知服务
│   │   └── user_manager.py     # 用户管理
│   ├── integrations/           # 外部集成
│   │   ├── whatsapp_client.py  # WhatsApp Business API
│   │   ├── sms_client.py       # SMS服务集成
│   │   └── email_client.py     # 邮件服务集成
│   ├── api/                    # API服务
│   │   ├── api_gateway.py      # FastAPI网关
│   │   ├── webhook_handler.py  # Webhook处理
│   │   └── admin_panel.py      # 管理后台
│   └── nhs_application/        # NHS特定实现
│       ├── nhs_data_processor.py # NHS数据处理
│       ├── patient_service.py   # 患者服务
│       └── hospital_recommender.py # 医院推荐
├── config/                     # 配置文件
│   ├── business.dev.yaml      # 开发环境配置
│   ├── business.prod.yaml     # 生产环境配置
│   └── tenants/              # 租户配置
└── main.py                    # 主应用入口
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd nhs-alert-system/prod_final

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements_business.txt

# 安装Playwright浏览器
playwright install chromium
```

### 2. 配置设置

```bash
# 复制配置文件
cp config.env.example config.env

# 编辑配置文件，设置数据库和API密钥
nano config.env
```

### 3. 运行方式

#### 仅ETL数据处理
```bash
python main.py --mode etl --env dev
```

#### 仅API服务
```bash
python main.py --mode api --env dev --host 0.0.0.0 --port 8000
```

#### 完整系统
```bash
python main.py --mode full --env dev
```

访问API文档：http://localhost:8000/docs

## 📊 主要功能

### 1. 数据处理引擎

智能数据发现和处理：

```python
from business_framework import DataProcessor, DataSource

# 创建数据处理器
processor = DataProcessor(database_manager, config_manager)

# 注册数据源
source = DataSource(
    name="my_data_source",
    type="csv",
    url="https://example.com/data",
    config={
        'discovery_strategies': ['html', 'playwright'],
        'transformation': {'normalize_columns': True}
    }
)
processor.register_data_source(source)

# 处理数据
results = await processor.process_all_sources()
```

### 2. 智能提醒引擎

创建和管理提醒规则：

```python
from business_framework import AlertEngine, AlertRule, AlertType

# 创建提醒规则
rule = AlertRule(
    id="threshold_alert",
    name="阈值提醒",
    type=AlertType.THRESHOLD,
    conditions={
        'field': 'waiting_time',
        'threshold': 18,
        'operator': 'gt'
    }
)

await alert_engine.create_rule(rule.__dict__)

# 评估用户提醒
alerts = await alert_engine.evaluate_user_alerts(user_id, context)
```

### 3. 多渠道通知

统一的通知接口：

```python
from business_framework import NotificationService, MessageRequest

# 发送WhatsApp消息
request = MessageRequest(
    recipient="+44xxxxxxxxxx",
    channel=MessageChannel.WHATSAPP,
    body="您的等候时间已更新",
    actions=[
        {"id": "view_details", "text": "查看详情"}
    ]
)

result = await notification_service.send_message(request)
```

### 4. 用户和订阅管理

完整的用户生命周期管理：

```python
# 创建用户
user = await user_manager.create_user({
    'phone_number': '+44xxxxxxxxxx',
    'email': 'user@example.com'
})

# 升级订阅
await user_manager.upgrade_subscription(user.user_id, SubscriptionTier.PREMIUM)

# 记录使用量
await user_manager.record_usage(user.user_id, 'alert_sent', quantity=1)
```

## 🔧 配置说明

### 环境变量

```bash
# 数据库
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nhs_alert
DB_USER=postgres
DB_PASSWORD=your_password

# WhatsApp Business API
WHATSAPP_PHONE_ID=your_phone_number_id
WHATSAPP_ACCESS_TOKEN=your_access_token
WHATSAPP_WEBHOOK_TOKEN=your_webhook_token

# SMS (Twilio)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+1234567890

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
FROM_EMAIL=noreply@your-domain.com

# 安全
JWT_SECRET=your-secret-key
```

### 业务配置

主要配置在 `config/business.{env}.yaml` 中：

```yaml
business_rules:
  max_alerts_per_user_per_day: 10
  alert_cooldown_minutes: 60
  
notifications:
  whatsapp:
    enabled: true
  sms:
    enabled: true
    provider: "twilio"
  email:
    enabled: true
    provider: "smtp"
```

## 🏥 NHS特定功能

### 患者管理

```python
from business_framework.nhs_application import PatientService

# 创建患者档案
patient = await patient_service.create_patient({
    'phone_number': '+44xxxxxxxxxx',
    'nhs_number': '1234567890',
    'postcode': 'CB2 1QT',
    'medical_specialties': ['120', '330'],  # ENT, Dermatology
    'preferred_travel_distance': 50
})

# 创建等候时间订阅
subscription = await patient_service.create_waiting_time_subscription(
    patient_id=patient.user_id,
    specialty_codes=['120'],
    alert_threshold_weeks=18
)
```

### NHS数据处理

```python
from business_framework.nhs_application import NHSDataProcessor

# 创建NHS数据处理器
nhs_processor = NHSDataProcessor(database_manager, config_manager)

# 生成等候时间报告
report = await nhs_processor.generate_waiting_time_report(
    provider_code='RGT01',
    specialty_code='120'
)
```

## 🔌 扩展性设计

### 自定义数据源

```python
from business_framework.core.data_processor import DataDiscoveryStrategy

class CustomDiscoveryStrategy(DataDiscoveryStrategy):
    async def discover(self, source: DataSource) -> List[str]:
        # 实现自定义数据发现逻辑
        return discovered_urls
    
    def get_priority(self) -> int:
        return 1

# 注册自定义策略
data_processor.register_discovery_strategy('custom', CustomDiscoveryStrategy())
```

### 自定义通知渠道

```python
from business_framework.core.notification_service import MessageProvider

class CustomMessageProvider(MessageProvider):
    async def send_message(self, request: MessageRequest) -> MessageResult:
        # 实现自定义通知逻辑
        pass
    
    def get_supported_channels(self) -> List[MessageChannel]:
        return [MessageChannel.WEBHOOK]

# 注册自定义提供商
notification_service.register_provider(CustomMessageProvider())
```

### 自定义提醒规则

```python
from business_framework.core.alert_engine import RuleEvaluator

class CustomRuleEvaluator(RuleEvaluator):
    async def evaluate(self, rule: AlertRule, context: AlertContext) -> Optional[AlertResult]:
        # 实现自定义规则评估逻辑
        pass
    
    def supports_rule_type(self, rule_type: AlertType) -> bool:
        return rule_type == AlertType.CUSTOM

# 注册自定义评估器
alert_engine.register_evaluator(AlertType.CUSTOM, CustomRuleEvaluator())
```

## 🚀 部署指南

### Docker部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements_business.txt .
RUN pip install -r requirements_business.txt

COPY . .
RUN playwright install chromium

CMD ["python", "main.py", "--mode", "full", "--env", "prod"]
```

### 生产环境配置

1. **数据库设置**
   - 使用PostgreSQL 14+
   - 配置连接池和备份
   - 启用SSL连接

2. **安全配置**
   - 使用强密码和密钥
   - 配置HTTPS和CORS
   - 启用限流和监控

3. **性能优化**
   - 配置Redis缓存
   - 启用数据库索引
   - 使用CDN加速

4. **监控告警**
   - 集成Sentry错误监控
   - 配置健康检查
   - 设置性能指标

## 📈 商业化特性

### 多租户支持

```python
# 创建租户
tenant = config_manager.create_tenant({
    'tenant_id': 'healthcare_clinic_1',
    'name': 'Healthcare Clinic',
    'branding': {
        'logo_url': 'https://clinic.com/logo.png',
        'primary_color': '#007bff'
    },
    'features': {
        'custom_branding': True,
        'priority_support': True
    }
})
```

### 订阅和计费

```python
# 订阅层级配置
subscription_tiers = {
    'free': {'price': 0, 'limits': {'alerts_per_day': 3}},
    'basic': {'price': 1.99, 'limits': {'alerts_per_day': 10}},
    'premium': {'price': 9.99, 'limits': {'alerts_per_day': 50}}
}
```

### 白标解决方案

- 自定义品牌和域名
- 独立的配置和数据
- 专门的支持和培训

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

## 📄 许可证

此项目使用MIT许可证 - 查看LICENSE文件了解详情。

## 📞 支持

- 📧 Email: support@nhs-alert.com
- 📚 文档: https://docs.nhs-alert.com
- 🐛 Issues: https://github.com/your-repo/issues

---

**NHS Alert System** - 让医疗更智能，让等候更透明 🏥💙 