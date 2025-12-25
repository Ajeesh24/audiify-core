#!/bin/bash

# Manual Backend Startup for Audifyy
echo "🐍 Starting Audifyy Backend..."

# Check if we're in backend directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Please run this from the backend/ directory"
    exit 1
fi

# Create and activate virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "🔧 Activating virtual environment..."
source venv/bin/activate

echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your OpenAI API key!"
fi

echo "🚀 Starting FastAPI server..."
echo "📊 Backend will be available at: http://localhost:8000"
echo "📖 API Docs will be available at: http://localhost:8000/docs"
echo ""

python -m app.main