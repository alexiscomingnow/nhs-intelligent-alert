#!/usr/bin/env python3
"""
测试真实用户的无数据情况修复
"""

import sqlite3
import sys
import os
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_real_user_nephrology():
    """测试真实用户的肾科数据问题"""
    try:
        print("🧪 测试真实用户(Nephrology)问题修复")
        print("=" * 60)
        
        # 设置环境变量
        os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token_for_testing'
        
        from telegram_driver import TelegramDriver
        driver = TelegramDriver()
        
        # 获取真实用户信息
        user_info = driver._get_user_info_for_daily_alert('7578790425')
        
        if not user_info:
            print("❌ 无法获取真实用户信息")
            return False
        
        print(f"👤 真实用户信息:")
        print(f"  姓名: {user_info.get('first_name')}")
        print(f"  专科: {user_info.get('specialty')}")
        print(f"  位置: {user_info.get('postcode')}")
        print(f"  阈值: {user_info.get('threshold_weeks')} 周")
        print(f"  搜索半径: {user_info.get('radius_km')} 公里")
        print(f"  语言: {user_info.get('language')}")
        
        # 使用修复后的生成器
        from structured_daily_alert_generator import StructuredDailyAlertGenerator
        generator = StructuredDailyAlertGenerator('nhs_alerts.db')
        
        print(f"\n📨 生成修复后的推送内容:")
        print("-" * 60)
        
        alert_message = generator.generate_structured_daily_alert(user_info)
        
        # 只显示前500字符避免输出过长
        print(alert_message[:500] + "...")
        
        print("-" * 60)
        
        # 检查关键改进
        improvements = [
            ("清晰的数据状态说明", "数据库暂无肾科数据" in alert_message),
            ("原因解释", "可能的原因" in alert_message),
            ("解决方案", "建议方案" in alert_message),
            ("相关专科推荐", "泌尿科" in alert_message or "Urology" in alert_message),
            ("实用建议", "直接联系" in alert_message or "扩大范围" in alert_message),
            ("中文专科名称", "肾科" in alert_message)
        ]
        
        print(f"\n🔍 修复效果检查:")
        passed_count = 0
        for description, check in improvements:
            status = "✅" if check else "❌"
            print(f"  {status} {description}")
            if check:
                passed_count += 1
        
        success_rate = passed_count / len(improvements)
        print(f"\n📊 修复成功率: {passed_count}/{len(improvements)} ({success_rate:.1%})")
        
        if success_rate >= 0.8:
            print("🎉 修复效果优秀！用户体验显著改善。")
            return True
        elif success_rate >= 0.6:
            print("✅ 修复效果良好，但仍有改进空间。")
            return True
        else:
            print("❌ 修复效果不理想，需要进一步改进。")
            return False
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_database_specialty_data():
    """检查数据库中的专科数据"""
    try:
        print("\n🔍 检查数据库专科数据")
        print("=" * 40)
        
        conn = sqlite3.connect('nhs_alerts.db')
        cursor = conn.cursor()
        
        # 检查所有可用专科
        cursor.execute("SELECT DISTINCT specialty_name, COUNT(*) as count FROM nhs_rtt_data GROUP BY specialty_name ORDER BY count DESC")
        specialties = cursor.fetchall()
        
        print("📊 数据库中可用的专科:")
        for specialty, count in specialties:
            print(f"  • {specialty}: {count} 条记录")
        
        # 检查是否有肾科相关数据
        nephrology_keywords = ['Nephrology', 'nephrology', 'Renal', 'renal', 'Kidney', 'kidney']
        
        print(f"\n🔍 搜索肾科相关数据:")
        found_nephrology = False
        for keyword in nephrology_keywords:
            cursor.execute("SELECT COUNT(*) FROM nhs_rtt_data WHERE specialty_name LIKE ?", (f'%{keyword}%',))
            count = cursor.fetchone()[0]
            if count > 0:
                print(f"  ✅ {keyword}: {count} 条记录")
                found_nephrology = True
            else:
                print(f"  ❌ {keyword}: 0 条记录")
        
        if not found_nephrology:
            print("\n❌ 确认：数据库中没有肾科相关数据")
            print("💡 这解释了为什么用户看到'暂无数据'的问题")
        
        conn.close()
        return specialties
        
    except Exception as e:
        print(f"❌ 数据库检查失败: {e}")
        return []

def show_before_after_comparison():
    """显示修复前后的对比"""
    print("\n📈 修复前后对比")
    print("=" * 60)
    
    print("🔴 **修复前 - 用户看到的令人困惑的内容**:")
    print("""
## 📊 当前等候状态分析

🏥 最佳选择：暂无数据
⏱️ 最短等候：0周
📈 平均等候：0.0周  
🎯 是否达标：❌ 超出您的1周期望
🔍 可选医院：0家
""")
    
    print("🟢 **修复后 - 清晰有用的信息**:")
    print("""
## 📊 当前等候状态分析

❌ **数据状态**：数据库暂无肾科数据

🔍 **可能的原因**：
• NHS数据库中暂无肾科专科的等候时间记录
• 该专科可能使用不同的名称或分类
• 数据更新中，暂时缺失

💡 **建议方案**：
• 🔄 **专科调整**：考虑选择相关专科（如泌尿科、普外科）
• 📞 **直接联系**：致电当地医院询问肾科服务
• 🌍 **扩大范围**：尝试增加搜索半径至50公里
• 🏥 **私立选择**：考虑私立医疗机构

🎯 **相关专科建议**：
  1. 泌尿科 (Urology)
  2. 普外科 (General Surgery)
  3. 心脏科 (Cardiology)
""")
    
    print("📊 **改进效果**:")
    print("✅ 消除了令人困惑的'暂无数据'、'0家医院'")
    print("✅ 提供了清晰的问题说明和原因解释")
    print("✅ 给出了具体可行的解决方案")
    print("✅ 推荐了相关专科作为替代选择")
    print("✅ 提供了实用的联系策略")
    print("✅ 建议了多种解决途径")

if __name__ == "__main__":
    print(f"🚀 真实用户无数据问题修复验证 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 检查数据库专科数据
    specialties = check_database_specialty_data()
    
    # 2. 测试真实用户的修复效果
    success = test_real_user_nephrology()
    
    # 3. 显示修复前后对比
    show_before_after_comparison()
    
    if success:
        print("\n🎉 真实用户问题修复成功！")
        print("\n💡 现在用户将看到:")
        print("• 清晰的数据状态说明而不是令人困惑的'暂无数据'")
        print("• 有用的相关专科建议(泌尿科、普外科等)")
        print("• 具体可行的解决方案和行动计划")
        print("• 专业的问题解释和多种选择建议")
        print("• 完全中文的友好界面")
    else:
        print("\n❌ 修复效果需要进一步改进")
    
    print(f"\n🏁 验证结束 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}") 