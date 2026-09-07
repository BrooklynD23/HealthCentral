"""
Platform-specific notification delivery.

Provides abstract interface for notifications with implementations for:
- Windows Toast Notifications (primary)
- Cross-platform via desktop-notifier (prototype)
- Cross-platform fallback via plyer

Phase 3: Smart Notifications - Platform Delivery Component
"""

import logging
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class NotificationPlatform(str, Enum):
    """Supported notification platforms."""
    WINDOWS_TOAST = "windows_toast"
    DESKTOP_NOTIFIER = "desktop_notifier"
    PLYER = "plyer"
    IN_APP = "in_app"
    MOCK = "mock"  # For testing


class DeliveryStatus(str, Enum):
    """Notification delivery status."""
    SENT = "sent"
    DELIVERED = "delivered"
    CLICKED = "clicked"
    DISMISSED = "dismissed"
    FAILED = "failed"
    PERMISSION_DENIED = "permission_denied"


@dataclass
class NotificationPayload:
    """Payload for a notification."""
    id: str
    title: str
    body: str
    medication_id: str
    schedule_id: Optional[str] = None
    action_text: str = "Mark as taken"
    icon_path: Optional[str] = None
    timeout_seconds: int = 30
    silent: bool = False


@dataclass
class DeliveryResult:
    """Result of notification delivery attempt."""
    success: bool
    status: DeliveryStatus
    platform: NotificationPlatform
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None
    native_id: Optional[str] = None  # Platform-specific ID


class NotificationProvider(ABC):
    """Abstract base class for notification providers."""

    @property
    @abstractmethod
    def platform(self) -> NotificationPlatform:
        """Return the platform type."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available on the current system."""
        pass

    @abstractmethod
    async def send(self, payload: NotificationPayload) -> DeliveryResult:
        """
        Send a notification.

        Args:
            payload: Notification content and metadata

        Returns:
            DeliveryResult with status
        """
        pass

    @abstractmethod
    async def request_permission(self) -> bool:
        """
        Request notification permissions if needed.

        Returns:
            True if permissions granted
        """
        pass


class WindowsToastProvider(NotificationProvider):
    """
    Windows Toast notification provider.

    Uses Windows SDK for native toast notifications with action buttons.
    Falls back to basic toast if SDK not available.
    """

    def __init__(self):
        self._toast_module = None
        self._initialized = False
        self._app_id = "Asclexis.MedicationReminder"

    @property
    def platform(self) -> NotificationPlatform:
        return NotificationPlatform.WINDOWS_TOAST

    def is_available(self) -> bool:
        """Check if Windows toast notifications are available."""
        if sys.platform != "win32":
            return False

        # Try to import Windows SDK
        try:
            from winsdk.windows.ui.notifications import (
                ToastNotificationManager,
                ToastNotification,
            )
            from winsdk.windows.data.xml.dom import XmlDocument
            self._toast_module = {
                "manager": ToastNotificationManager,
                "notification": ToastNotification,
                "xml": XmlDocument,
            }
            self._initialized = True
            return True
        except ImportError:
            logger.debug("Windows SDK not available, will use fallback")
            return False

    async def send(self, payload: NotificationPayload) -> DeliveryResult:
        """Send Windows toast notification."""
        if not self.is_available():
            return DeliveryResult(
                success=False,
                status=DeliveryStatus.FAILED,
                platform=self.platform,
                error_message="Windows SDK not available",
            )

        try:
            # Build toast XML
            toast_xml = self._build_toast_xml(payload)

            # Create and send notification
            manager = self._toast_module["manager"]
            xml_doc = self._toast_module["xml"]()
            xml_doc.load_xml(toast_xml)

            notification = self._toast_module["notification"](xml_doc)

            # Get notifier and show
            notifier = manager.create_toast_notifier(self._app_id)
            notifier.show(notification)

            return DeliveryResult(
                success=True,
                status=DeliveryStatus.SENT,
                platform=self.platform,
                delivered_at=datetime.utcnow(),
                native_id=payload.id,
            )

        except Exception as e:
            logger.error(f"Failed to send Windows toast: {e}")
            return DeliveryResult(
                success=False,
                status=DeliveryStatus.FAILED,
                platform=self.platform,
                error_message=str(e),
            )

    def _build_toast_xml(self, payload: NotificationPayload) -> str:
        """Build Windows toast notification XML."""
        # Escape XML special characters
        title = self._escape_xml(payload.title)
        body = self._escape_xml(payload.body)
        action_text = self._escape_xml(payload.action_text)

        # Build XML with action button
        return f"""
<toast launch="action=open&amp;medicationId={payload.medication_id}">
    <visual>
        <binding template="ToastGeneric">
            <text>{title}</text>
            <text>{body}</text>
        </binding>
    </visual>
    <actions>
        <action
            content="{action_text}"
            arguments="action=taken&amp;medicationId={payload.medication_id}&amp;scheduleId={payload.schedule_id or ''}"
            activationType="foreground"/>
        <action
            content="Snooze"
            arguments="action=snooze&amp;medicationId={payload.medication_id}"
            activationType="background"/>
    </actions>
    <audio silent="{str(payload.silent).lower()}"/>
</toast>
"""

    def _escape_xml(self, text: str) -> str:
        """Escape XML special characters."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    async def request_permission(self) -> bool:
        """Windows doesn't require explicit permission request."""
        return self.is_available()


