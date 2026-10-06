from __future__ import annotations

import asyncio
import sys

import uvicorn

from .config import WebConfig


def socket_loop_factory():
    """Socket-only loop avoids Proactor peer-reset shutdown callbacks on Windows."""
    return asyncio.SelectorEventLoop()


def web_loop() -> str:
    if sys.platform != 'win32':
        return 'auto'
    # Uvicorn >=0.36 uses its own factory and overrides global loop policy.
    if hasattr(uvicorn.Config, 'get_loop_factory'):
        return 'sanguosha.web.__main__:socket_loop_factory'
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    return 'asyncio'


def main() -> None:
    config = WebConfig.from_env()
    config.validate_production()
    uvicorn.run("sanguosha.web.app:app", host=config.host, port=config.port,
                log_level=config.log_level.lower(), workers=1, proxy_headers=False,
                loop=web_loop())


if __name__ == "__main__":
    main()
