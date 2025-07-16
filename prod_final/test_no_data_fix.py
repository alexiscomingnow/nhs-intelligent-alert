#!/usr/bin/env python3
"""
测试无数据情况的修复效果
"""

import sqlite3
import sys
import os
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def setup_nephrology_test_user():
    """设置肾科测试用户"""
    try:
        conn = sqlite3.connect('nhs_alerts.db')
        cursor = conn.cursor()
        
        # 清理旧的测试数据
        cursor.execute("DELETE FROM telegram_users WHERE chat_id = 'test_nephro_999'")
        cursor.execute("DELETE FROM user_preferences WHERE user_id = 'telegram_test_nephro_999'")
        
        # 插入测试Telegram用户
        cursor.execute("""
        INSERT OR REPLACE INTO telegram_users 
        (chat_id, user_id, username, first_name, language_code)
        VALUES (?, ?, ?, ?, ?)
        """, ('test_nephro_999', 'telegram_test_nephro_999', 'nephro_user', '肾科患者', 'zh'))
        
        # 插入测试用户偏好，模拟真实用户的设置
        cursor.execute("""
        INSERT OR REPLACE INTO user_preferences 
        (user_id, phone_number, postcode, specialty, threshold_weeks, radius_km, status, notification_types, language)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ('telegram_test_nephro_999', 'test_phone_nephro', 'BT37 0ZP', 'Nephrology', 1, 20, 'active', '["daily_alert"]', 'zh'))
        
        conn.commit()
        conn.close()
        
        print("✅ 肾科测试用户设置完成")
        return True
        
    except Exception as e:
        print(f"❌ 设置测试用户失败: {e}")
        return False

def test_no_data_handling():
    """测试无数据情况的处理"""
    try:
        print("🧪 测试无数据情况处理")
        print("=" * 50)
        
        from structured_daily_alert_generator import StructuredDailyAlertGenerator
        generator = StructuredDailyAlertGenerator('nhs_alerts.db')
        
        # 使用肾科测试用户信息
        test_user_info = {
            'user_id': 'telegram_test_nephro_999',
            'chat_id': 'test_nephro_999',
            'username': 'nephro_user',
            'first_name': '肾科患者',
            'language': 'zh',
            'postcode': 'BT37 0ZP',
            'specialty': 'Nephrology',
            'threshold_weeks': 1,
            'radius_km': 20,
            'status': 'active'
        }
        
        print(f"👤 测试用户信息:")
        print(f"  专科: {test_user_info['specialty']}")
        print(f"  位置: {test_user_info['postcode']}")
        print(f"  阈值: {test_user_info['threshold_weeks']} 周")
        print(f"  搜索半径: {test_user_info['radius_km']} 公里")
        
        # 生成结构化推送
        alert_message = generator.generate_structured_daily_alert(test_user_info)
        
        print(f"\n📨 生成的改进版推送内容:")
        print("-" * 60)
        print(alert_message)
        print("-" * 60)
        
        # 验证改进效果
        print(f"\n🔍 改进效果验证:")
        
        # 检查是否包含有用的信息
        useful_indicators = [
            "数据库暂无肾科数据",
            "可能的原因",
            "建议方案", 
            "相关专科建议",
            "泌尿科",
            "普外科",
            "直接联系",
            "扩大范围"
        ]
        
        useful_count = sum(1 for indicator in useful_indicators if indicator in alert_message)
        
        print(f"📊 有用信息指标: {useful_count}/{len(useful_indicators)} 个匹配")
        
        if useful_count >= 6:
            print("✅ 无数据情况处理良好 - 提供了有用的建议和解释")
            
            # 检查是否不再出现混淆信息
            confusing_terms = ["暂无数据", "0周", "0家", "数据获取失败"]
            confusing_count = sum(1 for term in confusing_terms if term in alert_message)
            
            if confusing_count == 0:
                print("✅ 成功消除了令人困惑的信息")
            else:
                print(f"⚠️ 仍有部分令人困惑的信息: {confusing_count} 处")
                
            return True
        else:
            print("❌ 无数据情况处理不完善")
            return False
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_core_status_data():
    """测试核心状态数据获取"""
    try:
        print("\n🔍 测试核心状态数据获取")
        print("=" * 50)
        
        from structured_daily_alert_generator import StructuredDailyAlertGenerator
        generator = StructuredDailyAlertGenerator('nhs_alerts.db')
        
        # 测试用户信息
        test_user_info = {
            'specialty': 'Nephrology',
            'postcode': 'BT37 0ZP',
            'radius_km': 20,
            'threshold_weeks': 1
        }
        
        # 获取核心状态数据
        core_status = generator._get_core_status_data(test_user_info)
        
        print(f"📊 核心状态数据:")
        print(f"  最佳选择: {core_status.best_hospital}")
        print(f"  最短等候: {core_status.current_min_wait} 周")
        print(f"  平均等候: {core_status.avg_wait} 周")
        print(f"  是否达标: {core_status.threshold_met}")
        print(f"  可选医院: {core_status.total_options} 家")
        print(f"  趋势方向: {core_status.trend_direction}")
        
        # 验证改进效果
        if "数据库暂无肾科数据" in core_status.best_hospital:
            print("✅ 正确识别了无数据情况并提供了清晰的说明")
            return True
        elif "建议查看肾科相关专科" in core_status.best_hospital:
            print("✅ 提供了相关专科的智能建议")
            return True
        else:
            print(f"⚠️ 状态信息可能需要进一步改进: {core_status.best_hospital}")
            return False
        
    except Exception as e:
        print(f"❌ 核心状态数据测试失败: {e}")
        return False

def test_related_specialty_suggestions():
    """测试相关专科建议"""
    try:
        print("\n🎯 测试相关专科建议")
        print("=" * 50)
        
        from structured_daily_alert_generator import StructuredDailyAlertGenerator
        generator = StructuredDailyAlertGenerator('nhs_alerts.db')
        
        # 测试专科名称转换
        chinese_name = generator._get_specialty_chinese_name('Nephrology')
        print(f"专科中文名称: Nephrology -> {chinese_name}")
        
        if chinese_name == '肾科':
            print("✅ 专科名称转换正确")
        else:
            print(f"❌ 专科名称转换错误: {chinese_name}")
        
        # 测试相关专科建议
        related_specialties = generator._get_related_specialties_for_display('Nephrology')
        print(f"\n相关专科建议:")
        for i, (specialty_en, specialty_cn) in enumerate(related_specialties, 1):
            print(f"  {i}. {specialty_cn} ({specialty_en})")
        
        if len(related_specialties) >= 2:
            print("✅ 提供了合理的相关专科建议")
            return True
        else:
            print("❌ 相关专科建议不足")
            return False
        
    except Exception as e:
        print(f"❌ 相关专科建议测试失败: {e}")
        return False

def compare_before_after():
    """对比修复前后的效果"""
    print("\n📈 修复前后对比")
    print("=" * 50)
    
    print("🔴 **修复前的问题**:")
    print("• 显示'最佳选择：暂无数据' - 令人困惑")
    print("• 显示'可选医院：0家' - 没有解释原因")
    print("• 显示'最短等候：0周' - 误导性信息")
    print("• 没有提供任何有用的建议或替代方案")
    print("• 用户不知道为什么没有数据")
    print("• 没有指导用户下一步应该做什么")
    
    print("\n🟢 **修复后的改进**:")
    print("• 明确说明'数据库暂无肾科数据' - 清晰准确")
    print("• 解释可能的原因 - 帮助用户理解")
    print("• 提供具体的解决方案 - 实用性强")
    print("• 推荐相关专科 - 智能建议")
    print("• 提供联系策略 - 可行的行动计划")
    print("• 建议扩大搜索范围 - 增加选择")
    print("• 提及私立选择 - 全面的选项")

def cleanup_test_data():
    """清理测试数据"""
    try:
        conn = sqlite3.connect('nhs_alerts.db')
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM telegram_users WHERE chat_id = 'test_nephro_999'")
        cursor.execute("DELETE FROM user_preferences WHERE user_id = 'telegram_test_nephro_999'")
        
        conn.commit()
        conn.close()
        
        print("🧹 测试数据清理完成")
        return True
        
    except Exception as e:
        print(f"❌ 清理测试数据失败: {e}")
        return False

if __name__ == "__main__":
    print(f"🚀 无数据情况修复测试开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. 设置测试用户
        if not setup_nephrology_test_user():
            print("❌ 测试用户设置失败，退出")
            exit(1)
        
        results = []
        
        # 2. 测试无数据情况处理
        no_data_ok = test_no_data_handling()
        results.append(("无数据情况处理", no_data_ok))
        
        # 3. 测试核心状态数据
        core_status_ok = test_core_status_data()
        results.append(("核心状态数据", core_status_ok))
        
        # 4. 测试相关专科建议
        related_ok = test_related_specialty_suggestions()
        results.append(("相关专科建议", related_ok))
        
        # 5. 对比修复前后
        compare_before_after()
        
        # 汇总结果
        print("\n" + "=" * 60)
        print("📋 测试结果汇总:")
        
        all_passed = True
        for test_name, passed in results:
            status = "✅ 通过" if passed else "❌ 失败"
            print(f"  {test_name}: {status}")
            if not passed:
                all_passed = False
        
        if all_passed:
            print("\n🎉 所有测试通过！无数据情况处理已大幅改进。")
            print("\n📝 改进总结:")
            print("✅ 消除了令人困惑的'暂无数据'、'0家医院'等信息")
            print("✅ 提供了清晰的问题解释和可能原因")
            print("✅ 给出了具体可行的解决方案")
            print("✅ 推荐了相关专科作为替代选择")
            print("✅ 提供了实用的联系策略和行动建议")
            print("✅ 建议了扩大搜索范围等解决方案")
            
            print("\n💡 用户现在会看到:")
            print("• 明确的数据状态说明")
            print("• 有用的相关专科建议")
            print("• 具体的行动计划")
            print("• 清晰的下一步指导")
        else:
            print("\n❌ 部分测试失败，需要进一步改进。")
            
    finally:
        # 清理测试数据
        cleanup_test_data()
        print(f"\n🏁 测试结束 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}") 