#!/bin/sh
set -eu

if [ "${ZEABUR:-}" = "true" ]; then
    exec python -m sanguosha.web
fi

# Existing VPS/Caddy path: keep the trusted Caddy proxy and its fixed internal port.
exec uvicorn sanguosha.web.app:app --host 0.0.0.0 --port 8000 --workers 1 --ws-max-size 256000 --timeout-graceful-shutdown 20 --proxy-headers --forwarded-allow-ips 172.30.91.2
