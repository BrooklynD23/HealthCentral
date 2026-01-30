# Implementation Prompt for Next Agent

## Mission
Continue implementing HealthCentral's v0.2 features. **Priority: Phase 0.3 (BioMistral Model Integration)** - Build the tiered model management system with hardware detection.

## Current Project State (2026-01-30)

| Phase | Status | Description |
|-------|--------|-------------|
| 0.1-0.2 | ✅ COMPLETE | Database models, seed data |
| **0.3** | **⏳ PRIORITY** | **BioMistral Model Integration** |
| 1 | ✅ COMPLETE | Lab Interpretation Engine (Backend) |
| 2 | ✅ COMPLETE | Medication Management (Backend) |
| 3 | ✅ COMPLETE | Smart Notifications (Backend) |
| 4 | ⏳ PENDING | Frontend Integration |
| 5 | ⏳ NOT STARTED | Polish & Testing |

**Backend is feature-complete.** Now enhance interpretation quality with tiered LLM support.

## Required Reading

1. **`docs/features/TASK_LIST.md`** - Active task tracker with phase details
2. **`docs/04_local_models_inference_plan.md`** - Local model inference architecture
3. **`docs/features/01_lab_result_interpreter_architecture.md`** - Lab interpreter specs

---

## Phase 0.3: BioMistral Model Integration (PRIORITY)

### Overview
Build a comprehensive model management system with hardware detection and user choice. **Default to Tier 3** (Qwen2.5 0.5B) for broad compatibility while allowing users to upgrade based on their hardware.

### 1. Model Tier Structure

Create organized model folder structure:
```
models/
├── tier1_high/
│   └── biomistral-7b.Q4_K_M.gguf (~4GB)
│   └── README.md (requirements: GPU 8GB+ VRAM)
├── tier2_mid/
│   └── phi-3-mini.Q4_K_M.gguf (~2GB)
│   └── README.md (requirements: GPU 4-6GB or 16GB RAM)
├── tier3_low/
│   └── qwen2.5-0.5b.Q4_K_M.gguf (~0.5GB)
│   └── README.md (requirements: CPU-only, 8GB RAM) ← DEFAULT
└── tier4_minimal/
    └── template_only/ (no model file needed)
    └── README.md (fallback, no LLM requirements)
```

### 2. Hardware Detection System

Create `scripts/detect_hardware.py`:
```python
# Capabilities to detect:
- GPU presence and VRAM (nvidia-smi or torch.cuda)
- System RAM total and available
- CPU cores and capabilities
- Disk space for model storage

# Output recommendation logic:
- GPU 8GB+ VRAM → Recommend Tier 1, allow Tier 2-4
- GPU 4-6GB or 16GB+ RAM → Recommend Tier 2, allow Tier 1-4
- 8GB+ RAM, no GPU → Recommend Tier 3 (DEFAULT), allow Tier 2-4
- <8GB RAM → Recommend Tier 4, allow Tier 3-4

# Always default to Tier 3 if detection fails
```

### 3. Model Manager Script

Create `scripts/model_manager.py`:
```python
# Commands:
python scripts/model_manager.py detect          # Show hardware + recommendation
python scripts/model_manager.py download --tier auto  # Download recommended tier
python scripts/model_manager.py download --tier 3     # Download specific tier
python scripts/model_manager.py list            # Show installed models
python scripts/model_manager.py switch --tier 2 # Switch active tier
python scripts/model_manager.py cleanup         # Remove unused models

# Download sources (HuggingFace):
- Tier 1: BioMistral/BioMistral-7B-GGUF
- Tier 2: microsoft/Phi-3-mini-4k-instruct-gguf
- Tier 3: Qwen/Qwen2.5-0.5B-Instruct-GGUF
```

### 4. Model Selector Module

Create `src/backend/modules/model_selector.py`:
```python
class ModelSelector:
    """Intelligent model selection with user preferences."""

    def detect_hardware_tier(self) -> HardwareProfile:
        """Assess system capabilities."""

    def get_recommended_tier(self) -> int:
        """Get hardware-based recommendation (default: 3)."""

    def get_user_preference(self, profile_id: str) -> Optional[int]:
        """Get user's saved tier preference."""

    def set_user_preference(self, profile_id: str, tier: int) -> None:
        """Save user's tier choice to profile."""

    def get_active_tier(self, profile_id: str) -> int:
        """Get tier to use: user preference > recommendation > default (3)."""

    def load_model(self, tier: int) -> LlamaModel:
        """Load model for specified tier with fallback chain."""

    def get_fallback_chain(self, tier: int) -> List[int]:
        """Return fallback tiers if loading fails: [tier, tier+1, ..., 4]."""
```

### 5. Hardware Detection Module

