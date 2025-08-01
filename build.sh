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

# Install Python dependencies with pre-compiled wheels when possible
pip install --upgrade pip
pip install --upgrade setuptools wheel

# Try to install with pre-compiled wheels first
pip install --only-binary=all -r requirements.txt || {
    echo "Some packages need compilation, trying with Rust..."
    pip install -r requirements.txt
} 