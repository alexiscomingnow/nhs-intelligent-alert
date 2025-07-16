#!/usr/bin/env python3
"""
最终验证脚本 - 确认语言偏好和日志记录修复
"""

import sqlite3
import sys
import os
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def verify_real_user_language():
    """验证实际用户的语言设置"""
    try:
        print("🔍 验证实际用户语言设置")
        print("=" * 40)
        
        conn = sqlite3.connect('nhs_alerts.db')
        cursor = conn.cursor()
        
        # 检查用户7578790425的设置
        user_id = 'telegram_7578790425'
        chat_id = '7578790425'
        
        # 检查user_preferences中的语言设置
        cursor.execute("""
            SELECT user_id, language, specialty, postcode 
            FROM user_preferences 
            WHERE user_id = ?
        """, (user_id,))
        
        prefs_result = cursor.fetchone()
        
        # 检查telegram_users中的设置
        cursor.execute("""
            SELECT user_id, chat_id, first_name, language_code 
            FROM telegram_users 
            WHERE user_id = ?
        """, (user_id,))
        
        telegram_result = cursor.fetchone()
        
        conn.close()
        
        print(f"👤 用户ID: {user_id}")
        print(f"📱 Chat ID: {chat_id}")
        
        if prefs_result:
            print(f"⚙️ 用户偏好: 语言={prefs_result[1]}, 专科={prefs_result[2]}, 邮编={prefs_result[3]}")
        else:
            print("❌ 未找到用户偏好记录")
            return False
        
        if telegram_result:
            print(f"💬 Telegram用户: 姓名={telegram_result[2]}, 语言代码={telegram_result[3]}")
        else:
            print("⚠️ 未找到Telegram用户记录")
        
        # 验证语言设置
        user_lang = prefs_result[1] if prefs_result[1] else (telegram_result[3] if telegram_result else 'en')
        print(f"🌍 最终检测语言: {user_lang}")
        
        if user_lang == 'zh':
            print("✅ 用户语言设置正确 - 中文")
            return True
        else:
            print(f"❌ 用户语言设置可能有问题 - {user_lang}")
            return False
        
    except Exception as e:
        print(f"❌ 验证用户语言设置失败: {e}")
        return False

