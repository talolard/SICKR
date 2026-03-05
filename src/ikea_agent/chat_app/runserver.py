"""CLI runner for FastAPI chat runtime."""

from __future__ import annotations

import argparse

import uvicorn

from ikea_agent.chat_app.main import create_app


def main() -> None:
    """Parse arguments and run the chat ASGI app with uvicorn."""

    parser = argparse.ArgumentParser(description="Run chat runtime FastAPI server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    uvicorn.run(create_app(), host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
