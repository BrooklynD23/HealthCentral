"""
Tests for Phase 3 Smart Notifications modules.

Tests the message generator, platform notifications, and notification scheduler
components of the medication reminder system.
"""

import asyncio
import pytest
import sys
from datetime import datetime, time, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.message_generator import (
    MessageGenerator,
    MessageContext,
    GeneratedMessage,
    ReminderPriority,
    MessageTone,
    get_message_generator,
)
from modules.platform_notifications import (
    NotificationService,
    NotificationPayload,
    DeliveryResult,
    DeliveryStatus,
    NotificationPlatform,
    MockProvider,
    PlyerProvider,
    DesktopNotifierProvider,
    get_notification_service,
)
from modules.notification_scheduler import (
    NotificationScheduler,
    SchedulerState,
    ScheduleCheck,
    NotificationSettings,
    SchedulerConfig,
    get_notification_scheduler,
)


class TestMessageGenerator:
    """Tests for the MessageGenerator module."""

    def test_generate_initial_reminder(self):
        """Test generating an initial reminder message."""
        generator = MessageGenerator()

        context = MessageContext(
            medication_name="Metformin",
            schedule_label="morning",
            current_streak=5,
            longest_streak=10,
            priority=ReminderPriority.INITIAL,
            is_weekend=False,
            hour_of_day=8,
            previous_reminders_today=0,
        )

        message = generator.generate_reminder(context)

        assert isinstance(message, GeneratedMessage)
        assert message.priority == ReminderPriority.INITIAL
        assert message.tone == MessageTone.FRIENDLY
        assert "Metformin" in message.body
        assert len(message.title) > 0
        assert len(message.body) > 0

    def test_generate_nudge_reminder(self):
        """Test generating a gentle nudge reminder."""
        generator = MessageGenerator()

        context = MessageContext(
            medication_name="Aspirin",
            schedule_label="evening",
            current_streak=3,
            longest_streak=7,
            priority=ReminderPriority.GENTLE_NUDGE,
            is_weekend=False,
            hour_of_day=18,
            previous_reminders_today=1,
        )

        message = generator.generate_reminder(context)

        assert message.priority == ReminderPriority.GENTLE_NUDGE
        assert message.tone == MessageTone.SUPPORTIVE
        assert "Aspirin" in message.body

    def test_generate_alert_reminder(self):
        """Test generating an important alert reminder."""
        generator = MessageGenerator()

        context = MessageContext(
            medication_name="Blood Pressure Med",
            schedule_label="morning",
            current_streak=7,
            longest_streak=14,
            priority=ReminderPriority.IMPORTANT_ALERT,
            is_weekend=False,
            hour_of_day=11,
            previous_reminders_today=2,
        )

        message = generator.generate_reminder(context)

        assert message.priority == ReminderPriority.IMPORTANT_ALERT
        assert message.tone == MessageTone.CONCERNED
        # Should mention streak if user has one
        assert message.includes_streak or "streak" in message.body.lower()

    def test_streak_celebration_3_days(self):
        """Test 3-day streak celebration message."""
        generator = MessageGenerator()

        context = MessageContext(
            medication_name="Vitamin D",
            schedule_label="morning",
            current_streak=3,  # Exact milestone
            longest_streak=3,
            priority=ReminderPriority.INITIAL,
            is_weekend=False,
            hour_of_day=9,
            previous_reminders_today=0,
        )

        message = generator.generate_reminder(context)

        assert message.includes_streak
        # Should be a celebration message
        assert "3" in message.title or "3" in message.body

    def test_streak_celebration_7_days(self):
        """Test 7-day streak celebration message."""
        generator = MessageGenerator()

        context = MessageContext(
            medication_name="Omega-3",
            schedule_label="evening",
            current_streak=7,
            longest_streak=7,
            priority=ReminderPriority.INITIAL,
            is_weekend=True,
            hour_of_day=20,
            previous_reminders_today=0,
        )

        message = generator.generate_reminder(context)

        assert message.includes_streak
        # Should mention week or 7 days
        assert "7" in message.body or "week" in message.body.lower()

    def test_streak_celebration_30_days(self):
        """Test 30-day (1 month) streak celebration message."""
        generator = MessageGenerator()

        context = MessageContext(
            medication_name="Statin",
            schedule_label="bedtime",
            current_streak=30,
            longest_streak=30,
            priority=ReminderPriority.INITIAL,
            is_weekend=False,
            hour_of_day=22,
            previous_reminders_today=0,
        )

        message = generator.generate_reminder(context)

        assert message.includes_streak
        # Should mention month or 30 days
        assert "30" in message.body or "month" in message.body.lower()

    def test_no_celebration_for_non_milestone(self):
        """Test that non-milestone streaks don't trigger celebration."""
        generator = MessageGenerator()

        context = MessageContext(
            medication_name="Test Med",
            schedule_label="morning",
            current_streak=5,  # Not a milestone
            longest_streak=5,
            priority=ReminderPriority.INITIAL,
            is_weekend=False,
            hour_of_day=8,
            previous_reminders_today=0,
        )

        message = generator.generate_reminder(context)

        # Should be a regular reminder, not a celebration
        assert not message.includes_streak

    def test_time_based_message_selection(self):
        """Test that messages are appropriate for time of day."""
        generator = MessageGenerator()

        # Morning
        morning_context = MessageContext(
            medication_name="Med",
            schedule_label="custom",
            current_streak=0,
            longest_streak=0,
            priority=ReminderPriority.INITIAL,
            is_weekend=False,
            hour_of_day=7,
            previous_reminders_today=0,
        )
        morning_msg = generator.generate_reminder(morning_context)
        # Morning messages should exist and be friendly
        assert morning_msg.tone == MessageTone.FRIENDLY

        # Evening
        evening_context = MessageContext(
            medication_name="Med",
            schedule_label="custom",
            current_streak=0,
            longest_streak=0,
            priority=ReminderPriority.INITIAL,
            is_weekend=False,
            hour_of_day=19,
            previous_reminders_today=0,
        )
        evening_msg = generator.generate_reminder(evening_context)
        assert evening_msg.tone == MessageTone.FRIENDLY

    def test_missed_recovery_message(self):
        """Test generating recovery message after missed dose."""
        generator = MessageGenerator()

        # After a long streak broken
        message = generator.generate_missed_recovery(
            medication_name="Metformin",
            days_missed=1,
            previous_streak=14,
        )

        assert isinstance(message, GeneratedMessage)
        assert message.tone == MessageTone.SUPPORTIVE
        # Should mention previous streak
        assert "14" in message.body or "streak" in message.body.lower()

    def test_quiet_hours_summary(self):
        """Test generating quiet hours summary message."""
        generator = MessageGenerator()

        # Single medication
        single_msg = generator.generate_quiet_hours_summary(
            medications_pending=["Metformin"],
            total_pending=1,
        )
        assert "Metformin" in single_msg.body

        # Multiple medications
        multi_msg = generator.generate_quiet_hours_summary(
            medications_pending=["Metformin", "Aspirin", "Vitamin D"],
            total_pending=3,
        )
        assert "3" in multi_msg.title

    def test_global_instance(self):
        """Test global message generator instance."""
        gen1 = get_message_generator()
        gen2 = get_message_generator()
        assert gen1 is gen2


