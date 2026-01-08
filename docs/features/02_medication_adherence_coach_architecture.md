# Adaptive Medication Adherence Coach - Architecture Document

*Version 0.1 | January 2025 | Draft - Pending PM Approval*

---

## 1. Feature Overview

An intelligent medication reminder system that adapts to real-world behavior patterns instead of rigid schedules. Unlike traditional apps that penalize users for taking medication at 9:37am instead of 9:00am, this coach learns individual patterns and adjusts expectations accordingly.

### User Stories

**US-1: Smart Medication Setup**
- Add medications by typing or scanning prescription bottles
- Set dosage, frequency, preferred time windows
- Easy conversational input

**US-2: Adaptive Reminder Scheduling**
- Learn when user ACTUALLY takes medications
- If typical "morning" is 7-9am, send reminder at start of window
- Not rigid clock-based timing

**US-3: Gentle Nudge Escalation**
- First reminder: "Good morning! Time for Metformin when you're ready"
- Second nudge: "Friendly reminder about your Metformin"
- Important alert: "Haven't logged Metformin yet - everything okay?"

**US-4: Quick Dose Logging**
- Tap notification → "Taken now" / "Taken earlier" / "Skip with reason"
- Minimal friction for daily use

**US-5: Pattern Recognition**
- Detect "weekday morning person" (7:15am) vs "weekend late riser" (9:30am)
- Notice "always forgets evening dose on Tuesdays"
- Extra nudge on problem days

**US-6: Adherence Insights**
- 7-day streak visualization
- "Your HbA1c improved 0.8% since consistent adherence"
- Links to lab result trends (cross-feature integration)

---

## 2. Data Architecture

### Database Schema

**`medications`**
```python
class Medication(Base):
    id: str                        # Primary key
    profile_id: str                # FK to profiles
    name: str                      # "Metformin"
    generic_name: Optional[str]
    dosage_amount: Optional[float] # 500
    dosage_unit: Optional[str]     # "mg"
    dosage_form: Optional[str]     # "tablet", "capsule"
    frequency: str                 # "daily", "twice_daily", "as_needed"
    is_active: bool
    instructions: Optional[str]    # "Take with food"
    reminder_enabled: bool
    metadata_json: Optional[str]   # Extended metadata
    started_at: datetime
    ended_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
```

**`medication_schedules`**
```python
class MedicationSchedule(Base):
    id: str
    medication_id: str             # FK to medications
    schedule_label: str            # "morning", "evening", "bedtime"
    target_time: time              # 08:00:00 (user-set baseline)
    adaptive_window_start: Optional[time]  # 07:15:00 (learned)
    adaptive_window_end: Optional[time]    # 09:30:00 (learned)
    reminder_offset_minutes: int   # Minutes before target for first reminder
    days_of_week: Optional[str]    # JSON: [0,1,2,3,4] for Mon-Fri
    is_active: bool
```

**`doses_taken`**
```python
class DoseTaken(Base):
    id: str
    medication_id: str
    schedule_id: Optional[str]
    taken_at: datetime             # When dose was taken
    log_method: str                # "manual", "notification_tap", "voice"
    dosage_amount: Optional[float]
    dosage_unit: Optional[str]
    variance_minutes: Optional[int]  # Positive = late, negative = early
    notes: Optional[str]           # "Took with breakfast"
    was_skipped: bool
    skip_reason: Optional[str]     # "forgot", "side_effects"
    logged_at: datetime
```

**`adherence_patterns`**
```python
class AdherencePattern(Base):
    id: str
    medication_id: str
    schedule_id: Optional[str]
    pattern_type: str              # "time_window", "weekday_vs_weekend", "missed_day_pattern"
    pattern_data: str              # JSON with pattern details
    confidence: float              # 0.0-1.0
    sample_size: int
    learned_at: datetime
```

**`reminder_logs`**
```python
class ReminderLog(Base):
    id: str
    profile_id: str
    medication_id: str
    schedule_id: Optional[str]
    reminder_type: str             # "initial", "gentle_nudge", "important_alert"
    message: str
    sent_at: datetime
    delivery_method: str           # "notification", "voice", "in_app"
    was_interacted: bool
    interaction_type: Optional[str]  # "dismissed", "snoozed", "marked_taken"
```

---

## 3. Adaptive Algorithm Design

### Pattern Learning Engine

```python
class PatternLearner:
    MIN_SAMPLES_FOR_PATTERN = 7    # Need 7 doses to establish pattern
    CONFIDENCE_THRESHOLD = 0.70    # 70% confidence minimum
    OUTLIER_THRESHOLD_STDEV = 2.5  # Remove outliers beyond 2.5 std devs

    async def learn_patterns(medication_id, schedule_id):
        # Returns list of detected patterns:
        # - time_window: avg time, std dev, earliest/latest
        # - weekday_vs_weekend: different patterns for each
        # - missed_day_pattern: frequently missed day of week

    async def update_adaptive_window(schedule_id):
        # Updates schedule's adaptive_window_start/end
        # Based on learned time_window pattern

    async def calculate_streak(medication_id):
        # Returns current streak, longest streak, 7-day adherence
```

