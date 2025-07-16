#!/usr/bin/env python3
"""
测试位置调整和日期修复
验证：
1. 实时号源推荐模块位置调整到当前等候状态分析之下
2. 实时号源推荐的时间是未来日期而非历史日期
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
import re

def test_position_and_date_fixes():
    """测试位置和日期修复"""
    print("🧪 测试位置调整和日期修复")
    print("=" * 60)
    
    try:
        from structured_daily_alert_generator import StructuredDailyAlertGenerator
        generator = StructuredDailyAlertGenerator('nhs_alerts.db')
        
        # 测试用户信息 - 使用有数据的专科确保号源推荐出现
        user_info = {
            'user_id': 'test_user',
            'first_name': 'TestUser',
            'language': 'zh',
            'postcode': 'SW1A 1AA',
            'specialty': 'Cardiology',  # 使用有数据的专科
            'threshold_weeks': 15,  # 设置较高阈值确保有选择
            'radius_km': 30
        }
        
        print(f"🔧 测试配置:")
        print(f"   专科: {user_info['specialty']}")
        print(f"   位置: {user_info['postcode']}")
        print(f"   阈值: {user_info['threshold_weeks']} 周")
        
        # 生成完整消息
        alert_message = generator.generate_structured_daily_alert(user_info)
        
        print(f"\n📊 消息长度: {len(alert_message)} 字符")
        
        # 测试1: 检查位置调整
        print(f"\n🔍 测试1: 号源推荐位置检查")
        print("-" * 40)
        
        # 查找关键模块的位置
        status_analysis_pos = alert_message.find("## 📊 **当前等候状态分析**")
        slot_recommendations_pos = alert_message.find("🏥 **实时号源推荐**")
        trend_prediction_pos = alert_message.find("## 📈 **趋势变化预测**")
        
        print(f"📊 当前等候状态分析位置: {status_analysis_pos}")
        print(f"🏥 实时号源推荐位置: {slot_recommendations_pos}")
        print(f"📈 趋势变化预测位置: {trend_prediction_pos}")
        
        position_test_passed = False
        if status_analysis_pos != -1 and slot_recommendations_pos != -1 and trend_prediction_pos != -1:
            if status_analysis_pos < slot_recommendations_pos < trend_prediction_pos:
                print("✅ 位置测试通过: 号源推荐正确位于当前状态分析之后、趋势预测之前")
                position_test_passed = True
            else:
                print("❌ 位置测试失败: 模块顺序不正确")
                print(f"   期望顺序: 状态分析 < 号源推荐 < 趋势预测")
                print(f"   实际顺序: {status_analysis_pos} < {slot_recommendations_pos} < {trend_prediction_pos}")
        else:
            print("❌ 位置测试失败: 找不到一个或多个关键模块")
        
        # 测试2: 检查日期修复
        print(f"\n🔍 测试2: 日期修复检查")
        print("-" * 40)
        
        # 获取可用时段数据
        available_slots = generator._get_available_appointment_slots(user_info)
        
        today = datetime.now()
        date_test_passed = True
        future_dates = []
        
        if available_slots:
            print(f"📅 找到 {len(available_slots)} 个可用时段:")
            for i, slot in enumerate(available_slots, 1):
                slot_date_str = slot['available_date']
                try:
                    slot_date = datetime.strptime(slot_date_str, '%Y-%m-%d')
                    days_from_now = (slot_date - today).days
                    future_dates.append(days_from_now)
                    
                    print(f"   {i}. {slot['hospital_name']}")
                    print(f"      📅 日期: {slot_date_str} ({days_from_now:+d} 天)")
                    print(f"      📞 电话: {slot['phone_number']}")
                    
                    if days_from_now <= 0:
                        print(f"      ❌ 这是过去或今天的日期!")
                        date_test_passed = False
                    else:
                        print(f"      ✅ 这是未来日期")
                        
                except Exception as e:
                    print(f"      ❌ 日期格式错误: {e}")
                    date_test_passed = False
                    
            if date_test_passed:
                print(f"\n✅ 日期测试通过: 所有日期都是未来日期")
                print(f"   最近预约: {min(future_dates)} 天后")
                print(f"   最远预约: {max(future_dates)} 天后")
            else:
                print(f"\n❌ 日期测试失败: 发现历史日期")
        else:
            print("❌ 无法测试日期: 没有生成可用时段")
            date_test_passed = False
        
        # 测试3: 检查消息中的日期显示
        print(f"\n🔍 测试3: 消息中日期显示检查")
        print("-" * 40)
        
        # 查找消息中的日期模式
        date_pattern = r'📅 可预约时间：(\d{4}-\d{2}-\d{2})'
        dates_in_message = re.findall(date_pattern, alert_message)
        
        message_date_test_passed = True
        if dates_in_message:
            print(f"📝 消息中找到 {len(dates_in_message)} 个预约日期:")
            for i, date_str in enumerate(dates_in_message, 1):
                try:
                    msg_date = datetime.strptime(date_str, '%Y-%m-%d')
                    days_from_now = (msg_date - today).days
                    
                    print(f"   {i}. {date_str} ({days_from_now:+d} 天)")
                    
                    if days_from_now <= 0:
                        print(f"      ❌ 消息中显示历史日期!")
                        message_date_test_passed = False
                    else:
                        print(f"      ✅ 消息中显示未来日期")
                        
                except Exception as e:
                    print(f"      ❌ 消息日期格式错误: {e}")
                    message_date_test_passed = False
            
            if message_date_test_passed:
                print(f"\n✅ 消息日期测试通过: 消息中所有日期都是未来日期")
            else:
                print(f"\n❌ 消息日期测试失败: 消息中发现历史日期")
        else:
            print("⚠️ 消息中没有找到预约日期 (可能因为没有可用时段)")
            # 检查是否有"暂无可用"的提示
            if "暂无可用的即时预约时段" in alert_message:
                print("💡 这是正常的：显示了无可用时段的提示")
                message_date_test_passed = True
            else:
                message_date_test_passed = False
        
        # 综合结果
        print(f"\n📊 综合测试结果")
        print("=" * 60)
        
        all_tests_passed = position_test_passed and date_test_passed and message_date_test_passed
        
        print(f"🔧 修复项目测试结果:")
        print(f"   1. 位置调整: {'✅ 通过' if position_test_passed else '❌ 失败'}")
        print(f"   2. 日期修复: {'✅ 通过' if date_test_passed else '❌ 失败'}")
        print(f"   3. 消息日期: {'✅ 通过' if message_date_test_passed else '❌ 失败'}")
        
        if all_tests_passed:
            print(f"\n🎉 所有测试通过! 修复成功!")
            print(f"✅ 号源推荐已正确移动到当前状态分析之下")
            print(f"✅ 预约日期已修复为未来日期")
        else:
            print(f"\n⚠️ 部分测试失败，需要进一步检查")
        
        return all_tests_passed
        
    except Exception as e:
        print(f"❌ 测试执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_position_and_date_fixes() 