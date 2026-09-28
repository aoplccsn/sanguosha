"""One timing policy for human decisions and non-blocking presentation."""

import os


HUMAN_DECISION_TIMEOUT_MS = 30_000
PREGAME_GENERAL_TIMEOUT_MS = HUMAN_DECISION_TIMEOUT_MS
DECISION_TIMER_TICK_MS = 100

TARGET_BEAM_MS = 560
SLASH_VFX_MS = 420
DODGE_VFX_MS = 380
DAMAGE_FEEDBACK_MS = 380
DEATH_VFX_MS = 640
KILL_ANNOUNCEMENT_MS = 1_250
GAME_RESULT_FADE_MS = 650


def vfx_duration(milliseconds: int) -> int:
    """Animations never delay rule resolution; tests can advance nearly instantly."""
    return 1 if os.environ.get('VFX_TEST_MODE') or os.environ.get('PYTEST_CURRENT_TEST') else milliseconds