### Time Window Learning

```python
def _learn_time_window(doses):
    # 1. Get last 30 days of non-skipped doses
    # 2. Extract time-of-day in minutes since midnight
    # 3. Remove outliers (z-score > 2.5)
    # 4. Calculate mean and std dev
    # 5. Window = mean ± 1.5 std dev (86% coverage)
    # 6. Confidence = 1.0 - (std_dev / 60) capped at [0, 1]

    return TimeWindowPattern(
        avg_time=avg_time,
        std_dev_minutes=std_minutes,
        earliest_time=earliest_time,
        latest_time=latest_time,
        confidence=confidence,
        sample_size=len(doses)
    )
```

### Reminder Priority System

```python
def calculate_priority(schedule, last_dose, current_time):
    window_start = schedule.adaptive_window_start or schedule.target_time
    window_end = schedule.adaptive_window_end or schedule.target_time

    if current_time < window_start:
        return ("initial", "supportive")
    elif window_start <= current_time <= window_end:
        return ("gentle_nudge", "friendly")
    else:
        minutes_late = (current_time - window_end).minutes
        if minutes_late > 120:
            return ("important_alert", "concerned")
        return ("gentle_nudge", "friendly")
```

---

## 4. Notification System

### Notification Scheduler

```python
class NotificationScheduler:
    """Runs as background task, checks every minute for due reminders."""

    async def start():
        while running:
            await _check_and_send_reminders()
            await asyncio.sleep(60)

    async def _check_and_send_reminders():
        # 1. Get all active schedules with reminders enabled
        # 2. Check if schedule applies today (days_of_week)
        # 3. Check if reminder is due (at window start)
        # 4. Check if dose already taken today
        # 5. Calculate priority and generate message
        # 6. Send notification and log
```

### Message Templates

```python
TEMPLATES = {
    ("initial", "supportive"): [
        "Good morning! Time for your {medication_name} when you're ready",
        "Hi there! Your {medication_name} reminder - {schedule_label} dose",
        "Starting your day right! Time for {medication_name}",
    ],
    ("gentle_nudge", "friendly"): [
        "Friendly reminder: {medication_name} ({dosage})",
        "Just checking in - have you taken your {medication_name}?",
        "Quick reminder about {medication_name}",
    ],
    ("important_alert", "concerned"): [
        "Haven't logged {medication_name} yet today - everything okay?",
        "Important: {medication_name} dose still pending",
        "You might have forgotten {medication_name} - please check",
    ],
}

STREAK_MESSAGES = {
    3: "3 days in a row!",
    7: "One week streak! Amazing!",
    14: "Two weeks strong!",
    30: "30-day streak! You're a champion!",
}
```

### Platform-Specific Notifications

| Platform | Implementation |
|----------|---------------|
| Windows | Windows Runtime ToastNotificationManager |
| macOS | pync / native notification center |
| Linux | D-Bus notify-send (plyer) |

---

## 5. API Endpoints

```python
# Medication CRUD
POST   /{profile_id}/medications              Create medication
GET    /{profile_id}/medications              List medications
GET    /{profile_id}/medications/{id}         Get medication

# Schedules
POST   /{profile_id}/medications/{id}/schedules   Create schedule
GET    /{profile_id}/medications/{id}/schedules   List schedules

# Dose Logging
POST   /{profile_id}/medications/{id}/doses   Log dose (taken or skipped)
GET    /{profile_id}/medications/{id}/doses   List recent doses

# Statistics & Patterns
GET    /{profile_id}/medications/{id}/stats   Get adherence stats
POST   /{profile_id}/medications/{id}/learn-patterns   Trigger pattern learning
GET    /{profile_id}/medications/{id}/correlations   Get lab correlations
```

### Request/Response Examples

**Create Medication:**
```json
POST /api/v1/medications/{profile_id}/medications
{
    "name": "Metformin",
    "dosage_amount": 500,
    "dosage_unit": "mg",
    "frequency": "twice_daily",
    "instructions": "Take with food",
    "reminder_enabled": true
}
```

**Log Dose:**
```json
POST /api/v1/medications/{profile_id}/medications/{id}/doses?schedule_id=xxx
{
    "taken_at": "2025-01-07T08:15:00Z",
    "log_method": "notification_tap",
    "notes": "With breakfast"
}
```

**Adherence Stats Response:**
```json
{
    "medication_id": "xxx",
    "current_streak_days": 12,
    "longest_streak_days": 24,
    "last_7_days_adherence": 0.86,
    "last_30_days_adherence": 0.92,
    "total_doses_taken": 54,
    "total_doses_skipped": 4
}
```

---

## 6. Integration with Lab Results

### Outcome Correlation

