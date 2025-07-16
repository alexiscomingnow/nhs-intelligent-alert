#!/usr/bin/env python3
"""
NHS每日提醒调度器
定时为所有用户生成和发送每日全面提醒
"""

import asyncio
import schedule
import time
import logging
from datetime import datetime, timedelta
from daily_comprehensive_alert_service import DailyComprehensiveAlertService
from notification_manager import NotificationManager

class DailyAlertScheduler:
    """每日提醒调度器"""
    
    def __init__(self):
        self.daily_service = DailyComprehensiveAlertService()
        self.notification_manager = NotificationManager("telegram")  # 使用Telegram
        self.logger = logging.getLogger(__name__)
        
        # 设置调度时间
        self.daily_alert_time = "08:00"  # 每天早上8点
        self.weekly_summary_time = "09:00"  # 每周一早上9点
        
    def start_scheduler(self):
        """启动调度器"""
        try:
            # 每日提醒
            schedule.every().day.at(self.daily_alert_time).do(self._run_daily_alerts)
            
            # 每周摘要（每周一）
            schedule.every().monday.at(self.weekly_summary_time).do(self._run_weekly_summary)
            
            # 测试：立即运行一次
            schedule.every().minute.do(self._run_test_alert).tag('test')
            
            self.logger.info("每日提醒调度器已启动")
            print(f"📅 每日提醒调度器已启动")
            print(f"⏰ 每日提醒时间：{self.daily_alert_time}")
            print(f"📊 每周摘要时间：每周一 {self.weekly_summary_time}")
            print(f"🔄 测试模式：每分钟运行一次（可手动取消）")
            
            # 运行调度循环
            while True:
                schedule.run_pending()
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("调度器已停止")
            print("\n📴 每日提醒调度器已停止")
        except Exception as e:
            self.logger.error(f"调度器运行失败: {e}")
            print(f"❌ 调度器错误: {e}")
    
    def _run_daily_alerts(self):
        """运行每日提醒"""
        try:
            self.logger.info("开始生成每日提醒")
            print(f"\n🌅 开始生成每日提醒 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 异步运行
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            alerts = loop.run_until_complete(
                self.daily_service.generate_daily_alerts_for_all_users()
            )
            
            loop.close()
            
            self.logger.info(f"每日提醒生成完成，共{len(alerts)}个用户")
            print(f"✅ 每日提醒生成完成：{len(alerts)} 个用户")
            
        except Exception as e:
            self.logger.error(f"每日提醒生成失败: {e}")
            print(f"❌ 每日提醒失败: {e}")
    
    def _run_weekly_summary(self):
        """运行每周摘要"""
        try:
            self.logger.info("开始生成每周摘要")
            print(f"\n📊 开始生成每周摘要 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 这里可以添加每周摘要逻辑
            # 例如：趋势分析、用户参与度统计、系统改进建议等
            
            print("✅ 每周摘要完成")
            
        except Exception as e:
            self.logger.error(f"每周摘要生成失败: {e}")
            print(f"❌ 每周摘要失败: {e}")
    
    def _run_test_alert(self):
        """运行测试提醒（仅用于测试）"""
        try:
            print(f"\n🧪 测试提醒 - {datetime.now().strftime('%H:%M:%S')}")
            
            # 运行一次后取消测试任务
            schedule.clear('test')
            
            # 立即运行一次每日提醒进行测试
            self._run_daily_alerts()
            
        except Exception as e:
            self.logger.error(f"测试提醒失败: {e}")
    
    def stop_scheduler(self):
        """停止调度器"""
        schedule.clear()
        self.logger.info("调度器已清理")

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 启动调度器
    scheduler = DailyAlertScheduler()
    scheduler.start_scheduler() 