class TestPlatformNotifications:
    """Tests for the platform notification providers."""

    def test_mock_provider_send(self):
        """Test MockProvider sends and records notifications."""
        provider = MockProvider()

        assert provider.is_available()

        payload = NotificationPayload(
            id="test-123",
            title="Test Title",
            body="Test Body",
            medication_id="med-456",
        )

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(provider.send(payload))
        finally:
            loop.close()

        assert result.success
        assert result.status == DeliveryStatus.DELIVERED
        assert result.platform == NotificationPlatform.MOCK
        assert len(provider.sent_notifications) == 1
        assert provider.sent_notifications[0].id == "test-123"

    def test_mock_provider_failure(self):
        """Test MockProvider can simulate failures."""
        provider = MockProvider()
        provider.set_should_fail(True)

        payload = NotificationPayload(
            id="test-fail",
            title="Test",
            body="Body",
            medication_id="med",
        )

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(provider.send(payload))
        finally:
            loop.close()

        assert not result.success
        assert result.status == DeliveryStatus.FAILED

    def test_mock_provider_callback(self):
        """Test MockProvider callback on send."""
        provider = MockProvider()
        received = []

        def on_send(payload):
            received.append(payload)

        provider.set_on_send(on_send)

        payload = NotificationPayload(
            id="test-cb",
            title="Test",
            body="Body",
            medication_id="med",
        )

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(provider.send(payload))
        finally:
            loop.close()

        assert len(received) == 1
        assert received[0].id == "test-cb"

    def test_mock_provider_clear(self):
        """Test clearing recorded notifications."""
        provider = MockProvider()

        payload = NotificationPayload(
            id="test",
            title="Test",
            body="Body",
            medication_id="med",
        )

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(provider.send(payload))
            assert len(provider.sent_notifications) == 1

            provider.clear()
            assert len(provider.sent_notifications) == 0
        finally:
            loop.close()

    def test_notification_service_with_mock(self):
        """Test NotificationService with mock provider."""
        mock_provider = MockProvider()
        service = NotificationService(providers=[mock_provider])

        loop = asyncio.new_event_loop()
        try:
            initialized = loop.run_until_complete(service.initialize())
            assert initialized
            assert service.active_platform == NotificationPlatform.MOCK

            payload = NotificationPayload(
                id="svc-test",
                title="Service Test",
                body="Testing service",
                medication_id="med",
            )

            result = loop.run_until_complete(service.send(payload))
            assert result.success
        finally:
            loop.close()

    def test_notification_service_fallback(self):
        """Test NotificationService falls back to available provider."""
        failing_provider = MockProvider()
        failing_provider.set_should_fail(True)

        working_provider = MockProvider()

        service = NotificationService(providers=[failing_provider, working_provider])

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(service.initialize())

            payload = NotificationPayload(
                id="fallback-test",
                title="Fallback Test",
                body="Should use working provider",
                medication_id="med",
            )

            result = loop.run_until_complete(service.send(payload))
            assert result.success
            # Should have used working provider
            assert len(working_provider.sent_notifications) == 1
        finally:
            loop.close()

    def test_notification_service_batch(self):
        """Test sending batch notifications."""
        mock_provider = MockProvider()
        service = NotificationService(providers=[mock_provider])

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(service.initialize())

            payloads = [
                NotificationPayload(id=f"batch-{i}", title=f"Test {i}", body="Body", medication_id="med")
                for i in range(3)
            ]

            results = loop.run_until_complete(service.send_batch(payloads))

            assert len(results) == 3
            assert all(r.success for r in results)
            assert len(mock_provider.sent_notifications) == 3
        finally:
            loop.close()

    def test_plyer_provider_availability(self):
        """Test PlyerProvider availability check."""
        provider = PlyerProvider()
        # May or may not be available depending on environment
        assert isinstance(provider.is_available(), bool)

    def test_desktop_notifier_provider_availability(self):
        """Test DesktopNotifierProvider degrades gracefully when unavailable."""
        provider = DesktopNotifierProvider()
        # May or may not be available depending on whether desktop-notifier
        # is installed in this environment; must never raise.
        assert isinstance(provider.is_available(), bool)
        assert provider.platform == NotificationPlatform.DESKTOP_NOTIFIER

    def test_desktop_notifier_provider_send_when_unavailable(self):
        """Test DesktopNotifierProvider reports failure instead of raising
        when the optional dependency is missing, so the service can fall
        back to the next provider."""
        provider = DesktopNotifierProvider()
        with patch.object(provider, "is_available", return_value=False):
            loop = asyncio.new_event_loop()
            try:
                payload = NotificationPayload(
                    id="test",
                    title="Title",
                    body="Body",
                    medication_id="med",
                )
                result = loop.run_until_complete(provider.send(payload))
                assert result.success is False
                assert result.status == DeliveryStatus.FAILED
                assert result.platform == NotificationPlatform.DESKTOP_NOTIFIER
            finally:
                loop.close()

    def test_desktop_notifier_provider_construction_error_is_swallowed(self):
        """A non-ImportError during DesktopNotifier construction (e.g. no DBus
        session bus on a headless host) must be treated as 'unavailable', not
        bubble up and break NotificationService initialization."""
        provider = DesktopNotifierProvider()
        fake_module = MagicMock()
        fake_module.DesktopNotifier.side_effect = RuntimeError("no DBus session bus")
        with patch.dict(sys.modules, {"desktop_notifier": fake_module}):
            # Must return False, never raise.
            assert provider.is_available() is False

    def test_notification_payload_defaults(self):
        """Test NotificationPayload default values."""
        payload = NotificationPayload(
            id="test",
            title="Title",
            body="Body",
            medication_id="med",
        )

        assert payload.action_text == "Mark as taken"
        assert payload.timeout_seconds == 30
        assert payload.silent is False
        assert payload.icon_path is None


