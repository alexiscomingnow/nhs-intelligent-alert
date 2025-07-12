# NHS Alert System - Production Deployment Guide

本指南提供完整的生产环境部署说明，包括Docker容器化、数据库配置、安全设置和扩展建议。

## 🚀 部署选项

### 1. Docker容器化部署 (推荐)
### 2. 传统服务器部署
### 3. 云平台部署 (AWS/Azure/GCP)
### 4. Kubernetes集群部署

---

## 📋 系统要求

### 最小硬件要求
- **CPU**: 2核心 (4核心推荐)
- **内存**: 4GB RAM (8GB推荐)
- **存储**: 20GB SSD (100GB推荐)
- **网络**: 稳定的互联网连接

### 软件要求
- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / Windows Server 2019+
- **Python**: 3.9+
- **PostgreSQL**: 13+
- **Redis**: 6+
- **Docker**: 20.10+ (容器化部署)
- **Docker Compose**: 1.29+ (容器化部署)

---

## 🐳 Docker容器化部署

### 1. 创建Docker配置

首先创建必要的Docker文件：

```dockerfile
# Dockerfile
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装Playwright浏览器
RUN pip install playwright
RUN playwright install chromium
RUN playwright install-deps

# 复制requirements文件
COPY requirements_business.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements_business.txt

# 复制应用代码
COPY . .

# 创建非root用户
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "main.py", "--mode", "full", "--env", "prod", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Docker Compose配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  # 主应用
  nhs-alert-app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/nhs_alerts
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=prod
    depends_on:
      - postgres
      - redis
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    restart: unless-stopped
    networks:
      - nhs-network

  # PostgreSQL数据库
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=nhs_alerts
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    restart: unless-stopped
    networks:
      - nhs-network

  # Redis缓存
  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    restart: unless-stopped
    networks:
      - nhs-network

  # Nginx反向代理
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl/certs
    depends_on:
      - nhs-alert-app
    restart: unless-stopped
    networks:
      - nhs-network

  # 监控组件
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
    restart: unless-stopped
    networks:
      - nhs-network

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    restart: unless-stopped
    networks:
      - nhs-network

volumes:
  postgres_data:
  redis_data:
  grafana_data:
  prometheus_data:

networks:
  nhs-network:
    driver: bridge
```

### 3. 环境变量配置

```bash
# .env
# 数据库配置
POSTGRES_PASSWORD=your_secure_postgres_password
REDIS_PASSWORD=your_secure_redis_password

# 应用配置
SECRET_KEY=your_super_secret_key_here
JWT_SECRET_KEY=your_jwt_secret_key_here

# WhatsApp配置
WHATSAPP_ACCESS_TOKEN=your_whatsapp_access_token
WHATSAPP_BUSINESS_ACCOUNT_ID=your_business_account_id
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_VERIFY_TOKEN=your_webhook_verify_token

# SMS配置 (Twilio)
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number

# Email配置
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# 监控配置
GRAFANA_PASSWORD=your_grafana_password
SENTRY_DSN=your_sentry_dsn

# SSL证书配置
SSL_CERT_PATH=/etc/ssl/certs/cert.pem
SSL_KEY_PATH=/etc/ssl/certs/key.pem
```

### 4. Nginx配置

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream nhs_app {
        server nhs-alert-app:8000;
    }

    # HTTPS重定向
    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    # 主服务器配置
    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        # SSL配置
        ssl_certificate /etc/ssl/certs/cert.pem;
        ssl_certificate_key /etc/ssl/certs/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        # 安全头
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

        # 请求大小限制
        client_max_body_size 10M;

        # 代理到应用
        location / {
            proxy_pass http://nhs_app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket支持
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        # 静态文件缓存
        location /static/ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # API速率限制
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://nhs_app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }

    # 速率限制配置
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
}
```

### 5. 部署步骤

```bash
# 1. 克隆项目
git clone <repository-url>
cd nhs-alert-system/prod_final

# 2. 配置环境变量
cp .env.example .env
# 编辑.env文件，设置所有必要的环境变量

# 3. 创建SSL证书目录
mkdir -p ssl

# 4. 获取SSL证书 (Let's Encrypt示例)
certbot certonly --standalone -d your-domain.com
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ssl/cert.pem
cp /etc/letsencrypt/live/your-domain.com/privkey.pem ssl/key.pem

# 5. 构建和启动服务
docker-compose up -d

# 6. 初始化数据库
docker-compose exec nhs-alert-app python -c "
from business_framework import DatabaseManager
import asyncio
async def init_db():
    db = DatabaseManager()
    await db.initialize_schema()
asyncio.run(init_db())
"

# 7. 验证部署
curl -k https://your-domain.com/health
```

---

## 🖥️ 传统服务器部署

### 1. 系统准备

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.11 python3.11-venv postgresql-13 redis-server nginx

# CentOS/RHEL
sudo yum update
sudo yum install -y python311 postgresql13-server redis nginx
```

### 2. 数据库设置

