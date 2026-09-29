from __future__ import annotations

import os

APP_VERSION = os.getenv("APP_VERSION", "0.3.0")
BUILD_COMMIT = os.getenv("BUILD_COMMIT", "development")
PROTOCOL_VERSION = 2
RELAY_PROTOCOL_VERSION = 1