class PlyerProvider(NotificationProvider):
    """
    Cross-platform notification provider using plyer.

    Works on Windows, macOS, Linux with native notification systems.
    Simpler than Windows SDK but less feature-rich.
    """

    def __init__(self):
        self._plyer = None
        self._initialized = False

    @property
    def platform(self) -> NotificationPlatform:
        return NotificationPlatform.PLYER

    def is_available(self) -> bool:
        """Check if plyer is available."""
        try:
            from plyer import notification
            self._plyer = notification
            self._initialized = True
            return True
        except ImportError:
            logger.debug("plyer not installed")
            return False

    async def send(self, payload: NotificationPayload) -> DeliveryResult:
        """Send notification via plyer."""
        if not self.is_available():
            return DeliveryResult(
                success=False,
                status=DeliveryStatus.FAILED,
                platform=self.platform,
                error_message="plyer not available",
            )

        try:
            self._plyer.notify(
                title=payload.title,
                message=payload.body,
                app_name="Asclexis",
                app_icon=payload.icon_path,
                timeout=payload.timeout_seconds,
            )

            return DeliveryResult(
                success=True,
                status=DeliveryStatus.SENT,
                platform=self.platform,
                delivered_at=datetime.utcnow(),
                native_id=payload.id,
            )

        except Exception as e:
            logger.error(f"Failed to send plyer notification: {e}")
            return DeliveryResult(
                success=False,
                status=DeliveryStatus.FAILED,
                platform=self.platform,
                error_message=str(e),
            )

    async def request_permission(self) -> bool:
        """plyer handles permissions automatically."""
        return self.is_available()


class DesktopNotifierProvider(NotificationProvider):
    """
    Cross-platform notification provider using the desktop-notifier library.

    Uses native notification centers via DBus (Linux), UNUserNotificationCenter
    (macOS), and WinRT (Windows). Async-native, so it integrates directly with
    this module's async send() interface without a thread hop. Prototype
    provider offered alongside plyer/winsdk (not a replacement).
    """

    def __init__(self):
        self._notifier = None
        self._initialized = False

    @property
    def platform(self) -> NotificationPlatform:
        return NotificationPlatform.DESKTOP_NOTIFIER

    def is_available(self) -> bool:
        """Check if desktop-notifier is installed."""
        try:
            from desktop_notifier import DesktopNotifier
            if self._notifier is None:
                self._notifier = DesktopNotifier(app_name="Asclexis")
            self._initialized = True
            return True
        except ImportError:
            logger.debug("desktop-notifier not installed")
            return False
        except Exception as e:
            # Constructing DesktopNotifier can fail on systems lacking the
            # required desktop services/config (e.g. no DBus on a headless
            # host). Treat any such failure as "unavailable" so the provider
            # degrades gracefully and NotificationService initialization is
            # not broken.
            logger.debug(f"desktop-notifier unavailable: {e}")
            return False

    async def send(self, payload: NotificationPayload) -> DeliveryResult:
        """Send notification via desktop-notifier."""
        if not self.is_available():
            return DeliveryResult(
                success=False,
                status=DeliveryStatus.FAILED,
                platform=self.platform,
                error_message="desktop-notifier not available",
            )

        try:
            native_id = await self._notifier.send(
                title=payload.title,
                message=payload.body,
                timeout=payload.timeout_seconds,
            )

            return DeliveryResult(
                success=True,
                status=DeliveryStatus.SENT,
                platform=self.platform,
                delivered_at=datetime.utcnow(),
                native_id=str(native_id) if native_id is not None else payload.id,
            )

        except Exception as e:
            logger.error(f"Failed to send desktop-notifier notification: {e}")
            return DeliveryResult(
                success=False,
                status=DeliveryStatus.FAILED,
                platform=self.platform,
                error_message=str(e),
            )

    async def request_permission(self) -> bool:
        """desktop-notifier requests permission automatically on first send."""
        return self.is_available()


