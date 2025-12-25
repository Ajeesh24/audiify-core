#!/bin/bash

# Manual Frontend Startup for Audifyy
echo "⚛️ Starting Audifyy Frontend..."

# Check if we're in frontend directory
if [ ! -f "package.json" ]; then
    echo "❌ Please run this from the frontend/ directory"
    exit 1
fi

echo "📦 Installing Node.js dependencies..."
npm install

echo "🚀 Starting Vite development server..."
echo "📱 Frontend will be available at: http://localhost:5173"
echo ""

npm run dev