class TestNotificationScheduler:
    """Tests for the NotificationScheduler module."""

    def test_scheduler_initial_state(self):
        """Test scheduler starts in stopped state."""
        scheduler = NotificationScheduler()
        assert scheduler.state == SchedulerState.STOPPED
        assert not scheduler.is_running

    def test_scheduler_config_defaults(self):
        """Test default scheduler configuration."""
        config = SchedulerConfig()
        assert config.check_interval_seconds == 60
        assert config.default_window_tolerance_minutes == 30
        assert config.max_notifications_per_hour == 10
        assert config.enable_streak_celebrations is True

    def test_notification_settings_defaults(self):
        """Test default notification settings."""
        settings = NotificationSettings()
        assert settings.enabled is True
        assert settings.max_reminders_per_dose == 3
        assert settings.initial_offset_minutes == 0
        assert settings.nudge_delay_minutes == 15
        assert settings.alert_delay_minutes == 30
        assert settings.weekend_enabled is True
        assert settings.celebration_enabled is True

    def test_scheduler_start_stop(self):
        """Test scheduler start and stop lifecycle."""
        mock_provider = MockProvider()
        service = NotificationService(providers=[mock_provider])
        scheduler = NotificationScheduler(notification_service=service)

        loop = asyncio.new_event_loop()
        try:
            # Start
            loop.run_until_complete(scheduler.start())
            assert scheduler.state == SchedulerState.RUNNING
            assert scheduler.is_running

            # Stop
            loop.run_until_complete(scheduler.stop())
            assert scheduler.state == SchedulerState.STOPPED
            assert not scheduler.is_running
        finally:
            loop.close()

    def test_scheduler_pause_resume(self):
        """Test scheduler pause and resume."""
        mock_provider = MockProvider()
        service = NotificationService(providers=[mock_provider])
        scheduler = NotificationScheduler(notification_service=service)

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(scheduler.start())
            assert scheduler.state == SchedulerState.RUNNING

            # Pause
            loop.run_until_complete(scheduler.pause())
            assert scheduler.state == SchedulerState.PAUSED

            # Resume
            loop.run_until_complete(scheduler.resume())
            assert scheduler.state == SchedulerState.RUNNING

            # Cleanup
            loop.run_until_complete(scheduler.stop())
        finally:
            loop.close()

    def test_scheduler_register_profile(self):
        """Test registering profile sessions."""
        scheduler = NotificationScheduler()

        async def mock_session_factory():
            return AsyncMock()

        scheduler.register_profile_session("profile-123", mock_session_factory)
        assert "profile-123" in scheduler._profile_sessions

        scheduler.unregister_profile_session("profile-123")
        assert "profile-123" not in scheduler._profile_sessions

    def test_time_window_checking(self):
        """Test time window calculation."""
        scheduler = NotificationScheduler()

        # Test normal window
        assert scheduler._time_in_window(time(8, 30), time(8, 0), time(9, 0))
        assert not scheduler._time_in_window(time(10, 0), time(8, 0), time(9, 0))

        # Test edge cases
        assert scheduler._time_in_window(time(8, 0), time(8, 0), time(9, 0))
        assert scheduler._time_in_window(time(9, 0), time(8, 0), time(9, 0))

    def test_time_offset_calculation(self):
        """Test time offset helper."""
        scheduler = NotificationScheduler()

        # Add minutes
        result = scheduler._offset_time(time(8, 30), 15)
        assert result == time(8, 45)

        # Subtract minutes
        result = scheduler._offset_time(time(8, 30), -15)
        assert result == time(8, 15)

        # Clamp to bounds
        result = scheduler._offset_time(time(23, 50), 30)
        assert result == time(23, 59)

        result = scheduler._offset_time(time(0, 10), -30)
        assert result == time(0, 0)

    def test_global_scheduler_instance(self):
        """Test global scheduler instance."""
        scheduler1 = get_notification_scheduler()
        scheduler2 = get_notification_scheduler()
        assert scheduler1 is scheduler2


