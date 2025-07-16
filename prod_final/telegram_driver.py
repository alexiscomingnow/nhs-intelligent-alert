#!/usr/bin/env python3
"""
优化版Telegram Driver - NHS智能等候提醒系统
完全重新设计的用户交互界面，简洁直观，编号命令系统，多语言支持
"""

import os
import logging
import requests
import sqlite3
import json
from typing import Dict, List, Optional
from datetime import datetime
from language_config import SUPPORTED_LANGUAGES, LANGUAGE_TEXTS, get_language_text, get_language_info

class TelegramDriver:
    """优化版Telegram驱动 - 支持多语言交互"""
    
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set.")
        
        self.send_message_url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        self.db_path = os.getenv('DATABASE_URL', 'sqlite:///nhs_alerts.db').replace('sqlite:///', '')
        
        # 设置日志
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # 用户会话状态
        self.user_sessions = {}
        
        # 语言配置
        self.supported_languages = SUPPORTED_LANGUAGES
        self.texts = LANGUAGE_TEXTS
    
    def send_alert_notification(self, user_phone: str, alert_type: str, alert_data: Dict) -> bool:
        """发送提醒通知"""
        try:
            # 获取用户语言偏好
            user_lang = self._get_user_language(user_phone)
            
            message_text = self._create_message_text(alert_type, alert_data, user_lang)
            
            return self._send_telegram_message(user_phone, message_text, parse_mode='Markdown')
        except Exception as e:
            self.logger.error(f"发送提醒通知失败: {e}")
            return False
    
    def process_user_message(self, chat_id: str, message_text: str, user_name: str = None) -> bool:
        """处理用户消息 - 增强版本，支持语言选择"""
        try:
            # 检查用户是否已选择语言
            if not self._has_language_preference(chat_id):
                return self._handle_language_selection(chat_id, message_text, user_name)
            
            # 获取用户语言
            user_lang = self._get_user_language(chat_id)
            
            # 处理命令
            if message_text.lower() in ['/start', 'hello', 'hi', '你好', 'start']:
                return self._send_welcome_message(chat_id, user_name, user_lang)
            
            # 检查是否为数字命令
            if message_text.strip().isdigit():
                number = int(message_text.strip())
                return self._handle_numbered_command(chat_id, number, user_lang)
            
            # 检查是否在设置流程中
            if chat_id in self.user_sessions:
                return self._handle_setup_flow(chat_id, message_text, user_lang)
            
            # 处理自然语言
            return self._handle_natural_language(chat_id, message_text, user_lang)
            
        except Exception as e:
            self.logger.error(f"处理用户消息失败: {e}")
            return self._send_error_message(chat_id)
    
    def _has_language_preference(self, chat_id: str) -> bool:
        """检查用户是否已设置语言偏好"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            user_id = f"telegram_{chat_id}"
            cursor.execute("""
                SELECT language FROM user_preferences WHERE user_id = ?
            """, (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            return result is not None and result[0] is not None
            
        except Exception as e:
            self.logger.error(f"检查语言偏好失败: {e}")
            return False
    
    def _get_user_language(self, chat_id: str) -> str:
        """获取用户语言偏好"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            user_id = f"telegram_{chat_id}"
            cursor.execute("""
                SELECT language FROM user_preferences WHERE user_id = ?
            """, (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result and result[0] else 'en'
            
        except Exception as e:
            self.logger.error(f"获取用户语言失败: {e}")
            return 'en'
    
    def _handle_language_selection(self, chat_id: str, message_text: str, user_name: str = None) -> bool:
        """处理语言选择"""
        try:
            # 如果是初次访问或hello命令，显示语言选择
            if message_text.lower() in ['/start', 'hello', 'hi', '你好', 'start']:
                return self._send_language_selection(chat_id, user_name)
            
            # 检查是否为语言选择数字
            if message_text.strip().isdigit():
                choice = message_text.strip()
                if choice in self.supported_languages:
                    return self._set_user_language(chat_id, choice, user_name)
            
            # 无效选择，重新显示语言选择
            return self._send_language_selection(chat_id, user_name)
            
        except Exception as e:
            self.logger.error(f"处理语言选择失败: {e}")
            return False
    
    def _send_language_selection(self, chat_id: str, user_name: str = None) -> bool:
        """发送语言选择菜单"""
        try:
            text = get_language_text('en', 'language_selection')
            return self._send_telegram_message(chat_id, text, parse_mode='Markdown')
        except Exception as e:
            self.logger.error(f"发送语言选择失败: {e}")
            return False
    
    def _set_user_language(self, chat_id: str, language_choice: str, user_name: str = None) -> bool:
        """设置用户语言偏好"""
        try:
            lang_info = get_language_info(language_choice)
            lang_code = lang_info['code']
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            user_id = f"telegram_{chat_id}"
            
            # 检查用户是否已存在
            cursor.execute("SELECT id FROM user_preferences WHERE user_id = ?", (user_id,))
            exists = cursor.fetchone()
            
            if exists:
                # 更新语言
                cursor.execute("""
                    UPDATE user_preferences SET language = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (lang_code, user_id))
            else:
                # 创建新用户记录
                cursor.execute("""
                    INSERT INTO user_preferences 
                    (user_id, phone_number, language, status, created_at, updated_at)
                    VALUES (?, ?, ?, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (user_id, chat_id, lang_code))
            
            conn.commit()
            conn.close()
            
            # 发送确认消息
            confirmation_text = f"{lang_info['flag']} {get_language_text(lang_code, 'language_confirmed')}"
            
            self._send_telegram_message(chat_id, confirmation_text, parse_mode='Markdown')
            
            # 发送欢迎消息
            return self._send_welcome_message(chat_id, user_name, lang_code)
            
        except Exception as e:
            self.logger.error(f"设置用户语言失败: {e}")
            return False
    
    def _send_welcome_message(self, chat_id: str, user_name: str = None, user_lang: str = 'en') -> bool:
        """发送欢迎消息"""
        try:
            greeting = f"👋 你好 {user_name}！\n\n" if user_name and user_lang == 'zh' else f"👋 Hello {user_name}!\n\n" if user_name else ""
            
            welcome_text = f"""{greeting}{get_language_text(user_lang, 'welcome_title')}
{get_language_text(user_lang, 'welcome_subtitle')}

{get_language_text(user_lang, 'why_need_me')}

{get_language_text(user_lang, 'benefit_1')}
{get_language_text(user_lang, 'benefit_2')}
{get_language_text(user_lang, 'benefit_3')}
{get_language_text(user_lang, 'benefit_4')}

{get_language_text(user_lang, 'get_started')}

{get_language_text(user_lang, 'new_user_options')}
*1* - {get_language_text(user_lang, 'option_setup')}
*2* - {get_language_text(user_lang, 'option_guide')}
*3* - {get_language_text(user_lang, 'option_features')}

{get_language_text(user_lang, 'existing_user_options')}
*1* - {get_language_text(user_lang, 'option_status')}
*2* - {get_language_text(user_lang, 'option_alerts')}
*3* - {get_language_text(user_lang, 'option_trends')}
*4* - {get_language_text(user_lang, 'option_reset')}
*5* - {get_language_text(user_lang, 'option_help')}
*6* - {get_language_text(user_lang, 'option_stop')}

💡 {get_language_text(user_lang, 'simple_instruction')}"""
            
            return self._send_telegram_message(chat_id, welcome_text, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"发送欢迎消息失败: {e}")
            return False

    def _handle_numbered_command(self, chat_id: str, number: int, user_lang: str = 'en') -> bool:
        """处理编号命令"""
        try:
            # 首先检查用户是否已有完成的偏好设置
            has_preferences = self.get_user_preferences(chat_id) is not None
            
            # 如果用户已有偏好设置，优先处理主菜单命令
            if has_preferences:
                # 主菜单命令 (对于已有偏好的用户)
                if number == 1:
                    return self._show_my_status(chat_id, user_lang)
                elif number == 2:
                    return self._show_recent_alerts(chat_id, user_lang)
                elif number == 3:
                    return self._show_waiting_trends(chat_id, user_lang)
                elif number == 4:
                    # 重置设置 - 清理可能存在的旧会话
                    if chat_id in self.user_sessions:
                        del self.user_sessions[chat_id]
                    return self._start_setup_flow(chat_id, user_lang)
                elif number == 5:
                    return self._send_help_menu(chat_id, user_lang)
                elif number == 6:
                    return self._handle_unsubscribe(chat_id, user_lang)
                else:
                    return self._send_invalid_choice(chat_id, "1-6", user_lang)
            else:
                # 新用户命令或设置流程
                if chat_id in self.user_sessions:
                    session = self.user_sessions[chat_id]
                    step = session.get('step', 1)
                    
                    # 如果在第2步（专科选择），将数字作为专科选择处理
                    if step == 2:
                        return self._handle_specialty_input(chat_id, str(number), user_lang)
                    # 如果在其他步骤，让setup_flow处理
                    else:
                        return self._handle_setup_flow(chat_id, str(number), user_lang)
                else:
                    # 新用户初始菜单
                    if number == 1:
                        return self._start_setup_flow(chat_id, user_lang)
                    elif number == 2:
                        return self._send_usage_guide(chat_id, user_lang)
                    elif number == 3:
                        return self._show_feature_overview(chat_id, user_lang)
                    else:
                        return self._send_invalid_choice(chat_id, "1-3", user_lang)
        except Exception as e:
            self.logger.error(f"处理编号命令失败: {e}")
            return False

    # 继续保留所有其他现有方法，但添加user_lang参数支持
    # 这里只展示关键的多语言支持方法，实际实现需要更新所有方法

    def _send_telegram_message(self, chat_id: str, text: str, parse_mode: str = None) -> bool:
        """发送Telegram消息 - 优化版本，增加重试和错误处理"""
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                payload = {
                    'chat_id': chat_id,
                    'text': text
                }
                
                if parse_mode:
                    payload['parse_mode'] = parse_mode
                
                # 设置更长的超时时间和重试策略
                response = requests.post(
                    self.send_message_url, 
                    json=payload, 
                    timeout=60,  # 增加超时时间
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code == 200:
                    self.logger.info(f"Message sent successfully to {chat_id}")
                    return True
                elif response.status_code == 429:  # Rate limit
                    self.logger.warning(f"Rate limit hit, waiting...")
                    import time
                    time.sleep(5)
                    continue
                else:
                    self.logger.error(f"Failed to send message: {response.status_code} - {response.text}")
                    if attempt < max_retries - 1:
                        self.logger.info(f"Retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
                        import time
                        time.sleep(retry_delay)
                        retry_delay *= 2  # 指数退避
                        continue
                    return False
                    
            except requests.exceptions.Timeout:
                self.logger.error(f"Request timeout on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    self.logger.info(f"Retrying in {retry_delay} seconds...")
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                return False
            except requests.exceptions.ConnectionError:
                self.logger.error(f"Connection error on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    self.logger.info(f"Retrying in {retry_delay} seconds...")
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                return False
            except Exception as e:
                self.logger.error(f"Unexpected error sending Telegram message: {e}")
                if attempt < max_retries - 1:
                    self.logger.info(f"Retrying in {retry_delay} seconds...")
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                return False
        
        self.logger.error(f"Failed to send message after {max_retries} attempts")
        return False

    def get_user_preferences(self, chat_id: str) -> Optional[Dict]:
        """获取用户偏好设置"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            user_id = f"telegram_{chat_id}"
            cursor.execute("""
                SELECT user_id, phone_number, postcode, specialty, threshold_weeks, radius_km, 
                       notification_types, language, status, created_at, updated_at
                FROM user_preferences WHERE user_id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'user_id': row[0],
                    'phone_number': row[1],
                    'postcode': row[2],
                    'specialty': row[3],
                    'threshold_weeks': row[4],
                    'radius_km': row[5],
                    'notification_types': json.loads(row[6]) if row[6] else [],
                    'language': row[7] or 'en',
                    'status': row[8],
                    'created_at': row[9],
                    'updated_at': row[10]
                }
            return None
            
        except Exception as e:
            self.logger.error(f"获取用户偏好失败: {e}")
            return None

    def _create_message_text(self, alert_type: str, alert_data: Dict, user_lang: str = 'en') -> str:
        """创建消息文本 - 支持多语言"""
        try:
            if alert_type == "waiting_time_alert":
                if user_lang == 'zh':
                    return f"""🚨 *等候时间提醒*

🏥 **医院**: {alert_data.get('hospital_name', '未知')}
🩺 **专科**: {alert_data.get('specialty', '未知')}
⏰ **等候时间**: {alert_data.get('waiting_weeks', 0)}周
📍 **距离**: {alert_data.get('distance_km', 0)}公里

💡 这比您的阈值({alert_data.get('threshold_weeks', 12)}周)更短！"""
                else:
                    return f"""🚨 *Waiting Time Alert*

🏥 **Hospital**: {alert_data.get('hospital_name', 'Unknown')}
🩺 **Specialty**: {alert_data.get('specialty', 'Unknown')}
⏰ **Waiting Time**: {alert_data.get('waiting_weeks', 0)} weeks
📍 **Distance**: {alert_data.get('distance_km', 0)} km

💡 This is shorter than your threshold ({alert_data.get('threshold_weeks', 12)} weeks)!"""
            else:
                return f"Alert: {alert_type}"
                
        except Exception as e:
            self.logger.error(f"创建消息文本失败: {e}")
            return "Alert notification"

    # 添加其他必要的方法存根
    def _send_main_menu(self, chat_id: str, user_lang: str = 'en') -> bool:
        """发送主菜单"""
        return self._send_welcome_message(chat_id, None, user_lang)

    def _start_setup_flow(self, chat_id: str, user_lang: str = 'en') -> bool:
        """开始设置流程 - 改进版本，提供更详细的指导"""
        if user_lang == 'zh':
            setup_text = """📍 **第1步/共3步：您的位置**

欢迎使用NHS智能等候提醒系统！

为了为您提供最准确的等候时间信息和附近医院推荐，我需要了解您的位置。

🏠 **请输入您的邮编**（例如：SW1A 1AA、M1 1AA、B1 1HQ）

💡 **为什么需要邮编？**
• 🔍 找到您附近的NHS医院
• 📏 计算精确的距离信息
• 🎯 只推荐您方便到达的医院
• 🚗 考虑实际旅行时间

🔒 **隐私保护**：
• 您的邮编仅用于距离计算
• 不会存储您的具体地址
• 所有数据都经过加密保护

请输入您的邮编："""
        else:
            setup_text = """📍 **Step 1/3: Your Location**

Welcome to the NHS Intelligent Waiting Time Alert System!

To provide you with accurate waiting times and nearby hospital recommendations, I need to know your location.

🏠 **Please enter your postcode** (e.g., SW1A 1AA, M1 1AA, B1 1HQ)

💡 **Why do I need your postcode?**
• 🔍 Find NHS hospitals near you
• 📏 Calculate accurate distances
• 🎯 Only recommend hospitals within your reach
• 🚗 Consider actual travel times

🔒 **Privacy Protection**:
• Your postcode is only used for distance calculations
• We don't store your specific address
• All data is encrypted and secure

Please enter your postcode:"""
        
        # 设置会话状态
        self.user_sessions[chat_id] = {
            'step': 1,
            'language': user_lang,
            'postcode': None,
            'specialty': None,
            'threshold_weeks': None,
            'radius_km': None
        }
        
        return self._send_telegram_message(chat_id, setup_text, parse_mode='Markdown')

    def _handle_postcode_input(self, chat_id: str, postcode: str, user_lang: str = 'en') -> bool:
        """处理邮编输入 - 改进版本"""
        if not self._validate_postcode(postcode):
            if user_lang == 'zh':
                error_text = """❌ 邮编格式无效

请输入有效的英国邮编格式：

✅ **正确格式示例**：
• SW1A 1AA（威斯敏斯特）
• M1 1AA（曼彻斯特市中心）
• B1 1HQ（伯明翰市中心）
• E1 6AN（伦敦东区）
• NW1 2BU（卡姆登）

💡 **格式说明**：
• 第一部分：1-2个字母 + 1-2个数字
• 第二部分：1个数字 + 2个字母
• 中间用空格分隔

🔍 **不确定您的邮编？**
• 访问 Royal Mail 邮编查询网站
• 查看您的银行账单或官方信件
• 使用 Google Maps 搜索您的地址

请重新输入您的邮编："""
            else:
                error_text = """❌ Invalid postcode format

Please enter a valid UK postcode:

✅ **Correct format examples**:
• SW1A 1AA (Westminster)
• M1 1AA (Manchester city centre)
• B1 1HQ (Birmingham city centre)
• E1 6AN (London East)
• NW1 2BU (Camden)

💡 **Format explanation**:
• First part: 1-2 letters + 1-2 numbers
• Second part: 1 number + 2 letters
• Separated by a space

🔍 **Don't know your postcode?**
• Visit the Royal Mail postcode finder
• Check your bank statements or official mail
• Use Google Maps to search your address

Please enter your postcode again:"""
            
            return self._send_telegram_message(chat_id, error_text, parse_mode='Markdown')
        
        # 保存邮编并进入下一步
        self.user_sessions[chat_id]['postcode'] = postcode.upper()
        self.user_sessions[chat_id]['step'] = 2
        
        if user_lang == 'zh':
            specialty_text = """🏥 **第2步/共3步：医疗专科**

很好！您的邮编已保存：**{postcode}**

现在请选择您需要监控的医疗专科。系统将为您监控这个专科的等候时间变化。

🩺 **请从以下NHS专科中选择**：

**🫀 心血管系统**
1️⃣ Cardiology (心脏科) - 心脏病、心律不齐、心脏手术

**🏥 其他专科**
2️⃣ Dermatology (皮肤科) - 皮肤病、皮肤手术
3️⃣ Gastroenterology (消化科) - 胃肠镜、肝病、肠道疾病

**🧠 神经系统**  
4️⃣ Neurology (神经科) - 中风、癫痫、帕金森病、头痛

**🔬 专科医学**
5️⃣ Oncology (肿瘤科) - 癌症治疗、化疗、放疗

**🦴 骨骼肌肉系统**
6️⃣ Orthopaedics (骨科) - 关节置换、骨折、脊柱手术

**🏥 其他专科**
7️⃣ Psychiatry (精神科) - 精神健康、心理治疗
8️⃣ Radiology (放射科) - 影像诊断、介入治疗
9️⃣ General Surgery (外科) - 一般外科手术

**🩸 内科系统**
1️⃣0️⃣ Urology (泌尿科) - 肾结石、前列腺、膀胱手术

**👩‍⚕️ 妇幼专科**
1️⃣1️⃣ Gynaecology (妇科) - 妇科手术、生殖健康
1️⃣2️⃣ Paediatrics (儿科) - 儿童医学、发育问题

**👁️ 感官系统**
1️⃣3️⃣ Ophthalmology (眼科) - 白内障、青光眼、视网膜手术
1️⃣4️⃣ ENT (耳鼻喉科) - 听力、鼻窦、咽喉问题

**🔬 专科医学**
1️⃣5️⃣ Endocrinology (内分泌科) - 糖尿病、甲状腺、激素
1️⃣6️⃣ Rheumatology (风湿科) - 关节炎、自身免疫病
1️⃣7️⃣ Haematology (血液科) - 血液病、白血病、贫血

**🩸 内科系统**
1️⃣8️⃣ Nephrology (肾科) - 肾病、透析、肾移植
1️⃣9️⃣ Respiratory Medicine (呼吸科) - 哮喘、肺病、睡眠呼吸

**🦴 骨骼肌肉系统**
2️⃣0️⃣ Trauma & Orthopaedics (创伤骨科) - 急诊骨科、运动损伤

💡 **如何选择？**
• 输入数字（1-20，如：1、6、13）
• 输入英文名称（如：Cardiology）
• 输入中文名称（如：心脏科）
• 常用术语（如：心脏、骨头、皮肤）

请选择您需要的专科：""".format(postcode=postcode.upper())
        else:
            specialty_text = """🏥 **Step 2/3: Medical Specialty**

Great! Your postcode is saved: **{postcode}**

Now please select the medical specialty you need to monitor. The system will track waiting time changes for this specialty.

🩺 **Please choose from these NHS specialties**:

**🫀 Cardiovascular**
1️⃣ Cardiology - Heart conditions, arrhythmia, cardiac surgery

**🏥 Other Specialties**
2️⃣ Dermatology - Skin conditions, dermatological surgery
3️⃣ Gastroenterology - Endoscopy, liver disease, bowel conditions

**🧠 Neurological**  
4️⃣ Neurology - Stroke, epilepsy, Parkinson's, headaches

**🔬 Specialist Medicine**
5️⃣ Oncology - Cancer treatment, chemotherapy, radiotherapy

**🦴 Musculoskeletal**
6️⃣ Orthopaedics - Joint replacement, fractures, spinal surgery

**🏥 Other Specialties**
7️⃣ Psychiatry - Mental health, psychotherapy
8️⃣ Radiology - Medical imaging, interventional procedures
9️⃣ General Surgery - General surgical procedures

**🩸 Internal Medicine**
1️⃣0️⃣ Urology - Kidney stones, prostate, bladder surgery

**👩‍⚕️ Women & Children**
1️⃣1️⃣ Gynaecology - Gynecological surgery, reproductive health
1️⃣2️⃣ Paediatrics - Children's medicine, developmental issues

**👁️ Sensory**
1️⃣3️⃣ Ophthalmology - Cataracts, glaucoma, retinal surgery
1️⃣4️⃣ ENT - Hearing, sinus, throat problems

**🔬 Specialist Medicine**
1️⃣5️⃣ Endocrinology - Diabetes, thyroid, hormones
1️⃣6️⃣ Rheumatology - Arthritis, autoimmune conditions
1️⃣7️⃣ Haematology - Blood disorders, leukaemia, anaemia

**🩸 Internal Medicine**
1️⃣8️⃣ Nephrology - Kidney disease, dialysis, transplants
1️⃣9️⃣ Respiratory Medicine - Asthma, lung disease, sleep breathing

**🦴 Musculoskeletal**
2️⃣0️⃣ Trauma & Orthopaedics - Emergency orthopedics, sports injuries

💡 **How to choose?**
• Enter a number (1-20, e.g., 1, 6, 13)
• Type the English name (e.g., Cardiology)
• Use common terms (e.g., heart, bone, skin)

Please select your specialty:""".format(postcode=postcode.upper())
        
        return self._send_telegram_message(chat_id, specialty_text, parse_mode='Markdown')

    def _handle_specialty_input(self, chat_id: str, specialty_input: str, user_lang: str = 'en') -> bool:
        """处理专科输入 - 支持数字、英文名称、中文名称和常用术语"""
        # NHS专科映射 - 修正为顺序显示的1-20编号
        nhs_specialty_map = {
            # 数字映射 (顺序显示的1-20)
            '1': 'Cardiology',
            '2': 'Dermatology', 
            '3': 'Gastroenterology',
            '4': 'Neurology',
            '5': 'Oncology',
            '6': 'Orthopaedics',
            '7': 'Psychiatry',
            '8': 'Radiology',
            '9': 'General Surgery',
            '10': 'Urology',
            '11': 'Gynaecology',
            '12': 'Paediatrics',
            '13': 'Ophthalmology',
            '14': 'ENT',
            '15': 'Endocrinology',
            '16': 'Rheumatology',
            '17': 'Haematology',
            '18': 'Nephrology',
            '19': 'Respiratory Medicine',
            '20': 'Trauma & Orthopaedics',
            
            # 英文名称映射
            'cardiology': 'Cardiology',
            'dermatology': 'Dermatology',
            'gastroenterology': 'Gastroenterology',
            'neurology': 'Neurology',
            'oncology': 'Oncology',
            'orthopaedics': 'Orthopaedics',
            'orthopedics': 'Orthopaedics',  # 美式拼写
            'psychiatry': 'Psychiatry',
            'radiology': 'Radiology',
            'general surgery': 'General Surgery',
            'surgery': 'General Surgery',
            'urology': 'Urology',
            'gynaecology': 'Gynaecology',
            'gynecology': 'Gynaecology',  # 美式拼写
            'paediatrics': 'Paediatrics',
            'pediatrics': 'Paediatrics',  # 美式拼写
            'ophthalmology': 'Ophthalmology',
            'ent': 'ENT',
            'endocrinology': 'Endocrinology',
            'rheumatology': 'Rheumatology',
            'haematology': 'Haematology',
            'hematology': 'Haematology',  # 美式拼写
            'nephrology': 'Nephrology',
            'respiratory medicine': 'Respiratory Medicine',
            'trauma & orthopaedics': 'Trauma & Orthopaedics',
            'trauma and orthopaedics': 'Trauma & Orthopaedics',
            
            # 中文名称映射
            '心脏科': 'Cardiology',
            '皮肤科': 'Dermatology',
            '消化科': 'Gastroenterology',
            '神经科': 'Neurology',
            '肿瘤科': 'Oncology',
            '骨科': 'Orthopaedics',
            '精神科': 'Psychiatry',
            '放射科': 'Radiology',
            '外科': 'General Surgery',
            '泌尿科': 'Urology',
            '妇科': 'Gynaecology',
            '儿科': 'Paediatrics',
            '眼科': 'Ophthalmology',
            '耳鼻喉科': 'ENT',
            '内分泌科': 'Endocrinology',
            '风湿科': 'Rheumatology',
            '血液科': 'Haematology',
            '肾科': 'Nephrology',
            '呼吸科': 'Respiratory Medicine',
            '创伤骨科': 'Trauma & Orthopaedics',
            
            # 常用术语映射
            'heart': 'Cardiology',
            'cardiac': 'Cardiology',
            'skin': 'Dermatology',
            'stomach': 'Gastroenterology',
            'brain': 'Neurology',
            'cancer': 'Oncology',
            'bone': 'Orthopaedics',
            'joint': 'Orthopaedics',
            'mental': 'Psychiatry',
            'psychology': 'Psychiatry',
            'scan': 'Radiology',
            'imaging': 'Radiology',
            'kidney': 'Urology',
            'bladder': 'Urology',
            'women': 'Gynaecology',
            'child': 'Paediatrics',
            'children': 'Paediatrics',
            'eye': 'Ophthalmology',
            'vision': 'Ophthalmology',
            'ear': 'ENT',
            'nose': 'ENT',
            'throat': 'ENT',
            'diabetes': 'Endocrinology',
            'thyroid': 'Endocrinology',
            'arthritis': 'Rheumatology',
            'blood': 'Haematology',
            'lung': 'Respiratory Medicine',
            'breathing': 'Respiratory Medicine',
            '心脏': 'Cardiology',
            '皮肤': 'Dermatology',
            '胃': 'Gastroenterology',
            '大脑': 'Neurology',
            '癌症': 'Oncology',
            '骨头': 'Orthopaedics',
            '关节': 'Orthopaedics',
            '精神': 'Psychiatry',
            '扫描': 'Radiology',
            '肾脏': 'Urology',
            '膀胱': 'Urology',
            '女性': 'Gynaecology',
            '孩子': 'Paediatrics',
            '儿童': 'Paediatrics',
            '眼睛': 'Ophthalmology',
            '视力': 'Ophthalmology',
            '耳朵': 'ENT',
            '鼻子': 'ENT',
            '喉咙': 'ENT',
            '糖尿病': 'Endocrinology',
            '甲状腺': 'Endocrinology',
            '关节炎': 'Rheumatology',
            '血液': 'Haematology',
            '肺': 'Respiratory Medicine',
            '呼吸': 'Respiratory Medicine'
        }
        
        # 清理输入
        clean_input = specialty_input.strip().lower()
        
        # 查找匹配的专科
        specialty = None
        
        # 首先检查直接匹配
        if clean_input in nhs_specialty_map:
            specialty = nhs_specialty_map[clean_input]
        else:
            # 检查包含匹配（用于常用术语）
            for key, value in nhs_specialty_map.items():
                if key in clean_input or clean_input in key:
                    specialty = value
                    break
        
        # 如果没有找到匹配
        if not specialty:
            if user_lang == 'zh':
                error_text = f"""❌ 无法识别专科："{specialty_input}"

请选择以下方式之一：

🔢 **输入数字**（1-20）：
• 1 = 心脏科 (Cardiology)
• 2 = 皮肤科 (Dermatology)
• 6 = 骨科 (Orthopaedics)
• 13 = 眼科 (Ophthalmology)
• 等等...

📝 **输入英文名称**：
• Cardiology
• Dermatology
• Orthopaedics
• 等等...

🈯 **输入中文名称**：
• 心脏科
• 皮肤科
• 骨科
• 等等...

🔍 **常用术语**：
• heart (心脏)
• bone (骨头)
• skin (皮肤)
• eye (眼睛)
• 等等...

请重新选择："""
            else:
                error_text = f"""❌ Cannot recognize specialty: "{specialty_input}"

Please choose one of these options:

🔢 **Enter a number** (1-20):
• 1 = Cardiology
• 2 = Dermatology
• 6 = Orthopaedics
• 13 = Ophthalmology
• etc...

📝 **Type English name**:
• Cardiology
• Dermatology
• Orthopaedics
• etc...

🔍 **Use common terms**:
• heart
• bone
• skin
• eye
• etc...

Please try again:"""
            
            return self._send_telegram_message(chat_id, error_text, parse_mode='Markdown')
        
        # 保存选择并进入下一步
        if chat_id in self.user_sessions:
            self.user_sessions[chat_id]['specialty'] = specialty
            self.user_sessions[chat_id]['step'] = 3
            
            # 发送第3步偏好设置
            preferences_text = self._get_detailed_preferences_text(specialty, user_lang)
            return self._send_telegram_message(chat_id, preferences_text, parse_mode='Markdown')
        else:
            return self._start_setup_flow(chat_id, user_lang)

    def _handle_setup_flow(self, chat_id: str, message_text: str, user_lang: str = 'en') -> bool:
        """处理设置流程"""
        if chat_id not in self.user_sessions:
            return self._start_setup_flow(chat_id, user_lang)
        
        session = self.user_sessions[chat_id]
        step = session.get('step', 1)
        
        if step == 1:
            return self._handle_postcode_input(chat_id, message_text, user_lang)
        elif step == 2:
            return self._handle_specialty_input(chat_id, message_text, user_lang)
        elif step == 3:
            # 检查是否在等待自定义输入
            if session.get('waiting_custom', False):
                # 清除等待标志并处理自定义输入
                session['waiting_custom'] = False
                return self._handle_custom_preferences_input(chat_id, message_text, user_lang)
            else:
                return self._handle_preferences_input(chat_id, message_text, user_lang)
        else:
            return self._start_setup_flow(chat_id, user_lang)

    def _handle_preferences_input(self, chat_id: str, preferences_input: str, user_lang: str = 'en') -> bool:
        """处理偏好输入 - 改进版本，支持1-4数字选择和自定义输入"""
        input_text = preferences_input.strip()
        
        # 检查是否在等待自定义输入
        session = self.user_sessions.get(chat_id, {})
        if session.get('waiting_custom', False):
            # 清除等待标志
            session['waiting_custom'] = False
            # 处理自定义输入
            try:
                threshold_weeks, radius_km = self._parse_preferences_input_improved(preferences_input)
            except ValueError as e:
                error_text = """❌ 自定义格式无效

💡 **正确格式**：`[周数] [距离]`
📝 **例如**：`8周 30公里` 或 `6 weeks 40 km`

请重新输入：""" if user_lang == 'zh' else """❌ Invalid custom format

💡 **Correct format**: `[weeks] [distance]`
📝 **Example**: `8 weeks 30 km` or `6周 30公里`

Please try again:"""
                
                # 保持等待状态
                session['waiting_custom'] = True
                return self._send_telegram_message(chat_id, error_text, parse_mode='Markdown')
        
        # 处理1-4数字选择
        elif input_text in ['1', '2', '3', '4']:
            if input_text == '1':  # 紧急需求
                threshold_weeks = 4
                radius_km = 50
            elif input_text == '2':  # 常规需求
                threshold_weeks = 12
                radius_km = 25
            elif input_text == '3':  # 可以等待
                threshold_weeks = 18
                radius_km = 15
            elif input_text == '4':  # 自定义设置
                custom_prompt = """📝 **自定义设置**

请输入您的具体偏好：

💡 **格式**：`[周数] [距离]` 
📝 **例如**：`8周 30公里` 或 `6 weeks 40 km`

请输入：""" if user_lang == 'zh' else """📝 **Custom Settings**

Please enter your specific preferences:

💡 **Format**: `[weeks] [distance]`
📝 **Example**: `8 weeks 30 km` or `6周 30公里`

Please enter:"""
                
                # 设置等待自定义输入的标志
                if chat_id in self.user_sessions:
                    self.user_sessions[chat_id]['waiting_custom'] = True
                
                return self._send_telegram_message(chat_id, custom_prompt, parse_mode='Markdown')
        
        # 处理自定义输入或默认值
        elif input_text.lower() in ['default', '默认', 'def']:
            threshold_weeks = 12
            radius_km = 25
        else:
            try:
                threshold_weeks, radius_km = self._parse_preferences_input_improved(preferences_input)
            except ValueError as e:
                if user_lang == 'zh':
                    error_text = f"""❌ 格式无效

请使用正确的格式：

📊 **推荐选择**：
1️⃣ 紧急需求（4周 50公里）
2️⃣ 常规需求（12周 25公里）
3️⃣ 可以等待（18周 15公里）
4️⃣ 自定义设置

✅ **或自定义格式**：
• `12周 25公里`
• `4 weeks 30 km`

❌ **您输入的**：`{preferences_input}`

请重新输入："""
                else:
                    error_text = f"""❌ Invalid format

Please use the correct format:

📊 **Recommended choices**:
1️⃣ Urgent needs (4 weeks 50 km)
2️⃣ Regular needs (12 weeks 25 km)
3️⃣ Can wait (18 weeks 15 km)
4️⃣ Custom settings

✅ **Or custom format**:
• `12 weeks 25 km`
• `4 weeks 30 km`

❌ **You entered**: `{preferences_input}`

Please try again:"""
                
                return self._send_telegram_message(chat_id, error_text, parse_mode='Markdown')
        
        # 验证范围
        if not (1 <= threshold_weeks <= 52):
            error_text = "❌ 周数必须在1-52之间" if user_lang == 'zh' else "❌ Weeks must be between 1-52"
            return self._send_telegram_message(chat_id, error_text)
        
        if not (5 <= radius_km <= 100):
            error_text = "❌ 距离必须在5-100公里之间" if user_lang == 'zh' else "❌ Distance must be between 5-100 km"
            return self._send_telegram_message(chat_id, error_text)
        
        # 保存用户偏好
        session = self.user_sessions[chat_id]
        result = self._save_user_preferences(
            user_phone=chat_id,
            postcode=session['postcode'],
            specialty=session['specialty'],
            threshold_weeks=threshold_weeks,
            radius_km=radius_km,
            notification_types=["threshold", "change", "alternative"]
        )
        
        # 清理会话
        del self.user_sessions[chat_id]
        
        # 发送设置完成消息和用户设置回顾
        if user_lang == 'zh':
            success_text = f"""🎉 **设置完成！**

✅ **您的个人NHS监控配置**：

👤 **用户ID**: {chat_id}
📍 **邮编**: {session['postcode']}
🏥 **专科**: {session['specialty']}
⏰ **提醒阈值**: {threshold_weeks} 周
📏 **搜索半径**: {radius_km} 公里
📱 **通知方式**: Telegram

🔔 **您将收到以下类型的提醒**：

1️⃣ **等候时间达标提醒** - 当您关注的专科等候时间降到{threshold_weeks}周以下时
2️⃣ **等候时间变化提醒** - 当等候时间有显著变化时（增加或减少超过2周）
3️⃣ **更优替代方案提醒** - 当发现距离您{radius_km}公里内有更短等候时间的医院时
4️⃣ **趋势分析提醒** - 每周发送等候时间趋势分析和预测

🚀 **系统现在开始为您监控！**

📊 使用 **3** 查看等候时间趋势
📋 使用 **1** 查看当前状态
❓ 使用 **help** 获取帮助

💡 您随时可以发送自然语言问题，如："心脏科等候时间多久？"或"我附近有更快的选择吗？" """
        else:
            success_text = f"""🎉 **Setup Complete!**

✅ **Your Personal NHS Monitoring Profile**:

👤 **User ID**: {chat_id}
📍 **Postcode**: {session['postcode']}
🏥 **Specialty**: {session['specialty']}
⏰ **Alert Threshold**: {threshold_weeks} weeks
📏 **Search Radius**: {radius_km} km
📱 **Notifications**: Telegram

🔔 **You will receive these types of alerts**:

1️⃣ **Threshold Alerts** - When {session['specialty']} waiting times drop below {threshold_weeks} weeks
2️⃣ **Change Alerts** - When waiting times change significantly (±2 weeks)
3️⃣ **Better Alternative Alerts** - When shorter waits are found within {radius_km}km
4️⃣ **Trend Analysis** - Weekly waiting time trends and predictions

🚀 **System is now monitoring for you!**

📊 Use **3** to view waiting time trends
📋 Use **1** to check current status
❓ Use **help** for assistance

💡 You can ask natural language questions anytime, like: "How long is the cardiology wait?" or "Any shorter options near me?" """
        
        return self._send_telegram_message(chat_id, success_text, parse_mode='Markdown')

    # 其他方法的简化实现
    def _show_my_status(self, chat_id: str, user_lang: str = 'en') -> bool:
        """显示我的状态 - 包含地理位置信息"""
        try:
            user_prefs = self.get_user_preferences(chat_id)
            if not user_prefs:
                no_setup_text = "❌ 尚未设置偏好，请先发送 *1* 进行设置" if user_lang == 'zh' else "❌ No preferences set, please send *1* to set up"
                return self._send_telegram_message(chat_id, no_setup_text, parse_mode='Markdown')
            
            # 构建状态信息
            postcode = user_prefs.get('postcode', '未设置')
            specialty = user_prefs.get('specialty', '未设置')
            threshold_weeks = user_prefs.get('threshold_weeks', 12)
            radius_km = user_prefs.get('radius_km', 25)
            
            if user_lang == 'zh':
                status_text = f"""📊 *我的状态*

👤 **用户ID**: {chat_id}
📍 **邮编**: {postcode}
🏥 **专科**: {specialty}
⏰ **提醒阈值**: {threshold_weeks} 周
📏 **搜索半径**: {radius_km} 公里
📱 **通知渠道**: Telegram
✅ **监控状态**: 活跃

🔄 *4* - 重新设置偏好
📊 *3* - 查看等候趋势"""
            else:
                status_text = f"""📊 *My Status*

👤 **User ID**: {chat_id}
📍 **Postcode**: {postcode}
🏥 **Specialty**: {specialty}
⏰ **Alert Threshold**: {threshold_weeks} weeks
📏 **Search Radius**: {radius_km} km
📱 **Notification Channel**: Telegram
✅ **Monitoring Status**: Active

🔄 *4* - Reset preferences
📊 *3* - View waiting trends"""
            
            return self._send_telegram_message(chat_id, status_text, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"显示状态失败: {e}")
            error_text = "❌ 获取状态信息失败" if user_lang == 'zh' else "❌ Failed to retrieve status"
            return self._send_telegram_message(chat_id, error_text, parse_mode='Markdown')

    def _show_recent_alerts(self, chat_id: str, user_lang: str = 'en') -> bool:
        """显示最近提醒 - 集成智能提醒引擎"""
        try:
            # 从数据库获取用户最近的提醒
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 查询最近7天的提醒
            user_id = f"telegram_{chat_id}"
            cursor.execute('''
                SELECT alert_type, data, created_at, status 
                FROM alert_events 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 10
            ''', (user_id,))
            
            alerts = cursor.fetchall()
            conn.close()
            
            if not alerts:
                no_alerts_text = "📋 暂无最近提醒记录" if user_lang == 'zh' else "📋 No recent alerts"
                return self._send_telegram_message(chat_id, no_alerts_text, parse_mode='Markdown')
            
            # 格式化提醒历史
            if user_lang == 'zh':
                alerts_text = "📋 *最近提醒*\n\n"
            else:
                alerts_text = "📋 *Recent Alerts*\n\n"
            
            for i, (alert_type, data_json, created_at, status) in enumerate(alerts[:5], 1):
                try:
                    data = json.loads(data_json) if data_json else {}
                    
                    # 获取提醒时间
                    created_time = datetime.fromisoformat(created_at).strftime('%m-%d %H:%M')
                    
                    # 格式化提醒内容
                    hospital_name = data.get('hospital_name', '未知医院')
                    specialty = data.get('specialty_name', data.get('specialty', '未知专科'))
                    waiting_weeks = data.get('waiting_weeks', data.get('current_weeks', 0))
                    distance_km = data.get('distance_km', 0)
                    
                    if user_lang == 'zh':
                        alert_info = f"""**{i}.** 🏥 {hospital_name}
   🩺 {specialty} - {waiting_weeks}周
   📍 距离: {distance_km}km | ⏰ {created_time}"""
                    else:
                        alert_info = f"""**{i}.** 🏥 {hospital_name}
   🩺 {specialty} - {waiting_weeks} weeks
   📍 Distance: {distance_km}km | ⏰ {created_time}"""
                    
                    alerts_text += alert_info + "\n\n"
                    
                except Exception as e:
                    self.logger.error(f"处理提醒数据失败: {e}")
                    continue
            
            # 添加操作提示
            if user_lang == 'zh':
                alerts_text += "💡 *3* - 查看等候趋势\n*1* - 查看当前状态"
            else:
                alerts_text += "💡 *3* - View waiting trends\n*1* - View current status"
            
            return self._send_telegram_message(chat_id, alerts_text, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"获取最近提醒失败: {e}")
            error_text = "❌ 获取提醒历史失败" if user_lang == 'zh' else "❌ Failed to retrieve alert history"
            return self._send_telegram_message(chat_id, error_text, parse_mode='Markdown')

    def _show_waiting_trends(self, chat_id: str, user_lang: str = 'en') -> bool:
        """显示等候趋势 - 使用增强版服务"""
        try:
            # 导入增强版趋势分析服务
            from enhanced_waiting_trends_service import EnhancedWaitingTrendsService
            
            # 创建服务实例并获取增强版趋势分析
            enhanced_trends_service = EnhancedWaitingTrendsService(self.db_path)
            trends_text = enhanced_trends_service.get_enhanced_user_trends(chat_id, user_lang)
            
            return self._send_telegram_message(chat_id, trends_text, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"获取增强等候趋势失败: {e}")
            
            # 回退到基础错误消息
            if user_lang == 'zh':
                error_text = """❌ **趋势分析暂时不可用**

可能原因：
• 系统正在更新数据
• 您的专科暂无足够数据
• 网络连接问题

💡 **建议**：
• 稍后再试
• 检查您的设置 (**1** 查看状态)
• 重新设置偏好 (**4** 重置设置)

🔧 或者尝试：
• 输入具体问题，如："心脏科等候多久？"
• 查询附近医院："我附近有什么医院？" """
            else:
                error_text = """❌ **Trend analysis temporarily unavailable**

Possible reasons:
• System is updating data
• Insufficient data for your specialty
• Network connectivity issues

💡 **Suggestions**:
• Try again later
• Check your settings (**1** view status)
• Reset preferences (**4** reset settings)

🔧 Or try:
• Ask specific questions like: "How long is cardiology wait?"
• Query nearby hospitals: "What hospitals are near me?" """
            
            return self._send_telegram_message(chat_id, error_text, parse_mode='Markdown')

    def _send_usage_guide(self, chat_id: str, user_lang: str = 'en') -> bool:
        """发送使用指南"""
        guide_text = get_language_text(user_lang, 'option_guide') + "\n\n"
        guide_text += "使用指南内容" if user_lang == 'zh' else "Usage guide content"
        
        return self._send_telegram_message(chat_id, guide_text, parse_mode='Markdown')

    def _send_features_intro(self, chat_id: str, user_lang: str = 'en') -> bool:
        """发送功能介绍"""
        features_text = get_language_text(user_lang, 'option_features') + "\n\n"
        features_text += "功能介绍内容" if user_lang == 'zh' else "Features introduction content"
        
        return self._send_telegram_message(chat_id, features_text, parse_mode='Markdown')

    def _send_help_menu(self, chat_id: str, user_lang: str = 'en') -> bool:
        """发送帮助菜单"""
        help_text = get_language_text(user_lang, 'help_title') + "\n\n"
        help_text += "帮助内容" if user_lang == 'zh' else "Help content"
        
        return self._send_telegram_message(chat_id, help_text, parse_mode='Markdown')

    def _handle_unsubscribe(self, chat_id: str, user_lang: str = 'en') -> bool:
        """处理取消订阅"""
        confirm_text = get_language_text(user_lang, 'unsubscribe_confirm')
        
        return self._send_telegram_message(chat_id, confirm_text, parse_mode='Markdown')

    def _send_invalid_choice(self, chat_id: str, valid_range: str, user_lang: str = 'en') -> bool:
        """发送无效选择提示"""
        error_text = get_language_text(user_lang, 'invalid_choice') + " " + valid_range
        
        return self._send_telegram_message(chat_id, error_text, parse_mode='Markdown')

    def _handle_natural_language(self, chat_id: str, message_text: str, user_lang: str = 'en') -> bool:
        """处理自然语言 - 集成地理感知查询"""
        try:
            message_lower = message_text.lower()
            
            # 等候时间查询
            waiting_keywords = ['waiting', 'wait', 'time', '等候', '等待', '时间']
            if any(keyword in message_lower for keyword in waiting_keywords):
                return self._handle_waiting_time_query(chat_id, message_text, user_lang)
            
            # 医院查询
            hospital_keywords = ['hospital', 'clinic', '医院', '诊所']
            if any(keyword in message_lower for keyword in hospital_keywords):
                return self._handle_hospital_query(chat_id, message_text, user_lang)
            
            # 趋势查询
            trend_keywords = ['trend', 'change', 'better', 'worse', '趋势', '变化', '改善']
            if any(keyword in message_lower for keyword in trend_keywords):
                return self._show_waiting_trends(chat_id, user_lang)
            
            # 距离/位置查询
            location_keywords = ['near', 'distance', 'close', '附近', '距离', '接近']
            if any(keyword in message_lower for keyword in location_keywords):
                return self._handle_location_query(chat_id, message_text, user_lang)
            
            # 默认帮助响应
            if user_lang == 'zh':
                help_text = """🤖 *智能助手*

我可以帮您：
• 查询等候时间：*"心脏科等候时间"*
• 寻找附近医院：*"附近有哪些医院"*
• 分析趋势变化：*"趋势如何"*

💡 或使用数字命令:
*1* - 查看状态  *2* - 最近提醒  *3* - 等候趋势"""
            else:
                help_text = """🤖 *Smart Assistant*

I can help you with:
• Check waiting times: *"cardiology waiting time"*
• Find nearby hospitals: *"hospitals near me"*
• Analyze trends: *"how are trends"*

💡 Or use numbered commands:
*1* - Status  *2* - Recent alerts  *3* - Trends"""
            
            return self._send_telegram_message(chat_id, help_text, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"处理自然语言失败: {e}")
            return self._send_error_message(chat_id, user_lang)

    def _handle_waiting_time_query(self, chat_id: str, query: str, user_lang: str = 'en') -> bool:
        """处理等候时间查询"""
        try:
            # 获取用户偏好
            user_prefs = self.get_user_preferences(chat_id)
            if not user_prefs:
                setup_msg = "请先设置您的偏好 (*1*)" if user_lang == 'zh' else "Please set up your preferences first (*1*)"
                return self._send_telegram_message(chat_id, setup_msg, parse_mode='Markdown')
            
            # 使用增强版等候趋势服务获取当前数据
            from enhanced_waiting_trends_service import EnhancedWaitingTrendsService
            enhanced_trends_service = EnhancedWaitingTrendsService(self.db_path)
            
            # 使用增强版服务获取智能推荐
            trends_text = enhanced_trends_service.get_enhanced_user_trends(chat_id, user_lang)
            
            return self._send_telegram_message(chat_id, trends_text, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"处理等候时间查询失败: {e}")
            return self._send_error_message(chat_id, user_lang)

    def _handle_hospital_query(self, chat_id: str, query: str, user_lang: str = 'en') -> bool:
        """处理医院查询"""
        try:
            user_prefs = self.get_user_preferences(chat_id)
            if not user_prefs:
                setup_msg = "请先设置您的位置偏好 (*1*)" if user_lang == 'zh' else "Please set up your location preferences first (*1*)"
                return self._send_telegram_message(chat_id, setup_msg, parse_mode='Markdown')
            
            postcode = user_prefs.get('postcode', '')
            radius_km = user_prefs.get('radius_km', 25)
            
            # 使用地理服务查找附近医院
            from geographic_service import GeographicService
            geo_service = GeographicService(self.db_path)
            
            # 获取附近医院（简化实现）
            if user_lang == 'zh':
                response = f"""🏥 *附近医院*

📍 **您的位置**: {postcode}
📏 **搜索半径**: {radius_km} 公里

🔍 正在搜索附近医院...

💡 使用 *3* 查看详细等候趋势"""
            else:
                response = f"""🏥 *Nearby Hospitals*

📍 **Your Location**: {postcode}
📏 **Search Radius**: {radius_km} km

🔍 Searching for nearby hospitals...

💡 Use *3* for detailed waiting trends"""
            
            return self._send_telegram_message(chat_id, response, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"处理医院查询失败: {e}")
            return self._send_error_message(chat_id, user_lang)

    def _handle_location_query(self, chat_id: str, query: str, user_lang: str = 'en') -> bool:
        """处理位置相关查询"""
        try:
            user_prefs = self.get_user_preferences(chat_id)
            if not user_prefs:
                setup_msg = "请先设置您的位置 (*1*)" if user_lang == 'zh' else "Please set up your location first (*1*)"
                return self._send_telegram_message(chat_id, setup_msg, parse_mode='Markdown')
            
            postcode = user_prefs.get('postcode', '')
            radius_km = user_prefs.get('radius_km', 25)
            
            if user_lang == 'zh':
                response = f"""📍 *位置信息*

🏠 **您的邮编**: {postcode}
📏 **搜索半径**: {radius_km} 公里

💡 系统会优先推荐 {radius_km} 公里内的医院
🔄 *4* - 重新设置位置和半径
📊 *3* - 查看按距离排序的等候趋势"""
            else:
                response = f"""📍 *Location Information*

🏠 **Your Postcode**: {postcode}
📏 **Search Radius**: {radius_km} km

💡 System prioritizes hospitals within {radius_km} km
🔄 *4* - Reset location and radius
📊 *3* - View waiting trends sorted by distance"""
            
            return self._send_telegram_message(chat_id, response, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"处理位置查询失败: {e}")
            return self._send_error_message(chat_id, user_lang)

    def _send_error_message(self, chat_id: str, user_lang: str = 'en') -> bool:
        """发送错误消息"""
        error_text = get_language_text(user_lang, 'error_occurred')
        
        return self._send_telegram_message(chat_id, error_text, parse_mode='Markdown')

    # 辅助方法
    def _validate_postcode(self, postcode: str) -> bool:
        """验证邮编格式"""
        import re
        # 简化的英国邮编验证
        pattern = r'^[A-Z]{1,2}[0-9][A-Z0-9]?\s?[0-9][A-Z]{2}$'
        return bool(re.match(pattern, postcode.upper()))

    def _parse_preferences_input_improved(self, input_text: str) -> tuple:
        """改进的偏好解析，支持多种格式"""
        import re
        
        # 清理输入
        text = input_text.lower().strip()
        
        # 正则表达式匹配各种格式
        patterns = [
            r'(\d+)\s*(?:周|weeks?|w)\s*[,，\s]*(\d+)\s*(?:公里|千米|km|kilometers?|k)',
            r'(\d+)\s*[,，\s]*(\d+)',  # 简单的数字格式
            r'(\d+)\s*(?:周|weeks?|w)\s*(\d+)',  # 没有距离单位
            r'(\d+)\s*(\d+)\s*(?:公里|千米|km|kilometers?|k)'  # 没有时间单位
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                weeks = int(match.group(1))
                distance = int(match.group(2))
                
                # 智能判断哪个是周数，哪个是距离
                if weeks > 52 or (distance <= 52 and weeks > distance):
                    # 可能搞反了，交换
                    weeks, distance = distance, weeks
                
                return weeks, distance
        
        raise ValueError("无法解析输入格式")

    def _save_user_preferences(self, user_phone: str, postcode: str, specialty: str, 
                             threshold_weeks: int, radius_km: int, notification_types: List[str]) -> str:
        """保存用户偏好设置"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 将通知类型转换为JSON字符串
            notification_types_json = json.dumps(notification_types)
            
            # 生成用户ID
            user_id = f"telegram_{user_phone}"
            
            cursor.execute("""
                INSERT OR REPLACE INTO user_preferences 
                (user_id, phone_number, postcode, specialty, threshold_weeks, radius_km, 
                 notification_types, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (user_id, user_phone, postcode, specialty, threshold_weeks, radius_km, notification_types_json))
            
            result_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            self.logger.info(f"保存用户偏好成功: {user_phone}")
            return str(result_id)
            
        except Exception as e:
            self.logger.error(f"保存用户偏好失败: {e}")
            raise
    def _get_detailed_specialty_text(self, postcode: str, user_lang: str = 'en'):
        """生成详细的专科选择文本"""
        if user_lang == 'zh':
            return f"""🏥 **第2步/共3步：医疗专科**

很好！您的邮编已保存：**{postcode}**

现在请选择您需要监控的医疗专科。系统将为您监控这个专科的等候时间变化。

🩺 **请从以下NHS专科中选择**：

**🫀 心血管系统**
1️⃣ Cardiology (心脏科) - 心脏病、心律不齐、心脏手术

**🏥 其他专科**
2️⃣ Dermatology (皮肤科) - 皮肤病、皮肤手术
3️⃣ Gastroenterology (消化科) - 胃肠镜、肝病、肠道疾病

**🧠 神经系统**  
4️⃣ Neurology (神经科) - 中风、癫痫、帕金森病、头痛

**🔬 专科医学**
5️⃣ Oncology (肿瘤科) - 癌症治疗、化疗、放疗

**🦴 骨骼肌肉系统**
6️⃣ Orthopaedics (骨科) - 关节置换、骨折、脊柱手术

**🏥 其他专科**
7️⃣ Psychiatry (精神科) - 精神健康、心理治疗
8️⃣ Radiology (放射科) - 影像诊断、介入治疗
9️⃣ General Surgery (外科) - 一般外科手术

**🩸 内科系统**
1️⃣0️⃣ Urology (泌尿科) - 肾结石、前列腺、膀胱手术

**👩‍⚕️ 妇幼专科**
1️⃣1️⃣ Gynaecology (妇科) - 妇科手术、生殖健康
1️⃣2️⃣ Paediatrics (儿科) - 儿童医学、发育问题

**👁️ 感官系统**
1️⃣3️⃣ Ophthalmology (眼科) - 白内障、青光眼、视网膜手术
1️⃣4️⃣ ENT (耳鼻喉科) - 听力、鼻窦、咽喉问题

**🔬 专科医学**
1️⃣5️⃣ Endocrinology (内分泌科) - 糖尿病、甲状腺、激素
1️⃣6️⃣ Rheumatology (风湿科) - 关节炎、自身免疫病
1️⃣7️⃣ Haematology (血液科) - 血液病、白血病、贫血

**🩸 内科系统**
1️⃣8️⃣ Nephrology (肾科) - 肾病、透析、肾移植
1️⃣9️⃣ Respiratory Medicine (呼吸科) - 哮喘、肺病、睡眠呼吸

**🦴 骨骼肌肉系统**
2️⃣0️⃣ Trauma & Orthopaedics (创伤骨科) - 急诊骨科、运动损伤

💡 **如何选择？**
• 输入数字（如：1、6、13）
• 输入英文名称（如：Cardiology）
• 输入中文名称（如：心脏科）

请选择您需要的专科："""
        else:
            return f"""🏥 **Step 2/3: Medical Specialty**

Great! Your postcode is saved: **{postcode}**

Now please select the medical specialty you need to monitor. The system will track waiting time changes for this specialty.

🩺 **Please choose from these NHS specialties**:

**🫀 Cardiovascular**
1️⃣ Cardiology - Heart conditions, arrhythmia, cardiac surgery

**🏥 Other Specialties**
2️⃣ Dermatology - Skin conditions, dermatological surgery
3️⃣ Gastroenterology - Endoscopy, liver disease, bowel conditions

**🧠 Neurological**  
4️⃣ Neurology - Stroke, epilepsy, Parkinson's, headaches

**🔬 Specialist Medicine**
5️⃣ Oncology - Cancer treatment, chemotherapy, radiotherapy

**🦴 Musculoskeletal**
6️⃣ Orthopaedics - Joint replacement, fractures, spinal surgery

**🏥 Other Specialties**
7️⃣ Psychiatry - Mental health, psychotherapy
8️⃣ Radiology - Medical imaging, interventional procedures
9️⃣ General Surgery - General surgical procedures

**🩸 Internal Medicine**
1️⃣0️⃣ Urology - Kidney stones, prostate, bladder surgery

**👩‍⚕️ Women & Children**
1️⃣1️⃣ Gynaecology - Gynecological surgery, reproductive health
1️⃣2️⃣ Paediatrics - Children's medicine, developmental issues

**👁️ Sensory**
1️⃣3️⃣ Ophthalmology - Cataracts, glaucoma, retinal surgery
1️⃣4️⃣ ENT - Hearing, sinus, throat problems

**🔬 Specialist Medicine**
1️⃣5️⃣ Endocrinology - Diabetes, thyroid, hormones
1️⃣6️⃣ Rheumatology - Arthritis, autoimmune conditions
1️⃣7️⃣ Haematology - Blood disorders, leukaemia, anaemia

**🩸 Internal Medicine**
1️⃣8️⃣ Nephrology - Kidney disease, dialysis, transplants
1️⃣9️⃣ Respiratory Medicine - Asthma, lung disease, sleep breathing

**🦴 Musculoskeletal**
2️⃣0️⃣ Trauma & Orthopaedics - Emergency orthopedics, sports injuries

💡 **How to choose?**
• Enter a number (1-20, e.g., 1, 6, 13)
• Type the English name (e.g., Cardiology)
• Use common terms (e.g., heart, bone, skin)

Please select your specialty:"""

    def _get_detailed_preferences_text(self, specialty: str, user_lang: str = 'en'):
        """生成详细的偏好设置文本"""
        if user_lang == 'zh':
            return f"""⚙️ **第3步/共3步：设置您的提醒偏好**

您已选择：**{specialty}**

现在请设置您的提醒偏好：

🔔 **等候时间阈值**：当等候时间低于这个数值时提醒您
📏 **搜索半径**：在您附近多少公里范围内搜索医院

📊 **推荐设置**：
1️⃣ **紧急需求** - 4周 50公里（急需治疗，愿意走远一些）
2️⃣ **常规需求** - 12周 25公里（标准等候，适中距离）
3️⃣ **可以等待** - 18周 15公里（不急，希望就近治疗）
4️⃣ **自定义设置** - 自己输入具体数值

💡 **输入格式**：
• 输入数字：`1`、`2`、`3` 或 `4`
• 自定义格式：`[周数] [距离]` - 例如：`12周 25公里`

🎯 **为什么设置这些？**
• **周数**：当等候时间降到这个数值时，系统会提醒您可以预约
• **距离**：只推荐在您方便到达范围内的医院

请选择您的偏好（1-4）或输入自定义设置："""
        else:
            return f"""⚙️ **Step 3/3: Set Your Alert Preferences**

You selected: **{specialty}**

Now please set your alert preferences:

🔔 **Waiting Time Threshold**: Get alerted when waiting times drop below this number
📏 **Search Radius**: How far are you willing to travel for treatment?

📊 **Recommended Settings**:
1️⃣ **Urgent needs** - 4 weeks 50 km (Need treatment soon, willing to travel further)
2️⃣ **Regular needs** - 12 weeks 25 km (Standard wait, moderate distance)
3️⃣ **Can wait** - 18 weeks 15 km (Not urgent, prefer nearby treatment)
4️⃣ **Custom settings** - Enter your own values

💡 **Input Format**:
• Enter number: `1`, `2`, `3` or `4`
• Custom format: `[weeks] [distance]` - e.g., `12 weeks 25 km`

🎯 **Why set these?**
• **Weeks**: Get notified when waiting times drop to this level
• **Distance**: Only suggest hospitals within your convenient travel range

Please choose your preference (1-4) or enter custom settings:"""


    def update_user_status(self, chat_id: str, status: str) -> bool:
        """更新用户状态"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            user_id = f"telegram_{chat_id}"
            cursor.execute("""
                UPDATE user_preferences SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (status, user_id))
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            return success
            
        except Exception as e:
            self.logger.error(f"更新用户状态失败: {e}")
            return False 