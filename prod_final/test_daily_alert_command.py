#!/usr/bin/env python3
"""
测试每日提醒命令脚本
独立测试每日提醒功能，无需等待定时任务
"""

import asyncio
import sys
import os
import sqlite3
from datetime import datetime

# 添加路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

async def test_daily_alert_for_user(user_id: str = None, test_all: bool = False):
    """测试特定用户或所有用户的每日提醒"""
    try:
        print("🧪 开始测试每日提醒功能...")
        print("=" * 50)
        
        from daily_comprehensive_alert_service import DailyComprehensiveAlertService
        
        service = DailyComprehensiveAlertService()
        
        if test_all:
            print("📊 为所有用户生成每日提醒...")
            alerts = await service.generate_daily_alerts_for_all_users()
            print(f"✅ 完成！为 {len(alerts)} 个用户生成了每日提醒")
            
            # 显示每个用户的提醒摘要
            for i, alert in enumerate(alerts[:5], 1):  # 只显示前5个
                print(f"\n📋 用户 {i} 提醒摘要:")
                print(f"   用户ID: {alert.user_id}")
                print(f"   关键洞察数量: {len(alert.key_insights)}")
                print(f"   推荐行动数量: {len(alert.recommendations)}")
                if alert.key_insights:
                    print(f"   首要洞察: {alert.key_insights[0][:100]}...")
        
        elif user_id:
            print(f"📊 为用户 {user_id} 生成每日提醒...")
            
            # 获取用户信息
            user_info = get_user_info(user_id)
            if not user_info:
                print(f"❌ 找不到用户 {user_id} 的信息")
                return
            
            alert = await service.generate_user_daily_alert(user_info)
            
            if alert:
                print("✅ 每日提醒生成成功！")
                print("\n" + "=" * 60)
                
                # 格式化并显示完整提醒
                message = service._format_daily_alert_message(alert, user_info.get('language', 'zh'))
                print("📱 完整每日提醒内容:")
                print("-" * 60)
                print(message)
                print("-" * 60)
                
                print(f"\n📊 提醒统计:")
                print(f"   关键洞察: {len(alert.key_insights)} 条")
                print(f"   推荐行动: {len(alert.recommendations)} 项")
                print(f"   生成时间: {alert.alert_date.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print("❌ 每日提醒生成失败")
        
        else:
            # 交互式选择用户
            users = get_all_users()
            if not users:
                print("❌ 没有找到任何用户")
                return
            
            print(f"📋 找到 {len(users)} 个用户:")
            for i, user in enumerate(users, 1):
                print(f"   {i}. {user['user_id']} ({user.get('first_name', 'Unknown')})")
            
            choice = input("\n请选择用户编号 (或按 Enter 测试所有用户): ").strip()
            
            if choice == "":
                await test_daily_alert_for_user(test_all=True)
            elif choice.isdigit() and 1 <= int(choice) <= len(users):
                selected_user = users[int(choice) - 1]
                await test_daily_alert_for_user(selected_user['user_id'])
            else:
                print("❌ 无效选择")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

def get_user_info(user_id: str) -> dict:
    """获取用户信息"""
    try:
        conn = sqlite3.connect('nhs_alerts.db')
        cursor = conn.cursor()
        
        # 从 telegram_users 表获取基本信息
        if user_id.startswith('telegram_'):
            chat_id = user_id.replace('telegram_', '')
            cursor.execute("""
                SELECT chat_id, username, first_name, language_code
                FROM telegram_users 
                WHERE chat_id = ?
            """, (chat_id,))
        else:
            cursor.execute("""
                SELECT chat_id, username, first_name, language_code
                FROM telegram_users 
                WHERE user_id = ? OR chat_id = ?
            """, (user_id, user_id))
        
        user_row = cursor.fetchone()
        if not user_row:
            return None
        
        # 获取用户偏好设置
        cursor.execute("""
            SELECT postcode, specialty, threshold_weeks, radius_km, status
            FROM user_preferences 
            WHERE user_id = ? AND status = 'active'
        """, (user_id,))
        
        prefs_row = cursor.fetchone()
        if not prefs_row:
            return None
        
        conn.close()
        
        # 构建用户信息字典
        user_info = {
            'user_id': user_id,
            'chat_id': user_row[0],
            'username': user_row[1] or '',
            'first_name': user_row[2] or '',
            'language': user_row[3] or 'zh',
            'postcode': prefs_row[0],
            'specialty': prefs_row[1],
            'threshold_weeks': prefs_row[2],
            'radius_km': prefs_row[3],
            'status': prefs_row[4]
        }
        
        return user_info
        
    except Exception as e:
        print(f"获取用户信息失败: {e}")
        return None

def get_all_users() -> list:
    """获取所有活跃用户"""
    try:
        conn = sqlite3.connect('nhs_alerts.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT u.chat_id, u.username, u.first_name, u.language_code,
                   ('telegram_' || u.chat_id) as user_id
            FROM telegram_users u
            INNER JOIN user_preferences p ON ('telegram_' || u.chat_id) = p.user_id
            WHERE p.status = 'active'
            ORDER BY u.first_name
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        users = []
        for row in rows:
            users.append({
                'chat_id': row[0],
                'username': row[1] or '',
                'first_name': row[2] or '',
                'language': row[3] or 'zh',
                'user_id': row[4]
            })
        
        return users
        
    except Exception as e:
        print(f"获取用户列表失败: {e}")
        return []

def show_help():
    """显示帮助信息"""
    print("""
🧪 每日提醒测试工具

用法:
    python test_daily_alert_command.py                    # 交互式选择用户
    python test_daily_alert_command.py --all              # 测试所有用户
    python test_daily_alert_command.py --user USER_ID     # 测试特定用户
    python test_daily_alert_command.py --help             # 显示帮助

示例:
    python test_daily_alert_command.py --user telegram_123456789
    python test_daily_alert_command.py --all

功能:
• 测试每日提醒生成功能
• 查看完整的提醒内容
• 验证个性化推荐
• 检查趋势分析
• 模拟真实发送场景
    """)

async def main():
    """主函数"""
    args = sys.argv[1:]
    
    if '--help' in args or '-h' in args:
        show_help()
        return
    
    if '--all' in args:
        await test_daily_alert_for_user(test_all=True)
    elif '--user' in args:
        try:
            user_index = args.index('--user')
            if user_index + 1 < len(args):
                user_id = args[user_index + 1]
                await test_daily_alert_for_user(user_id)
            else:
                print("❌ --user 参数需要指定用户ID")
                show_help()
        except ValueError:
            print("❌ 无效的 --user 参数")
            show_help()
    else:
        # 交互式模式
        await test_daily_alert_for_user()

if __name__ == "__main__":
    print("🏥 NHS 每日提醒测试工具")
    print("=" * 50)
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 测试已取消")
    except Exception as e:
        print(f"\n❌ 运行出错: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🎉 测试完成！") 