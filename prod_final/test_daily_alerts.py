#!/usr/bin/env python3
"""
测试每日提醒系统
"""

import asyncio
import sys
import os

# 添加路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_daily_alerts():
    """测试每日提醒生成"""
    try:
        print("🧪 开始测试每日提醒系统...")
        
        from daily_comprehensive_alert_service import DailyComprehensiveAlertService
        
        service = DailyComprehensiveAlertService()
        
        print("📊 生成每日提醒...")
        alerts = await service.generate_daily_alerts_for_all_users()
        
        print(f"✅ 测试完成！生成了 {len(alerts)} 个每日提醒")
        
        return alerts
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    asyncio.run(test_daily_alerts()) 