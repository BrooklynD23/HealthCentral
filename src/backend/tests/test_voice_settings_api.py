"""Tests for voice settings API response models."""

from api.model_settings import VoiceSettingsResponse, VoiceSettingsUpdate


def test_voice_settings_response():
    r = VoiceSettingsResponse(voice_logging_enabled=False, voice_modal_seen=False)
    assert r.voice_logging_enabled is False

def test_voice_settings_update_partial():
    u = VoiceSettingsUpdate(voice_logging_enabled=True)
    assert u.voice_logging_enabled is True
    assert u.voice_modal_seen is None
