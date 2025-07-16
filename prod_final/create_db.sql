-- NHS Intelligent Alert System - SQLite Database Schema
-- Compatible with current system implementation

-- Main NHS RTT Data Table
CREATE TABLE IF NOT EXISTS nhs_rtt_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    period TEXT NOT NULL,
    org_code TEXT NOT NULL,
    org_name TEXT NOT NULL,
    specialty_code TEXT NOT NULL,
    specialty_name TEXT NOT NULL,
    treatment_function_code TEXT,
    treatment_function_name TEXT,
    waiting_time_weeks INTEGER,
    patient_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User Preferences Table (Enhanced with language support)
CREATE TABLE IF NOT EXISTS user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT UNIQUE NOT NULL,
    phone_number TEXT,
    postcode TEXT,
    specialties TEXT,
    specialty TEXT,
    threshold_weeks INTEGER,
    radius_km INTEGER,
    notification_types TEXT,
    language TEXT DEFAULT 'en',
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Alert History Table
CREATE TABLE IF NOT EXISTS alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    message TEXT NOT NULL,
    channel TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Alert Rules Table (for Intelligent Alert Engine)
CREATE TABLE IF NOT EXISTS alert_rules (
    rule_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    condition_type TEXT NOT NULL,
    parameters TEXT NOT NULL,
    priority INTEGER DEFAULT 1,
    frequency_hours INTEGER DEFAULT 24,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Alert Events Table
CREATE TABLE IF NOT EXISTS alert_events (
    event_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    data TEXT NOT NULL,
    priority INTEGER DEFAULT 1,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP
);

-- NHS Data History Table
CREATE TABLE IF NOT EXISTS nhs_data_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_date DATE NOT NULL,
    org_code TEXT NOT NULL,
    specialty_code TEXT NOT NULL,
    avg_waiting_weeks REAL,
    total_patients INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User Alert History Table
CREATE TABLE IF NOT EXISTS user_alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    last_sent TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- GP Practices Table
CREATE TABLE IF NOT EXISTS gp_practices (
    practice_code TEXT PRIMARY KEY,
    practice_name TEXT NOT NULL,
    address TEXT,
    postcode TEXT,
    phone TEXT,
    website TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- GP Slots Table
CREATE TABLE IF NOT EXISTS gp_slots (
    slot_id TEXT PRIMARY KEY,
    practice_code TEXT NOT NULL,
    practice_name TEXT NOT NULL,
    doctor_name TEXT,
    specialty TEXT,
    appointment_datetime TIMESTAMP NOT NULL,
    duration_minutes INTEGER DEFAULT 15,
    appointment_type TEXT DEFAULT 'routine',
    availability_status TEXT DEFAULT 'available',
    booking_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (practice_code) REFERENCES gp_practices(practice_code)
);

-- Slot Alerts Table
CREATE TABLE IF NOT EXISTS slot_alerts (
    alert_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    slot_id TEXT NOT NULL,
    practice_code TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    priority INTEGER DEFAULT 1,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP,
    FOREIGN KEY (slot_id) REFERENCES gp_slots(slot_id),
    FOREIGN KEY (practice_code) REFERENCES gp_practices(practice_code)
);

-- User GP Preferences Table
CREATE TABLE IF NOT EXISTS user_gp_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    practice_codes TEXT,
    preferred_times TEXT,
    appointment_types TEXT,
    max_travel_minutes INTEGER DEFAULT 30,
    notification_enabled BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Slot Monitor Log Table
CREATE TABLE IF NOT EXISTS slot_monitor_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    practice_code TEXT NOT NULL,
    slots_found INTEGER DEFAULT 0,
    alerts_generated INTEGER DEFAULT 0,
    check_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'success',
    error_message TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_nhs_rtt_period ON nhs_rtt_data(period);
CREATE INDEX IF NOT EXISTS idx_nhs_rtt_org_code ON nhs_rtt_data(org_code);
CREATE INDEX IF NOT EXISTS idx_nhs_rtt_specialty ON nhs_rtt_data(specialty_code);
CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_user_preferences_language ON user_preferences(language);
CREATE INDEX IF NOT EXISTS idx_alert_history_user_id ON alert_history(user_id);
CREATE INDEX IF NOT EXISTS idx_alert_events_user_id ON alert_events(user_id);
CREATE INDEX IF NOT EXISTS idx_alert_events_rule_id ON alert_events(rule_id);
CREATE INDEX IF NOT EXISTS idx_nhs_data_history_date ON nhs_data_history(data_date);
CREATE INDEX IF NOT EXISTS idx_gp_slots_practice_code ON gp_slots(practice_code);
CREATE INDEX IF NOT EXISTS idx_gp_slots_datetime ON gp_slots(appointment_datetime); 