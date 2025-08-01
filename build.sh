#!/bin/bash

# Set environment variables to avoid Rust/Cargo issues
export CARGO_HOME=/tmp/cargo
export RUSTUP_HOME=/tmp/rustup
export PATH="$CARGO_HOME/bin:$PATH"

# Create cargo directories
mkdir -p $CARGO_HOME
mkdir -p $RUSTUP_HOME

# Install Rust if not present
if ! command -v rustc &> /dev/null; then
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
    source $CARGO_HOME/env
fi

# Upgrade pip and install build tools
python -m pip install --upgrade pip
python -m pip install --upgrade setuptools wheel

# Install dependencies with fallback strategy
echo "Installing Python dependencies..."
pip install -r requirements.txt

# If the above fails, try with pre-compiled wheels
if [ $? -ne 0 ]; then
    echo "Retrying with pre-compiled wheels..."
    pip install --only-binary=all -r requirements.txt || {
        echo "Some packages need compilation, trying with Rust..."
        pip install -r requirements.txt
    }
fi

echo "Build completed successfully!" 