Create `src/backend/modules/hardware_detection.py`:
```python
@dataclass
class HardwareProfile:
    gpu_available: bool
    gpu_vram_gb: Optional[float]
    gpu_name: Optional[str]
    ram_total_gb: float
    ram_available_gb: float
    cpu_cores: int
    disk_free_gb: float
    recommended_tier: int
    max_supported_tier: int
    detection_timestamp: datetime

def detect_hardware() -> HardwareProfile:
    """Detect system hardware capabilities."""

def get_tier_requirements(tier: int) -> dict:
    """Return requirements for each tier."""
    # Tier 1: {"gpu_vram_gb": 8, "ram_gb": 16, "disk_gb": 5}
    # Tier 2: {"gpu_vram_gb": 4, "ram_gb": 16, "disk_gb": 3}
    # Tier 3: {"gpu_vram_gb": 0, "ram_gb": 8, "disk_gb": 1}
    # Tier 4: {"gpu_vram_gb": 0, "ram_gb": 4, "disk_gb": 0}

def can_run_tier(profile: HardwareProfile, tier: int) -> bool:
    """Check if hardware can support a tier."""
```

### 6. Integration Points

**Update `modules/interpret.py`:**
```python
class InterpretModule:
    def __init__(self, model_selector: ModelSelector = None):
        self.model_selector = model_selector or get_model_selector()

    async def generate_interpretation(self, context, profile_id: str):
        tier = self.model_selector.get_active_tier(profile_id)

        if tier == 4:
            return self._template_based_interpretation(context)

        try:
            model = self.model_selector.load_model(tier)
            return await self._llm_interpretation(model, context)
        except ModelLoadError:
            # Fallback chain
            for fallback_tier in self.model_selector.get_fallback_chain(tier):
                try:
                    model = self.model_selector.load_model(fallback_tier)
                    return await self._llm_interpretation(model, context)
                except ModelLoadError:
                    continue
            return self._template_based_interpretation(context)
```

**Update `modules/rag.py`:**
- Use ModelSelector for model loading
- Add tier-aware context window sizing
- Implement graceful degradation

### 7. API Endpoints

Add to `api/settings.py` or create `api/model_settings.py`:
```python
GET  /settings/model              # Get current model settings
POST /settings/model/detect       # Run hardware detection
POST /settings/model/tier         # Set preferred tier
GET  /settings/model/download-progress  # Check download status
POST /settings/model/download     # Start model download
```

### 8. Dependencies to Add

Update `requirements.txt`:
```txt
# Model Management (Phase 0.3)
huggingface-hub>=0.20.0    # Model downloading
psutil>=5.9.0              # Hardware detection (RAM, CPU, disk)
py-cpuinfo>=9.0.0          # Detailed CPU info
# torch is optional - only for GPU detection, not required
```

### 9. User Experience Flow

**First Run:**
1. App starts → detect hardware
2. Show recommendation: "We recommend Tier 3 (Qwen 0.5B) for your system"
3. User can accept or choose different tier
4. Download selected model with progress indicator
5. Save preference to profile

**Subsequent Runs:**
1. Load saved preference
2. Verify model still exists
3. Option in settings to re-detect hardware or change tier

**Settings UI (Phase 4):**
- Current tier display
- Hardware info display
- Tier selection with requirements shown
- Download/switch button
- "Re-detect hardware" button

### 10. Implementation Checklist

```markdown
### Phase 0.3 Tasks
| Task | Status | Notes |
|------|--------|-------|
| Create `models/` folder structure with READMEs | [ ] TODO | |
| Create `scripts/detect_hardware.py` | [ ] TODO | |
| Create `scripts/model_manager.py` | [ ] TODO | |
| Create `modules/hardware_detection.py` | [ ] TODO | |
| Create `modules/model_selector.py` | [ ] TODO | |
| Update `modules/interpret.py` for tiered inference | [ ] TODO | |
| Update `modules/rag.py` for model selector | [ ] TODO | |
| Add model settings API endpoints | [ ] TODO | |
| Update requirements.txt | [ ] TODO | |
| Create unit tests for model selection | [ ] TODO | |
| Test fallback chain | [ ] TODO | |
| Document tier requirements | [ ] TODO | |
```

---

## Phase 4: Frontend Integration (After Phase 0.3)

**Lab Interpreter UI** (`components/features/interpreter/`):
- InterpretedResultCard.tsx, InterpretedTrendChart.tsx
- PanelInterpretationDashboard.tsx, ReferenceRangeComparison.tsx
- `pages/LabInterpreter.tsx`, `services/interpretationService.ts`

**Medication Coach UI** (`components/features/adherence/`):
- MedicationCard.tsx, DoseLoggingModal.tsx
- AdherenceDashboard.tsx, StreakDisplay.tsx, NotificationSettings.tsx
- `pages/MedicationCoach.tsx`, `services/medicationService.ts`

**Model Settings UI** (new for Phase 0.3):
- ModelSettingsPanel.tsx - Tier selection, hardware info, download progress

---

## Technical Patterns

### Backend Patterns
```python
# API endpoint pattern
@router.post("/endpoint")
async def endpoint(
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    # Use profile_db for user data
```

### Key Files for Patterns
- API: `api/interpretations.py`, `api/medications.py`, `api/notifications.py`
- Modules: `modules/interpret.py`, `modules/adherence_patterns.py`

## Quality Gates

Before marking phases complete:
- [ ] All unit tests passing (`pytest tests/`)
- [ ] Python syntax valid (`python -m py_compile`)
- [ ] Documentation updated in `TASK_LIST.md`

## Task Tracking

**Always update** `docs/features/TASK_LIST.md`:
- Mark tasks `[x] DONE` with dates
- Add session notes at bottom
