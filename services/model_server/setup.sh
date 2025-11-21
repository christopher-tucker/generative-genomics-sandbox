#!/bin/bash
# Setup script for model_server Python environment

set -e  # Exit on error

echo "🚀 Setting up model_server Python environment..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 not found. Please install Python 3.10+ first."
    exit 1
fi

# Remove existing venv if it exists (optional - comment out if you want to keep it)
if [ -d "venv" ]; then
    echo "⚠️  Existing venv directory found. Removing it..."
    rm -rf venv
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip --quiet

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To run tests:"
echo "  pytest"
echo ""
echo "To start the server:"
echo "  uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload"
echo ""

