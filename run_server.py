#!/usr/bin/env python3
"""
Entry point to launch the Travel Assistant API.
Run from the project root:
    python run_server.py
  or:
    .venv\\Scripts\\python run_server.py
"""
import sys
import os

# Add project root to path so all modules resolve correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,      # reload=True causes subprocess issues with venv on Windows
        log_level="info",
    )