def test_telegram_driver_integration():
    """测试TelegramDriver集成"""
    try:
        print("\n🤖 测试TelegramDriver集成")
        print("=" * 40)
        
        # 设置环境变量
        os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token_for_verification'
        
        from telegram_driver import TelegramDriver
        driver = TelegramDriver()
        
        # 测试获取用户信息
        user_info = driver._get_user_info_for_daily_alert('7578790425')
        
        if user_info:
            print(f"✅ 获取用户信息成功")
            print(f"👤 用户姓名: {user_info.get('first_name', '未设置')}")
            print(f"🌍 用户语言: {user_info.get('language', '未设置')}")
            print(f"🏥 监控专科: {user_info.get('specialty', '未设置')}")
            print(f"📍 位置: {user_info.get('postcode', '未设置')}")
            
            # 验证是否为中文
            if user_info.get('language') in ['zh', 'zh-hans', 'zh-cn']:
                print("✅ 用户语言偏好正确应用")
                return True, user_info
            else:
                print(f"❌ 用户语言偏好错误: {user_info.get('language')}")
                return False, user_info
        else:
            print("❌ 获取用户信息失败")
            return False, None
        
    except Exception as e:
        print(f"❌ TelegramDriver集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_structured_alert_chinese():
    """测试结构化推送中文生成"""
    try:
        print("\n📨 测试结构化推送中文生成")
        print("=" * 40)
        
        from structured_daily_alert_generator import StructuredDailyAlertGenerator
        generator = StructuredDailyAlertGenerator('nhs_alerts.db')
        
        # 使用真实用户信息
        test_user_info = {
            'user_id': 'telegram_7578790425',
            'chat_id': '7578790425',
            'username': 'real_user',
            'first_name': '用户',
            'language': 'zh',  # 强制设置为中文
            'postcode': 'SW1A 1AA',
            'specialty': 'cardiology',
            'threshold_weeks': 12,
            'radius_km': 25,
            'status': 'active'
        }
        
        alert_message = generator.generate_structured_daily_alert(test_user_info)
        
        # 检查中文内容
        chinese_indicators = ['早安', '等候状态分析', '趋势变化预测', '个性化建议', '行动计划']
        chinese_count = sum(1 for indicator in chinese_indicators if indicator in alert_message)
        
        print(f"🔍 中文内容检测: {chinese_count}/{len(chinese_indicators)} 个指标匹配")
        
        if chinese_count >= 4:
            print("✅ 结构化推送正确生成中文内容")
            print(f"📝 消息长度: {len(alert_message)} 字符")
            
            # 显示消息开头
            print("\n📄 消息开头:")
            print("-" * 30)
            print(alert_message[:150] + "...")
            print("-" * 30)
            
            return True
        else:
            print("❌ 结构化推送生成的中文内容不完整")
            print(f"📄 实际生成内容前200字符: {alert_message[:200]}")
            return False
        
    except Exception as e:
        print(f"❌ 结构化推送测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_log_test_alert_method():
    """测试_log_test_alert方法"""
    try:
        print("\n📝 测试_log_test_alert方法")
        print("=" * 40)
        
        # 设置环境变量
        os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token_for_verification'
        
        from telegram_driver import TelegramDriver
        driver = TelegramDriver()
        
        # 测试日志记录方法
        driver._log_test_alert('test_chat_123', 'test_user_123', 'success')
        
        # 验证日志是否记录
        conn = sqlite3.connect('nhs_alerts.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT chat_id, user_id, status, timestamp
            FROM test_alert_logs 
            WHERE chat_id = 'test_chat_123'
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        
        log_record = cursor.fetchone()
        
        # 清理测试记录
        cursor.execute("DELETE FROM test_alert_logs WHERE chat_id = 'test_chat_123'")
        conn.commit()
        conn.close()
        
        if log_record:
            print(f"✅ 日志记录方法正常工作")
            print(f"📝 记录内容: {log_record}")
            return True
        else:
            print("❌ 日志记录方法未能正确记录")
            return False
        
    except Exception as e:
        print(f"❌ 日志记录测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主验证流程"""
    print(f"🚀 最终验证开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    results = []
    
    # 1. 验证用户语言设置
    lang_ok = verify_real_user_language()
    results.append(("用户语言设置", lang_ok))
    
    # 2. 测试TelegramDriver集成
    driver_ok, user_info = test_telegram_driver_integration()
    results.append(("TelegramDriver集成", driver_ok))
    
    # 3. 测试结构化推送中文生成
    alert_ok = test_structured_alert_chinese()
    results.append(("结构化推送中文生成", alert_ok))
    
    # 4. 测试日志记录方法
    log_ok = test_log_test_alert_method()
    results.append(("日志记录方法", log_ok))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📋 验证结果汇总:")
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 所有验证通过！修复成功完成。")
        print("\n📝 修复总结:")
        print("✅ 语言偏好问题已解决 - 用户将收到中文推送")
        print("✅ _log_test_alert方法已添加 - 日志错误已解决")
        print("✅ 结构化推送正常工作 - 内容结构清晰")
        print("✅ TelegramDriver正确获取用户信息")
        
        print("\n💡 用户现在可以:")
        print("• 输入命令 '7' 测试每日提醒")
        print("• 收到完全中文的结构化推送内容")
        print("• 享受优先展示核心信息的新体验")
        print("• 不再看到日志错误信息")
    else:
        print("\n❌ 部分验证失败，请检查具体错误信息。")
    
    print(f"\n🏁 验证结束 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main() 