class MockProvider(NotificationProvider):
    """Mock provider for testing."""

    def __init__(self):
        self.sent_notifications: list[NotificationPayload] = []
        self._should_fail = False
        self._on_send: Optional[Callable[[NotificationPayload], None]] = None

    @property
    def platform(self) -> NotificationPlatform:
        return NotificationPlatform.MOCK

    def is_available(self) -> bool:
        return True

    def set_should_fail(self, should_fail: bool):
        """Configure mock to fail on send."""
        self._should_fail = should_fail

    def set_on_send(self, callback: Callable[[NotificationPayload], None]):
        """Set callback when notification is sent."""
        self._on_send = callback

    async def send(self, payload: NotificationPayload) -> DeliveryResult:
        """Mock send that records notifications."""
        if self._should_fail:
            return DeliveryResult(
                success=False,
                status=DeliveryStatus.FAILED,
                platform=self.platform,
                error_message="Mock failure",
            )

        self.sent_notifications.append(payload)
        if self._on_send:
            self._on_send(payload)

        return DeliveryResult(
            success=True,
            status=DeliveryStatus.DELIVERED,
            platform=self.platform,
            delivered_at=datetime.utcnow(),
            native_id=payload.id,
        )

    async def request_permission(self) -> bool:
        return True

    def clear(self):
        """Clear recorded notifications."""
        self.sent_notifications.clear()


class NotificationService:
    """
    Unified notification service with provider fallback.

    Tries providers in order until one succeeds:
    1. Windows Toast (if on Windows)
    2. plyer (cross-platform)
    3. In-app fallback
    """

    def __init__(self, providers: Optional[list[NotificationProvider]] = None):
        """
        Initialize notification service.

        Args:
            providers: Optional list of providers (uses defaults if None)
        """
        if providers:
            self._providers = providers
        else:
            self._providers = self._create_default_providers()

        self._active_provider: Optional[NotificationProvider] = None

    def _create_default_providers(self) -> list[NotificationProvider]:
        """Create default provider chain based on platform."""
        providers = []

        # Windows gets toast provider first
        if sys.platform == "win32":
            providers.append(WindowsToastProvider())

        # desktop-notifier: cross-platform native notification centers
        # (DBus/UNUserNotificationCenter/WinRT), tried before plyer
        providers.append(DesktopNotifierProvider())

        # plyer as fallback for all platforms
        providers.append(PlyerProvider())

        return providers

    async def initialize(self) -> bool:
        """
        Initialize the notification service.

        Finds the first available provider and requests permissions.

        Returns:
            True if at least one provider is available
        """
        for provider in self._providers:
            if provider.is_available():
                has_permission = await provider.request_permission()
                if has_permission:
                    self._active_provider = provider
                    logger.info(
                        f"Notification service initialized with {provider.platform.value}"
                    )
                    return True

        logger.warning("No notification providers available")
        return False

    @property
    def active_platform(self) -> Optional[NotificationPlatform]:
        """Return the active notification platform."""
        return self._active_provider.platform if self._active_provider else None

    async def send(self, payload: NotificationPayload) -> DeliveryResult:
        """
        Send a notification using the active provider.

        Falls back through providers if primary fails.

        Args:
            payload: Notification content

        Returns:
            DeliveryResult from first successful provider
        """
        # Try active provider first
        if self._active_provider:
            result = await self._active_provider.send(payload)
            if result.success:
                return result

        # Try all providers as fallback
        last_error = "No providers available"
        for provider in self._providers:
            if not provider.is_available():
                continue

            result = await provider.send(payload)
            if result.success:
                # Update active provider
                self._active_provider = provider
                return result
            last_error = result.error_message or "Unknown error"

        return DeliveryResult(
            success=False,
            status=DeliveryStatus.FAILED,
            platform=NotificationPlatform.IN_APP,
            error_message=f"All providers failed: {last_error}",
        )

    async def send_batch(
        self, payloads: list[NotificationPayload]
    ) -> list[DeliveryResult]:
        """
        Send multiple notifications.

        Args:
            payloads: List of notification payloads

        Returns:
            List of delivery results
        """
        results = []
        for payload in payloads:
            result = await self.send(payload)
            results.append(result)
        return results


# Global instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get or create the global notification service."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service


async def initialize_notifications() -> bool:
    """Initialize the global notification service."""
    service = get_notification_service()
    return await service.initialize()
