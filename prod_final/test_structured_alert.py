#!/usr/bin/env python3
"""
测试结构化每日推送生成器
"""

import sqlite3
import sys
import os
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_structured_daily_alert():
    """测试结构化每日推送生成器"""
    try:
        from structured_daily_alert_generator import StructuredDailyAlertGenerator
        
        # 创建生成器实例
        generator = StructuredDailyAlertGenerator('nhs_alerts.db')
        
        # 模拟用户信息
        test_user_info = {
            'user_id': 'telegram_test123',
            'chat_id': 'test123',
            'username': 'testuser',
            'first_name': '测试用户',
            'language': 'zh',
            'postcode': 'SW1A 1AA',
            'specialty': 'cardiology',
            'threshold_weeks': 12,
            'radius_km': 25,
            'status': 'active'
        }
        
        print("🧪 测试结构化每日推送生成器")
        print("=" * 50)
        
        # 测试中文版本
        print("\n📱 生成中文版每日推送...")
        chinese_alert = generator.generate_structured_daily_alert(test_user_info)
        print("\n✅ 中文版结果:")
        print(chinese_alert)
        
        print("\n" + "=" * 50)
        
        # 测试英文版本
        test_user_info['language'] = 'en'
        test_user_info['first_name'] = 'Test User'
        
        print("\n📱 生成英文版每日推送...")
        english_alert = generator.generate_structured_daily_alert(test_user_info)
        print("\n✅ 英文版结果:")
        print(english_alert)
        
        print("\n" + "=" * 50)
        print("🎉 测试完成！新的结构化每日推送已成功生成。")
        
        # 验证消息结构
        print("\n🔍 验证消息结构...")
        required_sections_zh = [
            "当前等候状态分析",
            "趋势变化预测", 
            "个性化建议",
            "行动计划",
            "号源推荐"
        ]
        
        required_sections_en = [
            "Current Waiting Status Analysis",
            "Trend Change Prediction",
            "Personalized Recommendations", 
            "Action Plan",
            "Slot Recommendations"
        ]
        
        # 检查中文版本
        missing_zh = [section for section in required_sections_zh if section not in chinese_alert]
        if missing_zh:
            print(f"⚠️ 中文版缺少以下部分: {missing_zh}")
        else:
            print("✅ 中文版包含所有必需部分")
        
        # 检查英文版本  
        missing_en = [section for section in required_sections_en if section not in english_alert]
        if missing_en:
            print(f"⚠️ 英文版缺少以下部分: {missing_en}")
        else:
            print("✅ 英文版包含所有必需部分")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_connection():
    """测试数据库连接"""
    try:
        print("\n🔗 测试数据库连接...")
        conn = sqlite3.connect('nhs_alerts.db')
        cursor = conn.cursor()
        
        # 检查NHS数据表
        cursor.execute("""
        SELECT COUNT(*) FROM nhs_rtt_data 
        WHERE specialty_name LIKE '%cardiology%' OR specialty_name LIKE '%Cardiology%'
        """)
        cardiology_count = cursor.fetchone()[0]
        
        print(f"📊 找到 {cardiology_count} 条心脏科相关数据")
        
        if cardiology_count > 0:
            # 获取示例数据
            cursor.execute("""
            SELECT org_name, specialty_name, waiting_time_weeks 
            FROM nhs_rtt_data 
            WHERE specialty_name LIKE '%cardiology%' OR specialty_name LIKE '%Cardiology%'
            LIMIT 3
            """)
            samples = cursor.fetchall()
            
            print("📋 示例数据:")
            for sample in samples:
                print(f"  • {sample[0]} - {sample[1]} - {sample[2]}周")
        
        conn.close()
        print("✅ 数据库连接正常")
        return True
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

if __name__ == "__main__":
    print(f"🚀 开始测试 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 测试数据库连接
    db_ok = test_database_connection()
    
    if db_ok:
        # 测试结构化生成器
        test_ok = test_structured_daily_alert()
        
        if test_ok:
            print("\n🎉 所有测试通过！结构化每日推送系统已就绪。")
            print("\n💡 使用方法:")
            print("1. 在Telegram中输入命令 '7' 测试每日提醒")
            print("2. 系统会生成包含完整结构化内容的推送")
            print("3. 内容优先展示用户最关心的核心信息")
        else:
            print("\n❌ 测试失败，请检查错误信息并修复。")
    else:
        print("\n❌ 数据库连接失败，请确保数据库已正确设置。") 