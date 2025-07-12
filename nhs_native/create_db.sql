CREATE DATABASE nhs;
\c nhs
CREATE TABLE IF NOT EXISTS rtt_provider_raw(
    provider_code          text,
    provider_name          text,
    specialty_code         text,
    specialty              text,
    period                 date,
    waiting_less_18_weeks  int,
    waiting_over_52_weeks  int,
    PRIMARY KEY(provider_code, specialty_code, period)
);
