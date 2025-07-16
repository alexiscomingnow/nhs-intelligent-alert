#!/usr/bin/env python3
"""
重置用户语言偏好脚本
允许用户重新选择语言
"""

import sqlite3
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def reset_user_language(user_id: str = None):
    """重置用户的语言偏好，允许重新选择语言"""
    try:
        db_path = os.getenv('DATABASE_URL', 'sqlite:///nhs_alerts.db').replace('sqlite:///', '')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        if user_id:
            # 重置特定用户
            cursor.execute("""
                UPDATE user_preferences 
                SET language = NULL, updated_at = CURRENT_TIMESTAMP 
                WHERE user_id = ?
            """, (user_id,))
            affected = cursor.rowcount
            print(f"✅ 重置用户 {user_id} 的语言偏好: {affected} 条记录被更新")
        else:
            # 显示所有用户让用户选择
            cursor.execute("""
                SELECT user_id, language, phone_number, created_at 
                FROM user_preferences 
                ORDER BY created_at DESC
            """)
            users = cursor.fetchall()
            
            if not users:
                print("❌ 没有找到任何用户记录")
                return
            
            print("\n📋 现有用户列表:")
            print("-" * 80)
            for i, (uid, lang, phone, created) in enumerate(users, 1):
                print(f"{i}. 用户ID: {uid}")
                print(f"   语言: {lang or '未设置'}")
                print(f"   电话: {phone}")
                print(f"   创建时间: {created}")
                print("-" * 80)
            
            try:
                choice = input(f"\n请选择要重置的用户 (1-{len(users)}) 或输入 'all' 重置所有用户: ").strip()
                
                if choice.lower() == 'all':
                    cursor.execute("""
                        UPDATE user_preferences 
                        SET language = NULL, updated_at = CURRENT_TIMESTAMP
                    """)
                    affected = cursor.rowcount
                    print(f"✅ 重置所有用户的语言偏好: {affected} 条记录被更新")
                else:
                    idx = int(choice) - 1
                    if 0 <= idx < len(users):
                        selected_user = users[idx][0]
                        cursor.execute("""
                            UPDATE user_preferences 
                            SET language = NULL, updated_at = CURRENT_TIMESTAMP 
                            WHERE user_id = ?
                        """, (selected_user,))
                        affected = cursor.rowcount
                        print(f"✅ 重置用户 {selected_user} 的语言偏好: {affected} 条记录被更新")
                    else:
                        print("❌ 无效的选择")
                        return
            except (ValueError, IndexError):
                print("❌ 无效的输入")
                return
        
        conn.commit()
        conn.close()
        
        print("\n🌍 语言偏好已重置！")
        print("📱 现在在Telegram中发送 /start 或 hello 将显示语言选择菜单")
        
    except Exception as e:
        print(f"❌ 重置失败: {e}")

if __name__ == "__main__":
    print("🌍 NHS智能提醒系统 - 语言偏好重置工具")
    print("=" * 50)
    
    # 从命令行参数获取用户ID，或者交互式选择
    import sys
    if len(sys.argv) > 1:
        user_id = sys.argv[1]
        reset_user_language(user_id)
    else:
        reset_user_language() 