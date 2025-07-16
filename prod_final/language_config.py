#!/usr/bin/env python3
"""
多语言配置文件 - 支持伦敦Top10语言
"""

# 伦敦Top10语言配置
SUPPORTED_LANGUAGES = {
    '1': {
        'code': 'en',
        'name': 'English',
        'native_name': 'English',
        'flag': '🇬🇧'
    },
    '2': {
        'code': 'zh',
        'name': 'Chinese',
        'native_name': '中文',
        'flag': '🇨🇳'
    },
    '3': {
        'code': 'hi',
        'name': 'Hindi',
        'native_name': 'हिन्दी',
        'flag': '🇮🇳'
    },
    '4': {
        'code': 'ur',
        'name': 'Urdu',
        'native_name': 'اردو',
        'flag': '🇵🇰'
    },
    '5': {
        'code': 'bn',
        'name': 'Bengali',
        'native_name': 'বাংলা',
        'flag': '🇧🇩'
    },
    '6': {
        'code': 'ar',
        'name': 'Arabic',
        'native_name': 'العربية',
        'flag': '🇸🇦'
    },
    '7': {
        'code': 'pl',
        'name': 'Polish',
        'native_name': 'Polski',
        'flag': '🇵🇱'
    },
    '8': {
        'code': 'fr',
        'name': 'French',
        'native_name': 'Français',
        'flag': '🇫🇷'
    },
    '9': {
        'code': 'es',
        'name': 'Spanish',
        'native_name': 'Español',
        'flag': '🇪🇸'
    },
    '10': {
        'code': 'pt',
        'name': 'Portuguese',
        'native_name': 'Português',
        'flag': '🇵🇹'
    }
}

