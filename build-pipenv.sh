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

# Try to use pipenv if available, otherwise fall back to pip
if command -v pipenv &> /dev/null; then
    echo "Using pipenv for dependency management..."
    pipenv install --system --deploy
else
    echo "pipenv not available, using pip..."
    pip install --upgrade pip
    pip install --upgrade setuptools wheel
    
    # Try to install with pre-compiled wheels first
    pip install --only-binary=all -r requirements.txt || {
        echo "Some packages need compilation, trying with Rust..."
        pip install -r requirements.txt
    }
fi 