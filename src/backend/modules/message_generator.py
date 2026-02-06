"""
Message generator for medication reminders.

Generates contextual, encouraging reminder messages based on:
- Priority level (initial, nudge, alert)
- User's adherence patterns and streaks
- Time of day and medication context

Phase 3: Smart Notifications - Message Generation Component
"""

import logging
import random
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ReminderPriority(str, Enum):
    """Priority levels for reminders."""
    INITIAL = "initial"
    GENTLE_NUDGE = "gentle_nudge"
    IMPORTANT_ALERT = "important_alert"


class MessageTone(str, Enum):
    """Tone for reminder messages."""
    SUPPORTIVE = "supportive"
    FRIENDLY = "friendly"
    CONCERNED = "concerned"


@dataclass
class MessageContext:
    """Context for message generation."""
    medication_name: str
    schedule_label: str  # "morning", "evening", etc.
    current_streak: int
    longest_streak: int
    priority: ReminderPriority
    is_weekend: bool
    hour_of_day: int
    previous_reminders_today: int
    days_since_last_miss: Optional[int] = None


@dataclass
class GeneratedMessage:
    """A generated reminder message."""
    title: str
    body: str
    tone: MessageTone
    priority: ReminderPriority
    includes_streak: bool
    action_text: str = "Mark as taken"


# Message templates organized by priority and context
INITIAL_TEMPLATES = {
    "morning": [
        ("Good morning! ☀️", "Time for your {medication_name}. Starting the day right!"),
        ("Morning reminder", "Your {schedule_label} {medication_name} is ready."),
        ("Rise and shine!", "Don't forget your {medication_name} this morning."),
    ],
    "midday": [
        ("Midday check-in", "Time for your {medication_name}."),
        ("Lunch reminder", "Remember your {schedule_label} {medication_name}."),
    ],
    "evening": [
        ("Evening reminder", "Time for your {medication_name}."),
        ("Winding down", "Don't forget your {schedule_label} {medication_name}."),
    ],
    "bedtime": [
        ("Bedtime routine", "Time for your {medication_name} before bed."),
        ("Sleep well", "Your {medication_name} is part of a good night's rest."),
    ],
    "default": [
        ("Medication reminder", "Time for your {medication_name}."),
        ("Quick reminder", "Your {schedule_label} {medication_name} is due."),
    ],
}

NUDGE_TEMPLATES = [
    ("Still time!", "Your {medication_name} is waiting. Just a gentle nudge."),
    ("Friendly reminder", "Haven't logged your {medication_name} yet today."),
    ("Just checking in", "Did you take your {medication_name}?"),
    ("Quick follow-up", "Your {schedule_label} {medication_name} is still pending."),
]

ALERT_TEMPLATES = [
    ("Important reminder", "Your {medication_name} dose may be missed. Please check."),
    ("Action needed", "It's been a while - please log your {medication_name}."),
    ("Don't forget!", "Your {schedule_label} {medication_name} needs attention."),
]

# Streak celebration messages
STREAK_CELEBRATIONS = {
    3: [
        ("3 days strong! 🎯", "You've taken {medication_name} 3 days in a row!"),
        ("Hat trick!", "3 consecutive days - great start!"),
    ],
    7: [
        ("One week! 🌟", "7 days of consistent {medication_name} - amazing!"),
        ("Weekly win!", "A full week of adherence - you're doing great!"),
    ],
    14: [
        ("Two weeks! 🏆", "14 days strong with {medication_name}!"),
        ("Fortnight champion!", "Two weeks of consistency - impressive!"),
    ],
    30: [
        ("One month! 🎉", "30 days of taking {medication_name} - incredible dedication!"),
        ("Monthly milestone!", "A full month - your commitment is inspiring!"),
    ],
    60: [
        ("Two months! 🥇", "60 days strong! You've built a solid habit."),
    ],
    90: [
        ("Three months! 🏅", "90 days of consistency - truly remarkable!"),
    ],
    365: [
        ("One year! 🎊", "365 days! An entire year of dedication to your health!"),
    ],
}


