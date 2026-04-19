"""Entry point: `python -m backend` (run from v2/).

Boots uvicorn on localhost:8000 by default. CLI flags pass through so a
production deploy can override host/port and harden the WS.
"""

import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(prog="brickshooter")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="restart on code changes (dev)")
    parser.add_argument(
        "--ws-max-size",
        type=int,
        default=65536,
        help="max inbound WS frame size in bytes (default 64 KiB)",
    )
    args = parser.parse_args()

    uvicorn.run(
        "backend.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        ws_max_size=args.ws_max_size,
    )


if __name__ == "__main__":
    main()
