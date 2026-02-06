#!/bin/bash
# Quick Start Script for Gundam Card Game Simulator

echo "======================================"
echo "Gundam Card Game Simulator - Quick Start"
echo "======================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Creating one..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment found"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
echo ""
echo "Checking dependencies..."
if ! python -c "import requests, bs4, lxml" 2>/dev/null; then
    echo "❌ Dependencies not installed. Installing..."
    pip install -r requirements.txt
    echo "✓ Dependencies installed"
else
    echo "✓ Dependencies installed"
fi

echo ""
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "Available commands:"
echo ""
echo "1. Run card scraper:"
echo "   python scrape_cards.py"
echo ""
echo "2. Test card database:"
echo "   python card_database/test_cases.py"
echo ""
echo "3. Demo card database:"
echo "   python card_database/card_loader.py"
echo ""
echo "4. View card structure:"
echo "   cat cards_structure.txt"
echo ""
echo "5. View all cards:"
echo "   cat card_database/all_cards.json | python -m json.tool"
echo ""
echo "======================================"
echo ""
