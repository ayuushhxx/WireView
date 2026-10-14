#!/usr/bin/env python3
"""
WireView HTTP - Server Launcher
Starts the scratch-built HTTP/1.1 TCP server and observability engine.
"""

import argparse
import logging
import signal
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from server.config import ServerConfig
from server.tcp_server import TCPServer


if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def main():
    parser = argparse.ArgumentParser(
        description="WireView HTTP - Low-Level Python Socket HTTP Server & Real-Time Studio"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Listening IP address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Listening TCP port (default: 8080)")
    parser.add_argument("--workers", type=int, default=32, help="Worker thread pool limit (default: 32)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose debug logging")

    args = parser.parse_args()
    setup_logging(args.verbose)

    config = ServerConfig(
        host=args.host,
        port=args.port,
        max_workers=args.workers,
    )

    server = TCPServer(config=config)

    def sigint_handler(sig, frame):
        print("\n[WireView] Shutting down server gracefully...")
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, sigint_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, sigint_handler)

    print("=" * 70)
    print(" [*] WIREVIEW HTTP/1.1 SERVER (BUILT FROM SCRATCH)")
    print("=" * 70)
    print(f" • Local Interface  : http://{config.host}:{config.port}/")
    print(f" • Studio Dashboard : http://{config.host}:{config.port}/dashboard")
    print(f" • Health Endpoint  : http://{config.host}:{config.port}/health")
    print(f" • Concurrency      : {config.max_workers} bounded worker threads")
    print(f" • Network Engine   : Standard Python TCP socket module (RFC 7230)")
    print("=" * 70)
    print("Press Ctrl+C to terminate.")
    print()

    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()