```bash
# PostgreSQL配置
sudo -u postgres createuser --interactive
sudo -u postgres createdb nhs_alerts
sudo -u postgres psql -c "ALTER USER your_user PASSWORD 'your_password';"

# Redis配置
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### 3. 应用部署

```bash
# 创建应用目录
sudo mkdir -p /opt/nhs-alert-system
sudo chown $USER:$USER /opt/nhs-alert-system
cd /opt/nhs-alert-system

# 克隆代码
git clone <repository-url> .

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements_business.txt
playwright install chromium

# 配置环境
cp config.env.example config.env
# 编辑config.env

# 初始化数据库
python main.py --mode init-db
```

### 4. 系统服务配置

```ini
# /etc/systemd/system/nhs-alert.service
[Unit]
Description=NHS Alert System
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/nhs-alert-system
Environment=PATH=/opt/nhs-alert-system/venv/bin
ExecStart=/opt/nhs-alert-system/venv/bin/python main.py --mode full --env prod
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 启用和启动服务
sudo systemctl daemon-reload
sudo systemctl enable nhs-alert.service
sudo systemctl start nhs-alert.service
```

---

## ☁️ 云平台部署

### AWS部署

#### ECS + Fargate方式

```yaml
# task-definition.json
{
  "family": "nhs-alert-system",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "nhs-alert-app",
      "image": "your-account.dkr.ecr.region.amazonaws.com/nhs-alert:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "ENVIRONMENT", "value": "prod"},
        {"name": "DATABASE_URL", "valueFrom": "arn:aws:ssm:region:account:parameter/nhs-alert/database-url"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/nhs-alert-system",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### Terraform配置示例

```hcl
# main.tf
resource "aws_ecs_cluster" "nhs_alert" {
  name = "nhs-alert-cluster"
}

resource "aws_ecs_service" "nhs_alert_service" {
  name            = "nhs-alert-service"
  cluster         = aws_ecs_cluster.nhs_alert.id
  task_definition = aws_ecs_task_definition.nhs_alert.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = var.private_subnet_ids
    security_groups = [aws_security_group.nhs_alert.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.nhs_alert.arn
    container_name   = "nhs-alert-app"
    container_port   = 8000
  }
}

resource "aws_rds_instance" "postgres" {
  identifier     = "nhs-alert-db"
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.t3.medium"
  allocated_storage = 100
  
  db_name  = "nhs_alerts"
  username = "postgres"
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.default.name
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  skip_final_snapshot = false
  final_snapshot_identifier = "nhs-alert-final-snapshot"
}
```

### Azure部署

#### Container Apps方式

```yaml
# azure-container-app.yaml
apiVersion: 2023-05-01
type: Microsoft.App/containerApps
properties:
  managedEnvironmentId: /subscriptions/{subscription}/resourceGroups/{rg}/providers/Microsoft.App/managedEnvironments/{environment}
  configuration:
    ingress:
      external: true
      targetPort: 8000
    secrets:
      - name: database-url
        value: "postgresql://..."
  template:
    containers:
      - image: your-registry.azurecr.io/nhs-alert:latest
        name: nhs-alert-app
        env:
          - name: DATABASE_URL
            secretRef: database-url
        resources:
          cpu: 1
          memory: 2Gi
    scale:
      minReplicas: 1
      maxReplicas: 10
```

### Google Cloud Platform部署

#### Cloud Run方式

```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/nhs-alert:$COMMIT_SHA', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/nhs-alert:$COMMIT_SHA']
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'nhs-alert-service'
      - '--image'
      - 'gcr.io/$PROJECT_ID/nhs-alert:$COMMIT_SHA'
      - '--region'
      - 'us-central1'
      - '--platform'
      - 'managed'
      - '--memory'
      - '2Gi'
      - '--cpu'
      - '1'
      - '--min-instances'
      - '1'
      - '--max-instances'
      - '10'
```

---

## ⚙️ Kubernetes部署

### 1. Kubernetes清单

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nhs-alert-app
  labels:
    app: nhs-alert
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nhs-alert
  template:
    metadata:
      labels:
        app: nhs-alert
    spec:
      containers:
      - name: nhs-alert-app
        image: nhs-alert:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: nhs-alert-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: nhs-alert-secrets
              key: redis-url
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: nhs-alert-service
spec:
  selector:
    app: nhs-alert
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: ClusterIP

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: nhs-alert-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - your-domain.com
    secretName: nhs-alert-tls
  rules:
  - host: your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: nhs-alert-service
            port:
              number: 80
```

### 2. Helm Chart

```yaml
# Chart.yaml
apiVersion: v2
name: nhs-alert-system
description: NHS Alert System Helm Chart
version: 1.0.0
appVersion: "1.0.0"

# values.yaml
replicaCount: 3

image:
  repository: nhs-alert
  pullPolicy: IfNotPresent
  tag: "latest"

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: your-domain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: nhs-alert-tls
      hosts:
        - your-domain.com

resources:
  limits:
    cpu: 1000m
    memory: 2Gi
  requests:
    cpu: 500m
    memory: 1Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80
  targetMemoryUtilizationPercentage: 80
```

---

## 🔒 安全配置

### 1. 网络安全

```bash
# 防火墙配置
sudo ufw enable
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 5432/tcp   # PostgreSQL (内部访问)
sudo ufw deny 6379/tcp   # Redis (内部访问)
```

### 2. SSL/TLS配置

```bash
# Let's Encrypt自动化
#!/bin/bash
# ssl-renew.sh
certbot renew --quiet
docker-compose restart nginx
```

```cron
# 自动续期 (crontab -e)
0 3 1 * * /path/to/ssl-renew.sh
```

### 3. 应用安全

```python
# 安全配置示例
SECURITY_CONFIG = {
    "jwt_expiry_hours": 24,
    "password_min_length": 8,
    "rate_limiting": {
        "login_attempts": 5,
        "api_calls_per_minute": 60
    },
    "encryption": {
        "algorithm": "AES-256-GCM",
        "key_rotation_days": 90
    }
}
```

---

## 📊 监控和日志

### 1. 监控配置

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'nhs-alert-app'
    static_configs:
      - targets: ['nhs-alert-app:8000']
    metrics_path: '/metrics'
```

### 2. 日志聚合

```yaml
# filebeat.yml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /app/logs/*.log
  fields:
    service: nhs-alert-system
  fields_under_root: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
```

### 3. 告警规则

```yaml
# alertmanager.yml
groups:
- name: nhs-alert-system
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
    for: 5m
    annotations:
      summary: "High error rate detected"
  
  - alert: DatabaseConnectionFailed
    expr: up{job="postgres"} == 0
    for: 1m
    annotations:
      summary: "Database connection failed"
```

---

## 🚀 性能优化

### 1. 数据库优化

```sql
-- PostgreSQL优化
-- postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 64MB
maintenance_work_mem = 256MB
max_connections = 100

-- 索引优化
CREATE INDEX CONCURRENTLY idx_users_phone ON users(phone_number);
CREATE INDEX CONCURRENTLY idx_alerts_created ON alerts(created_at);
CREATE INDEX CONCURRENTLY idx_messages_status ON messages(status, created_at);
```

### 2. 应用缓存

```python
# Redis缓存配置
CACHE_CONFIG = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://redis:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "TIMEOUT": 300,
    }
}
```

### 3. CDN配置

```nginx
# Cloudflare/CDN配置
location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
    add_header Vary Accept-Encoding;
}
```

---

## 📈 扩展策略

### 1. 水平扩展

```yaml
# 负载均衡配置
upstream nhs_app_cluster {
    least_conn;
    server app1.example.com:8000;
    server app2.example.com:8000;
    server app3.example.com:8000;
}
```

### 2. 数据库分片

```python
# 数据库分片策略
DATABASE_ROUTING = {
    'users': 'users_db',
    'alerts': 'alerts_db',
    'messages': 'messages_db'
}
```

### 3. 微服务架构

```yaml
# 微服务分解
services:
  - user-service (用户管理)
  - alert-service (提醒引擎)
  - notification-service (通知服务)
  - analytics-service (分析服务)
```

---

## 🛠️ 故障排除

### 常见问题

1. **WhatsApp API连接失败**
   ```bash
   # 检查网络连接
   curl -I https://graph.facebook.com/v18.0/me
   
   # 验证token
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        https://graph.facebook.com/v18.0/YOUR_BUSINESS_ACCOUNT_ID
   ```

2. **数据库连接超时**
   ```bash
   # 检查连接池配置
   # 增加连接超时时间
   DATABASE_POOL_SIZE = 20
   DATABASE_POOL_TIMEOUT = 30
   ```

3. **内存使用过高**
   ```bash
   # 监控内存使用
   docker stats
   
   # 调整内存限制
   deploy:
     resources:
       limits:
         memory: 1G
   ```

### 健康检查

```bash
#!/bin/bash
# health-check.sh

# 检查应用状态
curl -f http://localhost:8000/health || exit 1

# 检查数据库连接
psql $DATABASE_URL -c "SELECT 1;" || exit 1

# 检查Redis连接
redis-cli -u $REDIS_URL ping || exit 1

echo "All services healthy"
```

---

## 📞 支持和维护

### 日常维护任务

```bash
# 每日备份
#!/bin/bash
# daily-backup.sh
DATE=$(date +%Y%m%d)
pg_dump $DATABASE_URL > backup_$DATE.sql
aws s3 cp backup_$DATE.sql s3://your-backup-bucket/

# 清理旧日志
find /app/logs -name "*.log" -mtime +30 -delete

# 更新系统
apt update && apt upgrade -y
docker system prune -f
```

### 监控仪表板

访问以下URL查看系统状态：
- **应用状态**: https://your-domain.com/admin/monitoring
- **Grafana仪表板**: https://your-domain.com:3000
- **API文档**: https://your-domain.com/docs

### 联系支持

如需技术支持，请提供以下信息：
- 部署环境 (Docker/K8s/Cloud)
- 错误日志
- 系统配置
- 重现步骤

---

## 📝 更新日志

### v1.0.0 (2024-03-15)
- 初始生产版本
- Docker容器化支持
- 完整的监控和日志系统
- 多云平台部署支持

---

*本部署指南持续更新，请定期检查最新版本。* 