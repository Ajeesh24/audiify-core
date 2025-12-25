#!/bin/bash

# Audifyy MVP Development Startup Script
echo "🎧 Starting Audifyy MVP Development Environment..."

# Check if we're in the right directory
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "❌ Please run this script from inside the audifyy-mvp/ directory"
    echo "Current directory: $(pwd)"
    echo "Expected: backend/ and frontend/ subdirectories should be present"
    exit 1
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check dependencies
echo "🔍 Checking dependencies..."

if ! command_exists python3; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

if ! command_exists node; then
    echo "❌ Node.js is required but not installed."
    exit 1
fi

if ! command_exists npm; then
    echo "❌ npm is required but not installed."
    exit 1
fi

echo "✅ All dependencies found!"

# Start backend in background
echo "🐍 Starting FastAPI backend..."
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if not already installed
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

echo "⚠️  Skipping Playwright browsers due to certificate issues (article extraction will use fallback methods)"
# playwright install chromium

if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env file from example..."
    cp .env.example .env
    echo "⚠️  Please edit backend/.env and add your OpenAI API key!"
fi

echo "🚀 Starting backend server..."
python -m app.main &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start frontend
echo "⚛️ Starting React frontend..."
cd ../frontend

if [ ! -d "node_modules" ]; then
    echo "📦 Installing Node.js dependencies..."
    npm install
fi

echo "🚀 Starting frontend development server..."
npm run dev &
FRONTEND_PID=$!

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "👋 Goodbye!"
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

echo ""
echo "🎉 Audifyy MVP is now running!"
echo ""
echo "📊 Backend API: http://localhost:8000"
echo "📱 Frontend App: http://localhost:5173"
echo "📖 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID