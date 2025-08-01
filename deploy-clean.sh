#!/bin/bash

# Clean deployment script for Receipt Processing App
# This script ensures a clean build with latest requirements

echo "🧹 Starting clean deployment..."

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "[ERROR] requirements.txt not found. Please run this script from the backend directory."
    exit 1
fi

echo "[INFO] Current pandas version in requirements.txt:"
grep "pandas==" requirements.txt

echo "[INFO] Verifying Python version..."
python --version

echo "[INFO] Testing requirements installation..."
pip install -r requirements.txt --dry-run

echo "[INFO] Clean deployment ready!"
echo ""
echo "[INFO] Next steps:"
echo "1. Commit and push your changes"
echo "2. Deploy to your platform"
echo "3. Monitor the build logs"
echo ""
echo "[NOTE] If you're using Render, make sure to:"
echo "- Clear any build cache in your Render dashboard"
echo "- Redeploy with 'Clear build cache & deploy' option" 