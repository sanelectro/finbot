#!/usr/bin/env python3
"""
FinBot - Advanced RAG application with RBAC for FinSolve Technologies
"""

from src.api.main import app
import uvicorn

def main():
    """Start the FinBot API server"""
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()
