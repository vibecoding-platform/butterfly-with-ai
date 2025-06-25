#!/bin/bash
# Setup script for Jupyter integration with jupyter-server-proxy

set -e

echo "Setting up AetherTerm with Jupyter integration..."

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

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip and install build tools
echo "Upgrading pip and installing build tools..."
pip install --upgrade pip setuptools wheel

# Install AetherTerm with Jupyter support
echo "Installing AetherTerm with Jupyter integration..."
uv pip install -e ".[dev,test,jupyter]"

# Install frontend dependencies if directory exists
if [[ -d "frontend" ]]; then
    echo "Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

# Build frontend if possible
if [[ -d "frontend" && -f "Makefile" ]]; then
    echo "Building frontend..."
    make build-frontend
fi

# Create Jupyter configuration directory
echo "Setting up Jupyter configuration..."
mkdir -p jupyter_config

# Create jupyter-server-proxy configuration
cat > jupyter_config/jupyter_server_config.py << 'EOF'
# Jupyter Server configuration for AetherTerm integration

c = get_config()

# Enable jupyter-server-proxy
c.ServerApp.jpserver_extensions = {
    'jupyter_server_proxy': True
}

# Configure AetherTerm proxy
c.ServerProxy.servers = {
    'aetherterm': {
        'command': ['aetherterm-agentserver', '--host=127.0.0.1', '--port={port}', '--unsecure'],
        'port': 57575,
        'timeout': 30,
        'launcher_entry': {
            'title': 'AetherTerm',
            'icon_path': '/static/aetherterm.svg',
            'enabled': True
        },
        'new_browser_tab': True,
    }
}

# Optional: Add custom static files
c.ServerApp.extra_static_paths = [
    '/path/to/aetherterm/static'  # Customize this path
]
EOF

# Create Jupyter notebook configuration
cat > jupyter_config/jupyter_notebook_config.py << 'EOF'
# Jupyter Notebook configuration for AetherTerm integration

c = get_config()

# Enable server proxy extension
c.NotebookApp.server_extensions = [
    'jupyter_server_proxy'
]
EOF

# Create custom launcher extension configuration
cat > jupyter_config/aetherterm_launcher.json << 'EOF'
{
  "kernelspecs": {},
  "language_servers": {},
  "server_extensions": {
    "jupyter_server_proxy": true
  },
  "disabled_extensions": [],
  "federated_extensions": [],
  "labextensions": {},
  "themes": {},
  "shortcuts": [
    {
      "command": "server-proxy:open-aetherterm",
      "keys": ["Ctrl Shift T"],
      "selector": "body"
    }
  ]
}
EOF

# Create startup script
cat > jupyter_config/start_jupyter.sh << 'EOF'
#!/bin/bash
# Start Jupyter with AetherTerm integration

set -e

# Activate virtual environment
source ../venv/bin/activate

# Set Jupyter config directory
export JUPYTER_CONFIG_DIR=$(pwd)

# Start Jupyter Lab with AetherTerm proxy
echo "Starting Jupyter Lab with AetherTerm integration..."
echo "Access AetherTerm via: http://localhost:8888/aetherterm/"
echo ""

jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root
EOF

chmod +x jupyter_config/start_jupyter.sh

# Create example notebook
cat > jupyter_config/AetherTerm_Demo.ipynb << 'EOF'
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# AetherTerm Integration Demo\n",
    "\n",
    "This notebook demonstrates how to use AetherTerm within Jupyter.\n",
    "\n",
    "## Access AetherTerm\n",
    "\n",
    "1. **Via Launcher**: Look for the \"AetherTerm\" tile in the JupyterLab launcher\n",
    "2. **Via URL**: Navigate to `/aetherterm/` in your browser\n",
    "3. **Via Keyboard**: Press `Ctrl+Shift+T`\n",
    "\n",
    "## Python Integration\n",
    "\n",
    "You can also control AetherTerm programmatically:"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Example: Launch AetherTerm programmatically\n",
    "import subprocess\n",
    "import time\n",
    "\n",
    "# Start AetherTerm server in background\n",
    "# proc = subprocess.Popen(['aetherterm-agentserver', '--port=57576'])\n",
    "# time.sleep(2)\n",
    "\n",
    "print(\"AetherTerm integration ready!\")\n",
    "print(\"Access via: http://localhost:8888/aetherterm/\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Features Available\n",
    "\n",
    "- Full terminal emulation in your browser\n",
    "- AI-assisted terminal operations\n",
    "- Session sharing and collaboration\n",
    "- Real-time monitoring and logging\n",
    "- Integration with Jupyter workflows"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.11.0"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}
EOF

echo "Jupyter integration setup complete!"
echo ""
echo "Configuration files created in: jupyter_config/"
echo ""
echo "To start Jupyter with AetherTerm:"
echo "  cd jupyter_config"
echo "  ./start_jupyter.sh"
echo ""
echo "Or manually:"
echo "  source venv/bin/activate"
echo "  export JUPYTER_CONFIG_DIR=\$(pwd)/jupyter_config"
echo "  jupyter lab --ip=0.0.0.0 --port=8888"
echo ""
echo "Then access AetherTerm at: http://localhost:8888/aetherterm/"