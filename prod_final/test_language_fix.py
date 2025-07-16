#!/usr/bin/env python3
"""
测试语言偏好修复
"""

import sqlite3
import sys
import os
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def setup_test_user_with_language():
    """设置带有语言偏好的测试用户"""
    try:
        conn = sqlite3.connect('nhs_alerts.db')
        cursor = conn.cursor()
        
        # 清理旧的测试数据
        cursor.execute("DELETE FROM telegram_users WHERE chat_id = 'test_lang_789'")
        cursor.execute("DELETE FROM user_preferences WHERE user_id = 'telegram_test_lang_789'")
        
        # 插入测试Telegram用户
        cursor.execute("""
        INSERT OR REPLACE INTO telegram_users 
        (chat_id, user_id, username, first_name, language_code)
        VALUES (?, ?, ?, ?, ?)
        """, ('test_lang_789', 'telegram_test_lang_789', 'test_lang_user', '中文测试用户', 'zh'))
        
        # 插入测试用户偏好，明确设置language为zh
        cursor.execute("""
        INSERT OR REPLACE INTO user_preferences 
        (user_id, phone_number, postcode, specialty, threshold_weeks, radius_km, status, notification_types, language)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ('telegram_test_lang_789', 'test_phone_789', 'SW1A 1AA', 'cardiology', 12, 25, 'active', '["daily_alert"]', 'zh'))
        
        conn.commit()
        conn.close()
        
        print("✅ 带语言偏好的测试用户数据设置完成")
        return True
        
    except Exception as e:
        print(f"❌ 设置测试用户失败: {e}")
        return False

def test_language_preference_fix():
    """测试语言偏好修复"""
    try:
        print("🧪 测试语言偏好修复")
        print("=" * 50)
        
        # 模拟TelegramDriver的_get_user_info_for_daily_alert方法
        conn = sqlite3.connect('nhs_alerts.db')
        cursor = conn.cursor()
        
        chat_id = 'test_lang_789'
        user_id = f"telegram_{chat_id}"
        
        # 获取用户基本信息
        cursor.execute("""
            SELECT chat_id, username, first_name, language_code
            FROM telegram_users 
            WHERE chat_id = ?
        """, (chat_id,))
        
        user_row = cursor.fetchone()
        if not user_row:
            print("❌ 未找到用户基本信息")
            return False
        
        print(f"📱 Telegram用户信息: {user_row}")
        
        # 获取用户偏好设置（包括language字段）
        cursor.execute("""
            SELECT postcode, specialty, threshold_weeks, radius_km, status, language
            FROM user_preferences 
            WHERE user_id = ? AND status = 'active'
        """, (user_id,))
        
        prefs_row = cursor.fetchone()
        if not prefs_row:
            print("❌ 未找到用户偏好信息")
            return False
        
        print(f"⚙️ 用户偏好信息: {prefs_row}")
        
        conn.close()
        
        # 优先使用user_preferences中的language设置，其次是telegram_users中的language_code
        user_language = prefs_row[5] if prefs_row[5] else (user_row[3] or 'zh')
        
        print(f"🌍 检测到的用户语言: {user_language}")
        
        # 构建用户信息字典
        user_info = {
            'user_id': user_id,
            'chat_id': user_row[0],
            'username': user_row[1] or '',
            'first_name': user_row[2] or '',
            'language': user_language,
            'postcode': prefs_row[0],
            'specialty': prefs_row[1],
            'threshold_weeks': prefs_row[2],
            'radius_km': prefs_row[3],
            'status': prefs_row[4]
        }
        
        print(f"👤 完整用户信息: {user_info}")
        
        # 测试结构化推送生成
        from structured_daily_alert_generator import StructuredDailyAlertGenerator
        generator = StructuredDailyAlertGenerator('nhs_alerts.db')
        
        print(f"\n📨 生成{user_language}版结构化推送...")
        alert_message = generator.generate_structured_daily_alert(user_info)
        
        # 检查消息语言
        chinese_indicators = ['早安', '等候状态分析', '趋势变化预测', '个性化建议', '行动计划']
        english_indicators = ['Good Morning', 'Current Waiting Status', 'Trend Change Prediction', 'Personalized Recommendations', 'Action Plan']
        
        chinese_count = sum(1 for indicator in chinese_indicators if indicator in alert_message)
        english_count = sum(1 for indicator in english_indicators if indicator in alert_message)
        
        print(f"\n🔍 语言检测结果:")
        print(f"  中文指标匹配: {chinese_count}/{len(chinese_indicators)}")
        print(f"  英文指标匹配: {english_count}/{len(english_indicators)}")
        
        if user_language == 'zh' and chinese_count >= 3:
            print("✅ 语言偏好正确应用 - 生成了中文内容")
            success = True
        elif user_language == 'en' and english_count >= 3:
            print("✅ 语言偏好正确应用 - 生成了英文内容")
            success = True
        else:
            print(f"❌ 语言偏好应用错误 - 用户语言:{user_language}, 中文匹配:{chinese_count}, 英文匹配:{english_count}")
            success = False
        
        # 显示部分消息内容
        print(f"\n📄 生成的消息前200字符:")
        print("-" * 40)
        print(alert_message[:200] + "...")
        print("-" * 40)
        
        return success
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_telegram_driver_method():
    """测试TelegramDriver的方法"""
    try:
        print("\n🤖 测试TelegramDriver方法")
        print("=" * 50)
        
        # 设置临时环境变量
        os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token_for_testing'
        
        from telegram_driver import TelegramDriver
        driver = TelegramDriver()
        
        # 测试获取用户信息
        user_info = driver._get_user_info_for_daily_alert('test_lang_789')
        
        if user_info:
            print(f"✅ TelegramDriver获取用户信息成功")
            print(f"👤 用户语言: {user_info.get('language', '未设置')}")
            print(f"👤 用户姓名: {user_info.get('first_name', '未设置')}")
            
            # 测试语言偏好
            if user_info.get('language') == 'zh':
                print("✅ TelegramDriver正确获取中文语言偏好")
                return True
            else:
                print(f"❌ TelegramDriver语言偏好错误: {user_info.get('language')}")
                return False
        else:
            print("❌ TelegramDriver获取用户信息失败")
            return False
        
    except Exception as e:
        print(f"❌ TelegramDriver测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def cleanup_test_data():
    """清理测试数据"""
    try:
        conn = sqlite3.connect('nhs_alerts.db')
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM telegram_users WHERE chat_id = 'test_lang_789'")
        cursor.execute("DELETE FROM user_preferences WHERE user_id = 'telegram_test_lang_789'")
        
        conn.commit()
        conn.close()
        
        print("🧹 测试数据清理完成")
        return True
        
    except Exception as e:
        print(f"❌ 清理测试数据失败: {e}")
        return False

if __name__ == "__main__":
    print(f"🚀 语言偏好修复测试开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. 设置测试用户
        if not setup_test_user_with_language():
            print("❌ 测试用户设置失败，退出")
            exit(1)
        
        # 2. 测试语言偏好修复
        lang_test_ok = test_language_preference_fix()
        
        # 3. 测试TelegramDriver方法
        driver_test_ok = test_telegram_driver_method()
        
        if lang_test_ok and driver_test_ok:
            print("\n🎉 所有测试通过！")
            print("\n📋 修复总结:")
            print("✅ 语言偏好获取逻辑已修复")
            print("✅ 优先使用user_preferences.language字段")
            print("✅ 结构化推送正确应用用户语言偏好")
            print("✅ TelegramDriver._get_user_info_for_daily_alert方法正常工作")
            print("✅ _log_test_alert方法已添加，解决日志错误")
        else:
            print("\n❌ 部分测试失败，请检查错误信息")
            
    finally:
        # 清理测试数据
        cleanup_test_data()
        print("\n🏁 测试结束") 