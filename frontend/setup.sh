#!/bin/bash

# FinBot Frontend Setup Script
# This script sets up the NextJS frontend application for FinBot

set -e  # Exit on any error

echo "🚀 FinBot Frontend Setup"
echo "========================"

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: package.json not found. Please run this script from the frontend directory."
    exit 1
fi

# Check Node.js version
echo "📋 Checking Node.js version..."
if ! command -v node &> /dev/null; then
    echo "❌ Error: Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'.' -f1 | sed 's/v//')
if [ "$NODE_VERSION" -lt "18" ]; then
    echo "❌ Error: Node.js version 18+ required. Found: $(node -v)"
    exit 1
fi

echo "✅ Node.js version: $(node -v)"

# Check if npm is available
if ! command -v npm &> /dev/null; then
    echo "❌ Error: npm is not installed."
    exit 1
fi

echo "✅ npm version: $(npm -v)"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
npm install

# Check if .env.local exists
if [ ! -f ".env.local" ]; then
    echo ""
    echo "🔧 Creating environment configuration..."
    cp .env.example .env.local
    echo "✅ Created .env.local from .env.example"
else
    echo "✅ Environment configuration already exists"
fi

# Build verification
echo ""
echo "🔨 Running build verification..."
if npm run build; then
    echo "✅ Build successful!"
else
    echo "❌ Build failed. Please check the error messages above."
    exit 1
fi

echo ""
echo "🎉 Frontend setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Ensure the Python backend is running on http://localhost:8000"
echo "2. Start the development server: npm run dev"
echo "3. Open http://localhost:3000 in your browser"
echo ""
echo "👥 Demo accounts available:"
echo "   - john.employee / demo123   (Employee access)"
echo "   - sarah.finance / demo123   (Finance access)"
echo "   - mike.engineer / demo123   (Engineering access)"  
echo "   - lisa.marketing / demo123  (Marketing access)"
echo "   - robert.hr / demo123       (HR access)"
echo "   - maria.ceo / demo123       (Full admin access)"
echo ""
echo "🔗 Useful commands:"
echo "   npm run dev     - Start development server"
echo "   npm run build   - Build for production"
echo "   npm run start   - Start production server"
echo "   npm run lint    - Run ESLint checks"