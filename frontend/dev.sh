#!/bin/bash

# FinBot Development Startup Script
# Quick script to start both backend and frontend for development

echo "🚀 Starting FinBot Development Environment"
echo "=========================================="

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Check if backend is running
echo "🔍 Checking backend status..."
if check_port 8000; then
    echo "✅ Backend appears to be running on port 8000"
else
    echo "❌ Backend not detected on port 8000"
    echo "📝 Please start the Python backend first:"
    echo "   cd .."
    echo "   python main.py"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Exiting..."
        exit 1
    fi
fi

# Check if frontend is already running
if check_port 3000; then
    echo "⚠️  Frontend appears to be already running on port 3000"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Exiting..."
        exit 1
    fi
fi

# Start frontend development server
echo ""
echo "🎯 Starting frontend development server..."
echo "📱 Frontend will be available at: http://localhost:3000"
echo "🔗 Backend API expected at: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

npm run dev