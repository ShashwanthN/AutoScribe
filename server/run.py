from __future__ import annotations

import uvicorn

from server import settings


def main() -> None:
    uvicorn.run(
        "server.app:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
