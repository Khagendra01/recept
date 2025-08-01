#!/bin/bash

echo "Testing deployment configuration..."

# Check Python version
python --version

# Test if we can install the requirements
echo "Testing requirements installation..."
pip install --upgrade pip
pip install --upgrade setuptools wheel

# Try to install with pre-compiled wheels
echo "Attempting to install with pre-compiled wheels..."
pip install --only-binary=all -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Successfully installed with pre-compiled wheels"
else
    echo "⚠️  Some packages need compilation, this is expected for Rust dependencies"
    echo "Testing full installation..."
    pip install -r requirements.txt
    if [ $? -eq 0 ]; then
        echo "✅ Successfully installed all dependencies"
    else
        echo "❌ Failed to install dependencies"
        exit 1
    fi
fi

echo "Testing application startup..."
python -c "from app.main import app; print('✅ Application imports successfully')"

echo "✅ Deployment test completed successfully" 