class MessageGenerator:
    """
    Generates contextual reminder messages for medications.

    Selects appropriate templates based on:
    - Time of day
    - Priority level
    - User's streak and patterns
    - Previous reminders sent
    """

    def __init__(self):
        """Initialize the message generator."""
        pass

    def generate_reminder(self, context: MessageContext) -> GeneratedMessage:
        """
        Generate a reminder message based on context.

        Args:
            context: Message generation context

        Returns:
            Generated message with title, body, and metadata
        """
        # Check for streak celebration first
        streak_message = self._check_streak_celebration(context)
        if streak_message:
            return streak_message

        # Select templates based on priority
        if context.priority == ReminderPriority.INITIAL:
            return self._generate_initial(context)
        elif context.priority == ReminderPriority.GENTLE_NUDGE:
            return self._generate_nudge(context)
        else:
            return self._generate_alert(context)

    def _generate_initial(self, context: MessageContext) -> GeneratedMessage:
        """Generate initial reminder message."""
        # Select time-appropriate templates
        schedule_key = context.schedule_label.lower()
        if schedule_key not in INITIAL_TEMPLATES:
            # Infer from hour
            if context.hour_of_day < 11:
                schedule_key = "morning"
            elif context.hour_of_day < 14:
                schedule_key = "midday"
            elif context.hour_of_day < 20:
                schedule_key = "evening"
            else:
                schedule_key = "bedtime"

        templates = INITIAL_TEMPLATES.get(schedule_key, INITIAL_TEMPLATES["default"])
        title, body = random.choice(templates)

        return GeneratedMessage(
            title=title,
            body=body.format(
                medication_name=context.medication_name,
                schedule_label=context.schedule_label,
            ),
            tone=MessageTone.FRIENDLY,
            priority=ReminderPriority.INITIAL,
            includes_streak=False,
        )

    def _generate_nudge(self, context: MessageContext) -> GeneratedMessage:
        """Generate gentle nudge message."""
        title, body = random.choice(NUDGE_TEMPLATES)

        return GeneratedMessage(
            title=title,
            body=body.format(
                medication_name=context.medication_name,
                schedule_label=context.schedule_label,
            ),
            tone=MessageTone.SUPPORTIVE,
            priority=ReminderPriority.GENTLE_NUDGE,
            includes_streak=False,
        )

    def _generate_alert(self, context: MessageContext) -> GeneratedMessage:
        """Generate important alert message."""
        title, body = random.choice(ALERT_TEMPLATES)

        # If user has a good streak, mention it to encourage
        streak_mention = ""
        if context.current_streak >= 3:
            streak_mention = f" You have a {context.current_streak}-day streak going!"

        return GeneratedMessage(
            title=title,
            body=body.format(
                medication_name=context.medication_name,
                schedule_label=context.schedule_label,
            ) + streak_mention,
            tone=MessageTone.CONCERNED,
            priority=ReminderPriority.IMPORTANT_ALERT,
            includes_streak=context.current_streak >= 3,
        )

    def _check_streak_celebration(
        self, context: MessageContext
    ) -> Optional[GeneratedMessage]:
        """
        Check if current streak warrants a celebration message.

        Only triggers at milestone boundaries (3, 7, 14, 30, etc.)
        """
        # Only celebrate on initial reminder
        if context.priority != ReminderPriority.INITIAL:
            return None

        # Only check milestone days
        milestones = sorted(STREAK_CELEBRATIONS.keys())

        for milestone in milestones:
            # Celebrate when streak equals milestone (exact match)
            if context.current_streak == milestone:
                templates = STREAK_CELEBRATIONS[milestone]
                title, body = random.choice(templates)

                return GeneratedMessage(
                    title=title,
                    body=body.format(medication_name=context.medication_name),
                    tone=MessageTone.SUPPORTIVE,
                    priority=ReminderPriority.INITIAL,
                    includes_streak=True,
                    action_text="Keep it going!",
                )

        return None

    def generate_missed_recovery(
        self,
        medication_name: str,
        days_missed: int,
        previous_streak: int,
    ) -> GeneratedMessage:
        """
        Generate an encouraging message after a missed dose.

        Focuses on getting back on track rather than the miss.
        """
        if days_missed == 1 and previous_streak >= 7:
            title = "Let's get back on track"
            body = (
                f"One day doesn't erase your {previous_streak}-day streak mindset. "
                f"Ready to start fresh with {medication_name}?"
            )
        elif days_missed <= 2:
            title = "Welcome back!"
            body = f"Ready to restart your {medication_name} routine? Every day is a new opportunity."
        else:
            title = "Fresh start"
            body = f"No judgment here. Ready to begin again with {medication_name}?"

        return GeneratedMessage(
            title=title,
            body=body,
            tone=MessageTone.SUPPORTIVE,
            priority=ReminderPriority.INITIAL,
            includes_streak=False,
            action_text="Start fresh",
        )

    def generate_quiet_hours_summary(
        self,
        medications_pending: list[str],
        total_pending: int,
    ) -> GeneratedMessage:
        """
        Generate a summary message for after quiet hours.

        Used when user has enabled quiet hours and has pending medications.
        """
        if total_pending == 1:
            title = "Missed during quiet hours"
            body = f"You had a reminder for {medications_pending[0]} during quiet hours."
        else:
            med_list = ", ".join(medications_pending[:3])
            if len(medications_pending) > 3:
                med_list += f" and {len(medications_pending) - 3} more"
            title = f"{total_pending} reminders during quiet hours"
            body = f"Medications: {med_list}"

        return GeneratedMessage(
            title=title,
            body=body,
            tone=MessageTone.FRIENDLY,
            priority=ReminderPriority.INITIAL,
            includes_streak=False,
            action_text="Review",
        )


# Global instance
_message_generator: Optional[MessageGenerator] = None


def get_message_generator() -> MessageGenerator:
    """Get or create the global message generator instance."""
    global _message_generator
    if _message_generator is None:
        _message_generator = MessageGenerator()
    return _message_generator
