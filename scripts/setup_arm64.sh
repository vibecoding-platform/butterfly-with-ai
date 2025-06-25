#!/bin/bash
# Setup script for ARM64 compatibility

set -e

echo "Setting up AetherTerm for ARM64 architecture..."

# Detect architecture
ARCH=$(uname -m)
OS=$(uname -s)

if [[ "$ARCH" != "arm64" && "$ARCH" != "aarch64" ]]; then
    echo "Warning: This script is intended for ARM64 architecture. Detected: $ARCH"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python version: $PYTHON_VERSION"

# Install uv if not present
if ! command -v uv &> /dev/null; then
    echo "Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Install system dependencies based on OS
if [[ "$OS" == "Darwin" ]]; then
    # macOS
    echo "Installing macOS dependencies..."
    if command -v brew &> /dev/null; then
        brew install postgresql openssl libffi
        export LDFLAGS="-L$(brew --prefix openssl)/lib -L$(brew --prefix libffi)/lib"
        export CPPFLAGS="-I$(brew --prefix openssl)/include -I$(brew --prefix libffi)/include"
    else
        echo "Warning: Homebrew not found. Please install PostgreSQL and OpenSSL manually."
    fi
elif [[ "$OS" == "Linux" ]]; then
    # Linux
    echo "Installing Linux dependencies..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y build-essential libpq-dev libssl-dev libffi-dev python3-dev
    elif command -v yum &> /dev/null; then
        sudo yum install -y gcc postgresql-devel openssl-devel libffi-devel python3-devel
    else
        echo "Warning: Package manager not recognized. Please install build dependencies manually."
    fi
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip and install build tools
echo "Upgrading pip and installing build tools..."
pip install --upgrade pip setuptools wheel

# Install psycopg2 from source for ARM64
echo "Installing psycopg2 for ARM64..."
pip install psycopg2

# Install other dependencies
echo "Installing project dependencies..."
uv pip install -e ".[dev,test,arm64]"

# Install frontend dependencies
if [[ -d "frontend" ]]; then
    echo "Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

# Build frontend
if [[ -d "frontend" ]]; then
    echo "Building frontend..."
    make build-frontend
fi

echo "ARM64 setup complete!"
echo ""
echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To run the application:"
echo "  make run-agentserver"