class TestScheduleCheck:
    """Tests for ScheduleCheck dataclass."""

    def test_schedule_check_creation(self):
        """Test creating a ScheduleCheck."""
        check = ScheduleCheck(
            schedule_id="sched-123",
            medication_id="med-456",
            medication_name="Metformin",
            schedule_label="morning",
            target_time=time(8, 0),
            needs_notification=True,
            priority=ReminderPriority.INITIAL,
            reason="Initial reminder due",
            window_start=time(7, 45),
            window_end=time(8, 30),
            minutes_until_target=15,
            minutes_past_target=0,
            reminders_sent_today=0,
        )

        assert check.schedule_id == "sched-123"
        assert check.needs_notification is True
        assert check.priority == ReminderPriority.INITIAL


class TestIntegration:
    """Integration tests for notification system."""

    def test_full_notification_flow(self):
        """Test complete flow from message generation to delivery."""
        # Create components
        generator = MessageGenerator()
        mock_provider = MockProvider()
        service = NotificationService(providers=[mock_provider])

        # Generate message
        context = MessageContext(
            medication_name="Aspirin",
            schedule_label="evening",
            current_streak=5,
            longest_streak=10,
            priority=ReminderPriority.INITIAL,
            is_weekend=False,
            hour_of_day=18,
            previous_reminders_today=0,
        )
        message = generator.generate_reminder(context)

        # Create payload
        payload = NotificationPayload(
            id="integration-test",
            title=message.title,
            body=message.body,
            medication_id="med-123",
            action_text=message.action_text,
        )

        # Send notification
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(service.initialize())
            result = loop.run_until_complete(service.send(payload))

            assert result.success
            assert len(mock_provider.sent_notifications) == 1

            sent = mock_provider.sent_notifications[0]
            assert sent.title == message.title
            assert sent.body == message.body
        finally:
            loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
