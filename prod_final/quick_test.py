#!/usr/bin/env python3
"""
快速测试修复效果
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def quick_test():
    try:
        from structured_daily_alert_generator import StructuredDailyAlertGenerator
        generator = StructuredDailyAlertGenerator('nhs_alerts.db')
        
        # 真实用户信息
        user_info = {
            'user_id': 'telegram_7578790425',
            'first_name': 'alexcoming',
            'language': 'zh',
            'postcode': 'BT37 0ZP',
            'specialty': 'Nephrology',
            'threshold_weeks': 1,
            'radius_km': 20
        }
        
        print("🧪 快速测试 - 真实用户(Nephrology)")
        print(f"专科: {user_info['specialty']}")
        print(f"位置: {user_info['postcode']}")
        print(f"阈值: {user_info['threshold_weeks']} 周")
        
        # 获取核心状态
        core_status = generator._get_core_status_data(user_info)
        print(f"\n📊 核心状态:")
        print(f"最佳选择: {core_status.best_hospital}")
        print(f"可选医院: {core_status.total_options} 家")
        
        # 检查相关专科数据
        related_hospitals = generator._get_related_specialty_data('Nephrology', 'BT37 0ZP', 20)
        print(f"\n🔗 相关专科数据: {len(related_hospitals)} 家医院")
        for hospital in related_hospitals[:3]:
            print(f"  • {hospital['provider_name']} - {hospital['specialty_name']} - {hospital['waiting_weeks']}周")
        
        # 生成完整消息
        alert = generator.generate_structured_daily_alert(user_info)
        
        # 检查关键内容
        checks = [
            ("肾科", "肾科" in alert),
            ("数据状态", "数据状态" in alert),
            ("建议方案", "建议方案" in alert),
            ("普外科", "普外科" in alert),
            ("心脏科", "心脏科" in alert),
            ("神经科", "神经科" in alert)
        ]
        
        print(f"\n✅ 内容检查:")
        for name, check in checks:
            status = "✅" if check else "❌"
            print(f"  {status} {name}")
        
        passed = sum(1 for _, check in checks if check)
        print(f"\n📊 通过率: {passed}/{len(checks)} ({passed/len(checks):.1%})")
        
        if passed >= 4:
            print("🎉 修复成功！内容已大幅改善。")
        else:
            print("⚠️ 需要进一步调整。")
            
        return passed >= 4
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    quick_test() 