```python
class OutcomeCorrelation:
    """Correlate medication adherence with lab result improvements."""

    async def correlate_medication_to_labs(medication_id, analyte_canonical):
        # 1. Get medication start date
        # 2. Get adherence history since start
        # 3. Get lab observations for analyte since start
        # 4. Calculate adherence rate before each lab
        # 5. Correlate adherence with value changes

        return {
            "medication_name": "Metformin",
            "analyte": "hemoglobin_a1c",
            "correlations": [
                {
                    "period": "2024-10-01 to 2025-01-01",
                    "adherence_rate": 0.94,
                    "value_change": -0.8,
                    "prev_value": 7.4,
                    "curr_value": 6.6,
                }
            ],
            "overall_trend": "improving"
        }
```

**Example User Message:**
> "Your HbA1c improved from 7.4% to 6.6% over the past 3 months. This correlates with your 94% adherence to Metformin. Keep up the great work!"

---

## 7. Privacy & Safety

### All Data Local
- Medication data encrypted in SQLCipher database
- Per-profile encryption (same as documents)
- No cloud sync by default

### Safety Disclaimers

```
MEDICATION REMINDER DISCLAIMER

This is a reminder tool only. HealthCentral does NOT:
- Prescribe or recommend medications
- Provide medical advice or diagnoses
- Replace your healthcare provider

Always consult your doctor before:
- Starting, stopping, or changing medications
- If you experience side effects
- If you have questions about your medications

In case of emergency, call 911.
```

### Safety Guardrails
- Never suggest medications
- Never recommend dosage changes
- Never diagnose conditions
- No emergency medical advice

---

## 8. Resource Requirements

- **Compute:** CPU-only viable, no GPU required
- **Storage:** Minimal (schedules, adherence events)
- **Model:** Optional LLM for message personalization (uses existing small model)
- **Background:** System tray app for desktop, native scheduling APIs for mobile

---

## 9. Implementation Phases

### Phase 1: Core Medication Management (Week 1-2)
- Database models
- Basic CRUD API
- Simple dose logging UI
- Manual reminder creation

### Phase 2: Pattern Learning (Week 3-4)
- Time window learning algorithm
- Weekday vs weekend detection
- Streak tracking
- Statistics dashboard

### Phase 3: Smart Notifications (Week 5-6)
- Notification scheduler service
- Platform-specific providers
- Message generator with templates
- Priority system

### Phase 4: Conversational & Advanced (Week 7-8)
- Voice/text dose logging
- Intent detection
- Lab result correlation
- Gamification (streaks, achievements)

### Phase 5: Polish & Mobile (Week 9-10)
- Mobile app integration
- Background task optimization
- Battery optimization
- User testing

---

## 10. Files to Create

**Backend:**
```
src/backend/
├── models/medication.py           # All medication models
├── modules/
│   ├── adherence_patterns.py      # Pattern learning
│   ├── notification_scheduler.py  # Notification scheduling
│   ├── message_generator.py       # Message templates
│   └── platform_notifications.py  # Platform-specific
└── api/medications.py             # API endpoints
```

**Frontend:**
```
src/frontend/src/
├── components/features/adherence/
│   ├── MedicationCard.tsx
│   ├── DoseLoggingModal.tsx
│   ├── AdherenceDashboard.tsx
│   ├── StreakDisplay.tsx
│   └── NotificationSettings.tsx
├── pages/MedicationCoach.tsx
├── services/medicationService.ts
└── hooks/useAdherence.ts
```

---

## 11. Dependencies to Add

```txt
# requirements.txt additions
plyer>=2.1.0          # Cross-platform notifications
winsdk>=1.0.0b10      # Windows notification center
pync>=2.0.3           # macOS notifications
apscheduler>=3.10.0   # Background task scheduling
```

---

## 12. Resolved Decisions

### Platform: Desktop-First with Mobile-Ready Architecture ✓

- Windows desktop MVP (Tauri/Electron)
- API designed to support future mobile clients
- Notification system abstracted for cross-platform
- Android APK planned for future release (v0.3+)

**Mobile-Ready Design Patterns:**
```
Backend API:
├── RESTful endpoints (works with any client)
├── JWT authentication (mobile-compatible)
├── Push notification abstraction layer
└── Sync-ready data model (future offline-first mobile)

Notification System:
├── Platform provider interface
├── Windows provider (MVP)
├── Android provider (v0.3+)
└── iOS provider (future)
```

### Notifications: Opt-In Only ✓

- Disabled by default (reminder_enabled = false)
- User explicitly enables per medication
- Settings page explains notification behavior
- Easy to disable globally or per-medication
- Quiet hours configuration available

### Background Task: System Tray App ✓

- Tauri system tray integration
- Runs minimized when app closed
- User can fully exit from tray menu
- Respects Windows notification settings

## 13. Remaining Open Decisions

- [ ] Gamification level (basic streaks vs full badges/achievements)
- [ ] Lab correlation prominence in UI
- [ ] Voice logging implementation (v0.3+ or later)
- [ ] Medication database integration (RxNorm lookup)
