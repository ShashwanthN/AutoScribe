from __future__ import annotations

import uvicorn

from backend import settings


def main() -> None:
    uvicorn.run(
        "backend.app:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