# 多语言文本配置
LANGUAGE_TEXTS = {
    'en': {
        'language_selection': """🌍 *Welcome to NHS Intelligent Alert System*

Please select your preferred language:

1️⃣ 🇬🇧 English
2️⃣ 🇨🇳 中文 (Chinese)
3️⃣ 🇮🇳 हिन्दी (Hindi)
4️⃣ 🇵🇰 اردو (Urdu)
5️⃣ 🇧🇩 বাংলা (Bengali)
6️⃣ 🇸🇦 العربية (Arabic)
7️⃣ 🇵🇱 Polski (Polish)
8️⃣ 🇫🇷 Français (French)
9️⃣ 🇪🇸 Español (Spanish)
🔟 🇵🇹 Português (Portuguese)

*Simply enter the number (1-10) of your preferred language.*""",
        'language_confirmed': "✅ Language set to English. Let's get started!",
        'welcome_title': "🏥 *NHS Intelligent Alert System*",
        'welcome_subtitle': "Your Personal Healthcare Waiting Time Assistant",
        'why_need_me': "🤔 *Why do you need me?*",
        'benefit_1': "📊 *24/7 Monitoring* - I continuously track NHS waiting times",
        'benefit_2': "⚡ *Instant Notifications* - Get alerts when times drop below your threshold",
        'benefit_3': "🔍 *Find Faster Options* - I'll suggest shorter alternatives nearby",
        'benefit_4': "💡 *Smart Insights* - Receive trend analysis and predictions",
        'get_started': "🚀 *Ready to get started?*",
        'new_user_options': "For new users:",
        'existing_user_options': "For existing users:",
        'option_setup': "Start Setup",
        'option_guide': "Usage Guide",
        'option_features': "Feature Overview",
        'option_status': "View Status",
        'option_alerts': "Recent Alerts",
        'option_trends': "Waiting Trends",
        'option_reset': "Reset Settings",
        'option_help': "Help",
        'option_stop': "Stop Service",
        'option_test_daily': "Test Daily Alert",
        'simple_instruction': "Simply enter a number to select a function!",
        'invalid_choice': "❌ Invalid choice. Please enter a number between",
        'setup_step1_title': "📍 *Step 1/3: Your Location*",
        'setup_step1_desc': "Please enter your postcode (e.g., SW1A 1AA):",
        'setup_step1_purpose': "💡 *Why?* This helps me find hospitals near you and calculate travel distances.",
        'setup_step2_title': "🏥 *Step 2/3: Medical Specialty*",
        'setup_step2_desc': "Which medical specialty do you need? You can:",
        'setup_step2_options': "• Enter a number (1-20) from the list below\n• Type the specialty name in English or Chinese",
        'setup_step3_title': "⚙️ *Step 3/3: Alert Preferences*",
        'setup_step3_desc': "Set your alert preferences:",
        'setup_step3_format': "Format: `[weeks] [distance]` or `default`",
        'setup_step3_examples': "Examples:\n• `2 weeks 30 km` - Alert when ≤2 weeks, within 30km\n• `default` - Use system defaults (8 weeks, 25km)",
        'setup_step3_purpose': "💡 *Why set these?*\n• **Weeks**: Get notified when waiting times drop\n• **Distance**: Find convenient locations near you",
        'postcode_invalid': "❌ Invalid postcode format. Please enter a valid UK postcode (e.g., SW1A 1AA).",
        'specialty_invalid': "❌ Invalid specialty. Please choose a number (1-20) or enter a valid specialty name.",
        'preferences_invalid': "❌ Invalid format. Please use: `[weeks] [distance]` or `default`\nExample: `2 weeks 30 km`",
        'setup_complete': "🎉 *Setup Complete!*",
        'monitoring_started': "✅ Monitoring started for your preferences",
        'status_title': "📊 *Your Current Status*",
        'no_preferences': "❌ No preferences set. Please run setup first.",
        'recent_alerts_title': "📬 *Recent Alerts*",
        'no_recent_alerts': "📭 No recent alerts found.",
        'trends_title': "📈 *Waiting Time Trends*",
        'help_title': "❓ *Help & Support*",
        'unsubscribe_confirm': "❌ *Service Stopped*\n\nYou have been unsubscribed from all alerts.",
        'error_occurred': "❌ *Something went wrong*\n\nPlease try again later, or:\n\n*1* - Return to main menu\n*help* - View help\n\nIf the problem persists, please contact support."
    },
    'zh': {
        'language_selection': """🌍 *欢迎使用NHS智能等候提醒系统*

请选择您的首选语言：

1️⃣ 🇬🇧 English
2️⃣ 🇨🇳 中文 (Chinese)
3️⃣ 🇮🇳 हिन्दी (Hindi)
4️⃣ 🇵🇰 اردو (Urdu)
5️⃣ 🇧🇩 বাংলা (Bengali)
6️⃣ 🇸🇦 العربية (Arabic)
7️⃣ 🇵🇱 Polski (Polish)
8️⃣ 🇫🇷 Français (French)
9️⃣ 🇪🇸 Español (Spanish)
🔟 🇵🇹 Português (Portuguese)

*请输入您偏好语言的数字(1-10)。*""",
        'language_confirmed': "✅ 语言已设置为中文。让我们开始吧！",
        'welcome_title': "🏥 *NHS智能等候提醒系统*",
        'welcome_subtitle': "您的个人医疗等候时间助手",
        'why_need_me': "🤔 *为什么需要我？*",
        'benefit_1': "📊 *24/7监控* - 我持续跟踪NHS等候时间",
        'benefit_2': "⚡ *即时通知* - 当时间低于您的阈值时立即提醒",
        'benefit_3': "🔍 *寻找更快选择* - 我会建议附近更短的替代方案",
        'benefit_4': "💡 *智能洞察* - 接收趋势分析和预测",
        'get_started': "🚀 *准备开始了吗？*",
        'new_user_options': "新用户选项：",
        'existing_user_options': "现有用户选项：",
        'option_setup': "开始设置",
        'option_guide': "使用指南",
        'option_features': "功能概述",
        'option_status': "查看状态",
        'option_alerts': "最近提醒",
        'option_trends': "等候趋势",
        'option_reset': "重置设置",
        'option_help': "帮助",
        'option_stop': "停止服务",
        'option_test_daily': "测试每日提醒",
        'simple_instruction': "只需输入数字选择功能！",
        'invalid_choice': "❌ 无效选择。请输入数字",
        'setup_step1_title': "📍 *第1步/共3步：您的位置*",
        'setup_step1_desc': "请输入您的邮编（例如：SW1A 1AA）：",
        'setup_step1_purpose': "💡 *为什么？* 这帮助我找到您附近的医院并计算旅行距离。",
        'setup_step2_title': "🏥 *第2步/共3步：医疗专科*",
        'setup_step2_desc': "您需要哪个医疗专科？您可以：",
        'setup_step2_options': "• 输入下面列表中的数字（1-20）\n• 用英文或中文输入专科名称",
        'setup_step3_title': "⚙️ *第3步/共3步：提醒偏好*",
        'setup_step3_desc': "设置您的提醒偏好：",
        'setup_step3_format': "格式：`[周数] [距离]` 或 `默认`",
        'setup_step3_examples': "示例：\n• `2周 30公里` - 当≤2周时提醒，30公里内\n• `默认` - 使用系统默认值（8周，25公里）",
        'setup_step3_purpose': "💡 *为什么设置这些？*\n• **周数**：当等候时间下降时获得通知\n• **距离**：找到您附近方便的位置",
        'postcode_invalid': "❌ 邮编格式无效。请输入有效的英国邮编（例如：SW1A 1AA）。",
        'specialty_invalid': "❌ 专科无效。请选择数字（1-20）或输入有效的专科名称。",
        'preferences_invalid': "❌ 格式无效。请使用：`[周数] [距离]` 或 `默认`\n示例：`2周 30公里`",
        'setup_complete': "🎉 *设置完成！*",
        'monitoring_started': "✅ 已开始监控您的偏好",
        'status_title': "📊 *您的当前状态*",
        'no_preferences': "❌ 未设置偏好。请先运行设置。",
        'recent_alerts_title': "📬 *最近提醒*",
        'no_recent_alerts': "📭 未找到最近的提醒。",
        'trends_title': "📈 *等候时间趋势*",
        'help_title': "❓ *帮助与支持*",
        'unsubscribe_confirm': "❌ *服务已停止*\n\n您已取消订阅所有提醒。",
        'error_occurred': "❌ *出现了一些问题*\n\n请稍后再试，或者：\n\n*1* - 返回主菜单\n*help* - 查看帮助\n\n如果问题持续，请联系技术支持。"
    },
    'hi': {
        'language_selection': """🌍 *NHS इंटेलिजेंट अलर्ट सिस्टम में आपका स्वागत है*

कृपया अपनी पसंदीदा भाषा चुनें:

1️⃣ 🇬🇧 English
2️⃣ 🇨🇳 中文 (Chinese)
3️⃣ 🇮🇳 हिन्दी (Hindi)
4️⃣ 🇵🇰 اردو (Urdu)
5️⃣ 🇧🇩 বাংলা (Bengali)
6️⃣ 🇸🇦 العربية (Arabic)
7️⃣ 🇵🇱 Polski (Polish)
8️⃣ 🇫🇷 Français (French)
9️⃣ 🇪🇸 Español (Spanish)
🔟 🇵🇹 Português (Portuguese)

*बस अपनी पसंदीदा भाषा का नंबर (1-10) दर्ज करें।*""",
        'language_confirmed': "✅ भाषा हिंदी में सेट कर दी गई है। चलिए शुरू करते हैं!",
        'welcome_title': "🏥 *NHS इंटेलिजेंट अलर्ट सिस्टम*",
        'welcome_subtitle': "आपका व्यक्तिगत स्वास्थ्य सेवा प्रतीक्षा समय सहायक",
        'why_need_me': "🤔 *आपको मेरी आवश्यकता क्यों है?*",
        'benefit_1': "📊 *24/7 निगरानी* - मैं NHS प्रतीक्षा समय को लगातार ट्रैक करता हूं",
        'benefit_2': "⚡ *तत्काल सूचनाएं* - जब समय आपकी सीमा से कम हो जाए तो अलर्ट पाएं",
        'benefit_3': "🔍 *तेज़ विकल्प खोजें* - मैं आस-पास के छोटे विकल्प सुझाऊंगा",
        'benefit_4': "💡 *स्मार्ट अंतर्दृष्टि* - ट्रेंड विश्लेषण और भविष्यवाणियां प्राप्त करें",
        'get_started': "🚀 *शुरू करने के लिए तैयार हैं?*",
        'new_user_options': "नए उपयोगकर्ताओं के लिए:",
        'existing_user_options': "मौजूदा उपयोगकर्ताओं के लिए:",
        'option_setup': "सेटअप शुरू करें",
        'option_guide': "उपयोग गाइड",
        'option_features': "फीचर अवलोकन",
        'option_status': "स्थिति देखें",
        'option_alerts': "हाल की अलर्ट",
        'option_trends': "प्रतीक्षा रुझान",
        'option_reset': "सेटिंग्स रीसेट करें",
        'option_help': "सहायता",
        'option_stop': "सेवा बंद करें",
        'option_test_daily': "दैनिक अलर्ट का परीक्षण करें",
        'simple_instruction': "बस कार्य चुनने के लिए एक नंबर दर्ज करें!",
        'invalid_choice': "❌ गलत विकल्प। कृपया इसके बीच एक नंबर दर्ज करें",
        'setup_complete': "🎉 *सेटअप पूरा!*",
        'monitoring_started': "✅ आपकी प्राथमिकताओं के लिए निगरानी शुरू की गई",
        'status_title': "📊 *आपकी वर्तमान स्थिति*",
        'no_preferences': "❌ कोई प्राथमिकताएं सेट नहीं हैं। कृपया पहले सेटअप चलाएं।",
        'recent_alerts_title': "📬 *हाल की अलर्ट*",
        'no_recent_alerts': "📭 कोई हाल की अलर्ट नहीं मिली।",
        'trends_title': "📈 *प्रतीक्षा समय रुझान*",
        'help_title': "❓ *सहायता और समर्थन*",
        'unsubscribe_confirm': "❌ *सेवा बंद*\n\nआपने सभी अलर्ट से अनसब्स्क्राइब कर दिया है।",
        'error_occurred': "❌ *कुछ गलत हुआ*\n\nकृपया बाद में पुनः प्रयास करें, या:\n\n*1* - मुख्य मेनू पर वापस जाएं\n*help* - सहायता देखें\n\nयदि समस्या बनी रहती है, तो कृपया सहायता से संपर्क करें।"
    },
    'ur': {
        'language_selection': """🌍 *NHS انٹیلیجنٹ الرٹ سسٹم میں خوش آمدید*

براہ کرم اپنی پسندیدہ زبان منتخب کریں:

1️⃣ 🇬🇧 English
2️⃣ 🇨🇳 中文 (Chinese)
3️⃣ 🇮🇳 हिन्दी (Hindi)
4️⃣ 🇵🇰 اردو (Urdu)
5️⃣ 🇧🇩 বাংলা (Bengali)
6️⃣ 🇸🇦 العربية (Arabic)
7️⃣ 🇵🇱 Polski (Polish)
8️⃣ 🇫🇷 Français (French)
9️⃣ 🇪🇸 Español (Spanish)
🔟 🇵🇹 Português (Portuguese)

*صرف اپنی پسندیدہ زبان کا نمبر (1-10) داخل کریں۔*""",
        'language_confirmed': "✅ زبان اردو میں سیٹ کر دی گئی ہے۔ آئیے شروع کرتے ہیں!",
        'welcome_title': "🏥 *NHS انٹیلیجنٹ الرٹ سسٹم*",
        'welcome_subtitle': "آپ کا ذاتی صحت کی دیکھ بھال انتظار کا وقت معاون",
        'why_need_me': "🤔 *آپ کو میری ضرورت کیوں ہے؟*",
        'benefit_1': "📊 *24/7 نگرانی* - میں NHS انتظار کے وقت کو مسلسل ٹریک کرتا ہوں",
        'benefit_2': "⚡ *فوری اطلاعات* - جب وقت آپ کی حد سے کم ہو جائے تو الرٹ حاصل کریں",
        'benefit_3': "🔍 *تیز آپشنز تلاش کریں* - میں آس پاس کے چھوٹے متبادل تجویز کروں گا",
        'benefit_4': "💡 *اسمارٹ بصیرت* - رجحان کا تجزیہ اور پیشین گوئیاں حاصل کریں",
        'get_started': "🚀 *شروع کرنے کے لیے تیار ہیں؟*",
        'new_user_options': "نئے صارفین کے لیے:",
        'existing_user_options': "موجودہ صارفین کے لیے:",
        'option_setup': "سیٹ اپ شروع کریں",
        'option_guide': "استعمال کی رہنمائی",
        'option_features': "فیچر جائزہ",
        'option_status': "حالت دیکھیں",
        'option_alerts': "حالیہ الرٹس",
        'option_trends': "انتظار کے رجحانات",
        'option_reset': "سیٹنگز ری سیٹ کریں",
        'option_help': "مدد",
        'option_stop': "سروس بند کریں",
        'option_test_daily': "یومیہ الرٹ ٹیسٹ کریں",
        'simple_instruction': "فنکشن منتخب کرنے کے لیے صرف ایک نمبر داخل کریں!",
        'invalid_choice': "❌ غلط انتخاب۔ براہ کرم اس کے درمیان ایک نمبر داخل کریں",
        'setup_complete': "🎉 *سیٹ اپ مکمل!*",
        'monitoring_started': "✅ آپ کی ترجیحات کے لیے نگرانی شروع کی گئی",
        'status_title': "📊 *آپ کی موجودہ حالت*",
        'no_preferences': "❌ کوئی ترجیحات سیٹ نہیں ہیں۔ براہ کرم پہلے سیٹ اپ چلائیں۔",
        'recent_alerts_title': "📬 *حالیہ الرٹس*",
        'no_recent_alerts': "📭 کوئی حالیہ الرٹس نہیں ملے۔",
        'trends_title': "📈 *انتظار کے وقت کے رجحانات*",
        'help_title': "❓ *مدد اور سپورٹ*",
        'unsubscribe_confirm': "❌ *سروس بند*\n\nآپ نے تمام الرٹس سے ان سبسکرائب کر دیا ہے۔",
        'error_occurred': "❌ *کچھ غلط ہوا*\n\nبراہ کرم بعد میں دوبارہ کوشش کریں، یا:\n\n*1* - مین مینو پر واپس جائیں\n*help* - مدد دیکھیں\n\nاگر مسئلہ برقرار رہے تو براہ کرم سپورٹ سے رابطہ کریں۔"
    },
    'bn': {
        'language_selection': """🌍 *NHS ইন্টেলিজেন্ট অ্যালার্ট সিস্টেমে স্বাগতম*

দয়া করে আপনার পছন্দের ভাষা নির্বাচন করুন:

1️⃣ 🇬🇧 English
2️⃣ 🇨🇳 中文 (Chinese)
3️⃣ 🇮🇳 हिन्दी (Hindi)
4️⃣ 🇵🇰 اردو (Urdu)
5️⃣ 🇧🇩 বাংলা (Bengali)
6️⃣ 🇸🇦 العربية (Arabic)
7️⃣ 🇵🇱 Polski (Polish)
8️⃣ 🇫🇷 Français (French)
9️⃣ 🇪🇸 Español (Spanish)
🔟 🇵🇹 Português (Portuguese)

*শুধুমাত্র আপনার পছন্দের ভাষার নম্বর (1-10) লিখুন।*""",
        'language_confirmed': "✅ ভাষা বাংলায় সেট করা হয়েছে। চলুন শুরু করি!",
        'welcome_title': "🏥 *NHS ইন্টেলিজেন্ট অ্যালার্ট সিস্টেম*",
        'welcome_subtitle': "আপনার ব্যক্তিগত স্বাস্থ্যসেবা অপেক্ষার সময় সহায়ক",
        'why_need_me': "🤔 *আপনার আমার প্রয়োজন কেন?*",
        'benefit_1': "📊 *24/7 পর্যবেক্ষণ* - আমি NHS অপেক্ষার সময় ক্রমাগত ট্র্যাক করি",
        'benefit_2': "⚡ *তাৎক্ষণিক বিজ্ঞপ্তি* - যখন সময় আপনার সীমার নিচে নেমে যায় তখন অ্যালার্ট পান",
        'benefit_3': "🔍 *দ্রুত বিকল্প খুঁজুন* - আমি কাছাকাছি ছোট বিকল্প সুপারিশ করব",
        'benefit_4': "💡 *স্মার্ট অন্তর্দৃষ্টি* - ট্রেন্ড বিশ্লেষণ এবং পূর্বাভাস পান",
        'get_started': "🚀 *শুরু করার জন্য প্রস্তুত?*",
        'new_user_options': "নতুন ব্যবহারকারীদের জন্য:",
        'existing_user_options': "বিদ্যমান ব্যবহারকারীদের জন্য:",
        'option_setup': "সেটআপ শুরু করুন",
        'option_guide': "ব্যবহারের গাইড",
        'option_features': "বৈশিষ্ট্য ওভারভিউ",
        'option_status': "অবস্থা দেখুন",
        'option_alerts': "সাম্প্রতিক অ্যালার্ট",
        'option_trends': "অপেক্ষার প্রবণতা",
        'option_reset': "সেটিংস রিসেট করুন",
        'option_help': "সাহায্য",
        'option_stop': "সেবা বন্ধ করুন",
        'option_test_daily': "দৈনিক সতর্কতা পরীক্ষা করুন",
        'simple_instruction': "কার্যকারিতা নির্বাচন করতে শুধু একটি নম্বর প্রবেশ করান!",
        'invalid_choice': "❌ ভুল পছন্দ। দয়া করে এর মধ্যে একটি নম্বর লিখুন",
        'setup_complete': "🎉 *সেটআপ সম্পূর্ণ!*",
        'monitoring_started': "✅ আপনার পছন্দের জন্য পর্যবেক্ষণ শুরু হয়েছে",
        'status_title': "📊 *আপনার বর্তমান অবস্থা*",
        'no_preferences': "❌ কোন পছন্দ সেট করা নেই। দয়া করে প্রথমে সেটআপ চালান।",
        'recent_alerts_title': "📬 *সাম্প্রতিক অ্যালার্ট*",
        'no_recent_alerts': "📭 কোন সাম্প্রতিক অ্যালার্ট পাওয়া যায়নি।",
        'trends_title': "📈 *অপেক্ষার সময়ের প্রবণতা*",
        'help_title': "❓ *সাহায্য এবং সহায়তা*",
        'unsubscribe_confirm': "❌ *সেবা বন্ধ*\n\nআপনি সব অ্যালার্ট থেকে আনসাবস্ক্রাইব করেছেন।",
        'error_occurred': "❌ *কিছু ভুল হয়েছে*\n\nদয়া করে পরে আবার চেষ্টা করুন, অথবা:\n\n*1* - মূল মেনুতে ফিরে যান\n*help* - সাহায্য দেখুন\n\nযদি সমস্যা অব্যাহত থাকে, দয়া করে সাহায্যের সাথে যোগাযোগ করুন।"
    },
    'ar': {
        'language_selection': """🌍 *مرحباً بكم في نظام التنبيهات الذكي لـ NHS*

يرجى اختيار لغتك المفضلة:

1️⃣ 🇬🇧 English
2️⃣ 🇨🇳 中文 (Chinese)
3️⃣ 🇮🇳 हिन्दी (Hindi)
4️⃣ 🇵🇰 اردو (Urdu)
5️⃣ 🇧🇩 বাংলা (Bengali)
6️⃣ 🇸🇦 العربية (Arabic)
7️⃣ 🇵🇱 Polski (Polish)
8️⃣ 🇫🇷 Français (French)
9️⃣ 🇪🇸 Español (Spanish)
🔟 🇵🇹 Português (Portuguese)

*فقط أدخل رقم لغتك المفضلة (1-10).*""",
        'language_confirmed': "✅ تم تعيين اللغة إلى العربية. لنبدأ!",
        'welcome_title': "🏥 *نظام التنبيهات الذكي لـ NHS*",
        'welcome_subtitle': "مساعدك الشخصي لأوقات انتظار الرعاية الصحية",
        'why_need_me': "🤔 *لماذا تحتاجني؟*",
        'benefit_1': "📊 *مراقبة 24/7* - أراقب أوقات انتظار NHS باستمرار",
        'benefit_2': "⚡ *إشعارات فورية* - احصل على تنبيهات عندما تنخفض الأوقات عن حدك",
        'benefit_3': "🔍 *العثور على خيارات أسرع* - سأقترح بدائل أقصر في المنطقة المجاورة",
        'benefit_4': "💡 *رؤى ذكية* - احصل على تحليل الاتجاهات والتنبؤات",
        'get_started': "🚀 *هل أنت مستعد للبدء؟*",
        'new_user_options': "للمستخدمين الجدد:",
        'existing_user_options': "للمستخدمين الحاليين:",
        'option_setup': "بدء الإعداد",
        'option_guide': "دليل الاستخدام",
        'option_features': "نظرة عامة على الميزات",
        'option_status': "عرض الحالة",
        'option_alerts': "التنبيهات الأخيرة",
        'option_trends': "اتجاهات الانتظار",
        'option_reset': "إعادة تعيين الإعدادات",
        'option_help': "المساعدة",
        'option_stop': "إيقاف الخدمة",
        'option_test_daily': "اختبار التنبيه اليومي",
        'simple_instruction': "ما عليك سوى إدخال رقم لاختيار وظيفة!",
        'invalid_choice': "❌ اختيار غير صحيح. يرجى إدخال رقم بين",
        'setup_complete': "🎉 *اكتمل الإعداد!*",
        'monitoring_started': "✅ بدأت المراقبة لتفضيلاتك",
        'status_title': "📊 *حالتك الحالية*",
        'no_preferences': "❌ لم يتم تعيين تفضيلات. يرجى تشغيل الإعداد أولاً.",
        'recent_alerts_title': "📬 *التنبيهات الأخيرة*",
        'no_recent_alerts': "📭 لم يتم العثور على تنبيهات حديثة.",
        'trends_title': "📈 *اتجاهات أوقات الانتظار*",
        'help_title': "❓ *المساعدة والدعم*",
        'unsubscribe_confirm': "❌ *توقف الخدمة*\n\nلقد ألغيت الاشتراك في جميع التنبيهات.",
        'error_occurred': "❌ *حدث خطأ ما*\n\nيرجى المحاولة مرة أخرى لاحقاً، أو:\n\n*1* - العودة إلى القائمة الرئيسية\n*help* - عرض المساعدة\n\nإذا استمرت المشكلة، يرجى الاتصال بالدعم."
    },
    'pl': {
        'language_selection': """🌍 *Witamy w NHS Intelligent Alert System*

Proszę wybrać preferowany język:

1️⃣ 🇬🇧 English
2️⃣ 🇨🇳 中文 (Chinese)
3️⃣ 🇮🇳 हिन्दी (Hindi)
4️⃣ 🇵🇰 اردو (Urdu)
5️⃣ 🇧🇩 বাংলা (Bengali)
6️⃣ 🇸🇦 العربية (Arabic)
7️⃣ 🇵🇱 Polski (Polish)
8️⃣ 🇫🇷 Français (French)
9️⃣ 🇪🇸 Español (Spanish)
🔟 🇵🇹 Português (Portuguese)

*Po prostu wprowadź numer preferowanego języka (1-10).*""",
        'language_confirmed': "✅ Język został ustawiony na polski. Zacznijmy!",
        'welcome_title': "🏥 *NHS Intelligent Alert System*",
        'welcome_subtitle': "Twój osobisty asystent czasów oczekiwania na opiekę zdrowotną",
        'why_need_me': "🤔 *Dlaczego mnie potrzebujesz?*",
        'benefit_1': "📊 *Monitorowanie 24/7* - Stale śledzę czasy oczekiwania NHS",
        'benefit_2': "⚡ *Natychmiastowe powiadomienia* - Otrzymuj alerty gdy czasy spadną poniżej Twojego progu",
        'benefit_3': "🔍 *Znajdź szybsze opcje* - Zaproponuję krótsze alternatywy w pobliżu",
        'benefit_4': "💡 *Inteligentne wglądy* - Otrzymuj analizę trendów i prognozy",
        'get_started': "🚀 *Gotowy na start?*",
        'new_user_options': "Dla nowych użytkowników:",
        'existing_user_options': "Dla istniejących użytkowników:",
        'option_setup': "Rozpocznij konfigurację",
        'option_guide': "Przewodnik użytkowania",
        'option_features': "Przegląd funkcji",
        'option_status': "Zobacz status",
        'option_alerts': "Ostatnie alerty",
        'option_trends': "Trendy oczekiwania",
        'option_reset': "Resetuj ustawienia",
        'option_help': "Pomoc",
        'option_stop': "Zatrzymaj usługę",
        'option_test_daily': "Testuj codzienne powiadomienie",
        'simple_instruction': "Po prostu wprowadź numer, aby wybrać funkcję!",
        'invalid_choice': "❌ Nieprawidłowy wybór. Proszę wprowadzić numer między",
        'setup_complete': "🎉 *Konfiguracja zakończona!*",
        'monitoring_started': "✅ Monitorowanie rozpoczęte dla Twoich preferencji",
        'status_title': "📊 *Twój obecny status*",
        'no_preferences': "❌ Brak ustawionych preferencji. Proszę najpierw uruchomić konfigurację.",
        'recent_alerts_title': "📬 *Ostatnie alerty*",
        'no_recent_alerts': "📭 Nie znaleziono ostatnich alertów.",
        'trends_title': "📈 *Trendy czasów oczekiwania*",
        'help_title': "❓ *Pomoc i wsparcie*",
        'unsubscribe_confirm': "❌ *Usługa zatrzymana*\n\nZrezygnowałeś z subskrypcji wszystkich alertów.",
        'error_occurred': "❌ *Coś poszło nie tak*\n\nProszę spróbować ponownie później, lub:\n\n*1* - Powrót do menu głównego\n*help* - Zobacz pomoc\n\nJeśli problem będzie się powtarzał, skontaktuj się z wsparciem."
    },
    'fr': {
        'language_selection': """🌍 *Bienvenue dans le NHS Intelligent Alert System*

Veuillez sélectionner votre langue préférée:

1️⃣ 🇬🇧 English
2️⃣ 🇨🇳 中文 (Chinese)
3️⃣ 🇮🇳 हिन्दी (Hindi)
4️⃣ 🇵🇰 اردو (Urdu)
5️⃣ 🇧🇩 বাংলা (Bengali)
6️⃣ 🇸🇦 العربية (Arabic)
7️⃣ 🇵🇱 Polski (Polish)
8️⃣ 🇫🇷 Français (French)
9️⃣ 🇪🇸 Español (Spanish)
🔟 🇵🇹 Português (Portuguese)

*Entrez simplement le numéro de votre langue préférée (1-10).*""",
        'language_confirmed': "✅ Langue définie en français. Commençons!",
        'welcome_title': "🏥 *NHS Intelligent Alert System*",
        'welcome_subtitle': "Votre assistant personnel des temps d'attente de soins de santé",
        'why_need_me': "🤔 *Pourquoi avez-vous besoin de moi?*",
        'benefit_1': "📊 *Surveillance 24/7* - Je surveille continuellement les temps d'attente NHS",
        'benefit_2': "⚡ *Notifications instantanées* - Recevez des alertes quand les temps descendent sous votre seuil",
        'benefit_3': "🔍 *Trouvez des options plus rapides* - Je suggérerai des alternatives plus courtes à proximité",
        'benefit_4': "💡 *Aperçus intelligents* - Recevez des analyses de tendances et des prédictions",
        'get_started': "🚀 *Prêt à commencer?*",
        'new_user_options': "Pour les nouveaux utilisateurs:",
        'existing_user_options': "Pour les utilisateurs existants:",
        'option_setup': "Commencer la configuration",
        'option_guide': "Guide d'utilisation",
        'option_features': "Aperçu des fonctionnalités",
        'option_status': "Voir le statut",
        'option_alerts': "Alertes récentes",
        'option_trends': "Tendances d'attente",
        'option_reset': "Réinitialiser les paramètres",
        'option_help': "Aide",
        'option_stop': "Arrêter le service",
        'option_test_daily': "Tester l'alerte quotidienne",
        'simple_instruction': "Entrez simplement un numéro pour sélectionner une fonction!",
        'invalid_choice': "❌ Choix invalide. Veuillez entrer un numéro entre",
        'setup_complete': "🎉 *Configuration terminée!*",
        'monitoring_started': "✅ Surveillance commencée pour vos préférences",
        'status_title': "📊 *Votre statut actuel*",
        'no_preferences': "❌ Aucune préférence définie. Veuillez d'abord exécuter la configuration.",
        'recent_alerts_title': "📬 *Alertes récentes*",
        'no_recent_alerts': "📭 Aucune alerte récente trouvée.",
        'trends_title': "📈 *Tendances des temps d'attente*",
        'help_title': "❓ *Aide et support*",
        'unsubscribe_confirm': "❌ *Service arrêté*\n\nVous vous êtes désabonné de toutes les alertes.",
        'error_occurred': "❌ *Quelque chose s'est mal passé*\n\nVeuillez réessayer plus tard, ou:\n\n*1* - Retour au menu principal\n*help* - Voir l'aide\n\nSi le problème persiste, veuillez contacter le support."
    },
    'es': {
        'language_selection': """🌍 *Bienvenido al NHS Intelligent Alert System*

Por favor, seleccione su idioma preferido:

1️⃣ 🇬🇧 English
2️⃣ 🇨🇳 中文 (Chinese)
3️⃣ 🇮🇳 हिन्दी (Hindi)
4️⃣ 🇵🇰 اردو (Urdu)
5️⃣ 🇧🇩 বাংলা (Bengali)
6️⃣ 🇸🇦 العربية (Arabic)
7️⃣ 🇵🇱 Polski (Polish)
8️⃣ 🇫🇷 Français (French)
9️⃣ 🇪🇸 Español (Spanish)
🔟 🇵🇹 Português (Portuguese)

*Simplemente ingrese el número de su idioma preferido (1-10).*""",
        'language_confirmed': "✅ Idioma configurado en español. ¡Comencemos!",
        'welcome_title': "🏥 *NHS Intelligent Alert System*",
        'welcome_subtitle': "Su asistente personal de tiempos de espera de atención médica",
        'why_need_me': "🤔 *¿Por qué me necesita?*",
        'benefit_1': "📊 *Monitoreo 24/7* - Rastro continuamente los tiempos de espera del NHS",
        'benefit_2': "⚡ *Notificaciones instantáneas* - Reciba alertas cuando los tiempos caigan por debajo de su umbral",
        'benefit_3': "🔍 *Encuentre opciones más rápidas* - Sugeriré alternativas más cortas cerca",
        'benefit_4': "💡 *Perspectivas inteligentes* - Reciba análisis de tendencias y predicciones",
        'get_started': "🚀 *¿Listo para empezar?*",
        'new_user_options': "Para nuevos usuarios:",
        'existing_user_options': "Para usuarios existentes:",
        'option_setup': "Iniciar configuración",
        'option_guide': "Guía de uso",
        'option_features': "Resumen de características",
        'option_status': "Ver estado",
        'option_alerts': "Alertas recientes",
        'option_trends': "Tendencias de espera",
        'option_reset': "Resetear configuración",
        'option_help': "Ayuda",
        'option_stop': "Detener servicio",
        'option_test_daily': "Probar alerta diaria",
        'simple_instruction': "¡Simplemente ingresa un número para seleccionar una función!",
        'invalid_choice': "❌ Opción inválida. Por favor ingrese un número entre",
        'setup_complete': "🎉 *¡Configuración completa!*",
        'monitoring_started': "✅ Monitoreo iniciado para sus preferencias",
        'status_title': "📊 *Su estado actual*",
        'no_preferences': "❌ No hay preferencias configuradas. Por favor ejecute la configuración primero.",
        'recent_alerts_title': "📬 *Alertas recientes*",
        'no_recent_alerts': "📭 No se encontraron alertas recientes.",
        'trends_title': "📈 *Tendencias de tiempos de espera*",
        'help_title': "❓ *Ayuda y soporte*",
        'unsubscribe_confirm': "❌ *Servicio detenido*\n\nSe ha desuscrito de todas las alertas.",
        'error_occurred': "❌ *Algo salió mal*\n\nPor favor intente nuevamente más tarde, o:\n\n*1* - Volver al menú principal\n*help* - Ver ayuda\n\nSi el problema persiste, por favor contacte soporte."
    },
    'pt': {
        'language_selection': """🌍 *Bem-vindo ao NHS Intelligent Alert System*

Por favor, selecione seu idioma preferido:

1️⃣ 🇬🇧 English
2️⃣ 🇨🇳 中文 (Chinese)
3️⃣ 🇮🇳 हिन्दी (Hindi)
4️⃣ 🇵🇰 اردو (Urdu)
5️⃣ 🇧🇩 বাংলা (Bengali)
6️⃣ 🇸🇦 العربية (Arabic)
7️⃣ 🇵🇱 Polski (Polish)
8️⃣ 🇫🇷 Français (French)
9️⃣ 🇪🇸 Español (Spanish)
🔟 🇵🇹 Português (Portuguese)

*Simplesmente digite o número do seu idioma preferido (1-10).*""",
        'language_confirmed': "✅ Idioma definido para português. Vamos começar!",
        'welcome_title': "🏥 *NHS Intelligent Alert System*",
        'welcome_subtitle': "Seu assistente pessoal de tempos de espera de cuidados de saúde",
        'why_need_me': "🤔 *Por que você precisa de mim?*",
        'benefit_1': "📊 *Monitoramento 24/7* - Eu rastreio continuamente os tempos de espera do NHS",
        'benefit_2': "⚡ *Notificações instantâneas* - Receba alertas quando os tempos caírem abaixo do seu limite",
        'benefit_3': "🔍 *Encontre opções mais rápidas* - Eu sugerirei alternativas mais curtas nas proximidades",
        'benefit_4': "💡 *Insights inteligentes* - Receba análise de tendências e previsões",
        'get_started': "🚀 *Pronto para começar?*",
        'new_user_options': "Para novos usuários:",
        'existing_user_options': "Para usuários existentes:",
        'option_setup': "Iniciar configuração",
        'option_guide': "Guia de uso",
        'option_features': "Visão geral dos recursos",
        'option_status': "Ver status",
        'option_alerts': "Alertas recentes",
        'option_trends': "Tendências de espera",
        'option_reset': "Redefinir configurações",
        'option_help': "Ajuda",
        'option_stop': "Parar serviço",
        'option_test_daily': "Testar alerta diário",
        'simple_instruction': "Simplesmente digite um número para selecionar uma função!"
    }
}

def get_language_text(lang_code: str, key: str, default_lang: str = 'en') -> str:
    """获取指定语言的文本"""
    if lang_code in LANGUAGE_TEXTS and key in LANGUAGE_TEXTS[lang_code]:
        return LANGUAGE_TEXTS[lang_code][key]
    elif default_lang in LANGUAGE_TEXTS and key in LANGUAGE_TEXTS[default_lang]:
        return LANGUAGE_TEXTS[default_lang][key]
    else:
        return f"[Missing text: {key}]"

def get_language_info(choice: str) -> dict:
    """获取语言信息"""
    return SUPPORTED_LANGUAGES.get(choice, SUPPORTED_LANGUAGES['1']) 