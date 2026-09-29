from __future__ import annotations

import uvicorn

from .config import WebConfig


def main() -> None:
    config = WebConfig.from_env()
    config.validate_production()
    uvicorn.run("sanguosha.web.app:app", host=config.host, port=config.port,
                log_level=config.log_level.lower(), workers=1, proxy_headers=False)


if __name__ == "__main__":
    main()
