from typing import Optional
import os
import logging

# Lazy import drivers to avoid unnecessary dependencies

def _import_whatsapp_service():
    try:
        from whatsapp_flow_service import WhatsAppFlowService  # type: ignore
        return WhatsAppFlowService
    except ImportError:
        return None


def _import_telegram_driver():
    try:
        from telegram_driver import TelegramDriver  # type: ignore
        return TelegramDriver
    except ImportError:
        return None


class NotificationManager:
    """Unified notification manager supporting multiple channels.

    The manager selects an underlying driver based on the NOTIFY_CHANNEL
    environment variable. All drivers must expose *send_alert_notification*
    with the same signature as WhatsAppFlowService for backward compatibility:

        send_alert_notification(user_phone: str, alert_type: str, alert_data: dict) -> bool
    """

    def __init__(self, default_channel: str = "whatsapp"):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.channel = os.getenv("NOTIFY_CHANNEL", default_channel).strip().lower()

        driver_cls = None
        if self.channel == "telegram":
            driver_cls = _import_telegram_driver()
        elif self.channel == "whatsapp":
            driver_cls = _import_whatsapp_service()
        elif self.channel == "sms":
            # defer import to avoid mandatory dependency
            try:
                from sms_driver import SMSDriver  # type: ignore
                driver_cls = SMSDriver
            except ImportError:
                driver_cls = None
        else:
            self.logger.warning(
                "Unknown NOTIFY_CHANNEL '%s', falling back to WhatsApp driver", self.channel
            )
            driver_cls = _import_whatsapp_service()
            self.channel = "whatsapp"

        if driver_cls is None:
            raise RuntimeError(
                f"Notification driver for channel '{self.channel}' is not available or failed to import."
            )

        # Some drivers require a config_manager parameter, but WhatsAppFlowService in the
        # existing codebase expects none when env vars are present. We try to instantiate
        # with zero args first, fallback to config_manager if necessary.
        try:
            self.driver = driver_cls()
        except TypeError:
            from business_framework.core.config_manager import ConfigManager  # fallback

            cfg = ConfigManager(environment=os.getenv("ENV", "prod"))
            self.driver = driver_cls(cfg)

        self.logger.info("NotificationManager initialized with channel '%s'", self.channel)

    # ------------------------------------------------------------------
    # Public API expected by IntelligentAlertEngine and other components
    # ------------------------------------------------------------------
    def send_alert_notification(self, user_phone: str, alert_type: str, alert_data: dict) -> bool:
        """Proxy method to the underlying driver."""
        if not hasattr(self.driver, "send_alert_notification"):
            self.logger.error("Underlying driver has no 'send_alert_notification' method")
            return False
        return self.driver.send_alert_notification(user_phone, alert_type, alert_data) 