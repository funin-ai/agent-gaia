#!/usr/bin/env python
"""AgentGaia entry point script."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    from src.main import app
    import uvicorn
    import argparse

    parser = argparse.ArgumentParser(description="AgentGaia Server")
    parser.add_argument("--env", "-e", type=str, default="local", help="Environment")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host")
    parser.add_argument("--port", "-p", type=int, default=9033, help="Port")
    parser.add_argument("--reload", "-r", action="store_true", help="Auto-reload")
    parser.add_argument("--use-vault", action="store_true", help="Use Vault for API keys")

    args = parser.parse_args()

    os.environ["APP_ENV"] = args.env

    if args.use_vault:
        os.environ["USE_VAULT"] = "true"

    print(f"🚀 Starting AgentGaia ({args.env}) on http://{args.host}:{args.port}")

    uvicorn.run(
        "src.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )
