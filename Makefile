include Makefile.config
-include Makefile.custom.config

all: install lint check-outdated build-frontend run-agentserver

install:
	uv sync
	$(PIP) install --upgrade --no-cache pip setuptools -e .[lint,themes] devcore
	cd frontend && $(NPM) install

clean:
	rm -fr $(NODE_MODULES)
	rm -fr $(VENV)
	rm -fr *.egg-info

lint:
	$(PYTEST) --flake8 -m flake8 $(PROJECT_NAME)
	$(PYTEST) --isort -m isort $(PROJECT_NAME)

check-outdated:
	$(PIP) list --outdated --format=columns

# AgentServer (Web Terminal) - default args
AGENTSERVER_ARGS ?= --host=localhost --port=57575 --unsecure --debug
run-agentserver:
	uv run aetherterm-agentserver $(AGENTSERVER_ARGS)

# AgentShell (AI Terminal Wrapper)
AGENTSHELL_ARGS ?=
run-agentshell:
	uv run aetherterm-agentshell $(AGENTSHELL_ARGS)

# ControlServer (Central Management)
CONTROLSERVER_ARGS ?= --port=8765
run-controlserver:
	uv run aetherterm-controlserver $(CONTROLSERVER_ARGS)

# Legacy alias for backward compatibility
run-debug: run-agentserver

# Process management with supervisord
run-supervisor:
	supervisord -c supervisord.conf

stop-supervisor:
	supervisorctl -c supervisord.conf shutdown

status-supervisor:
	supervisorctl -c supervisord.conf status

restart-supervisor:
	supervisorctl -c supervisord.conf restart all

# Log retrieval using supervisord-mcp
logs-agentserver:
	uv run supervisord-mcp logs agentserver

logs-agentserver-stderr:
	uv run supervisord-mcp logs agentserver --stderr

logs-frontend:
	uv run supervisord-mcp logs frontend

logs-frontend-stderr:
	uv run supervisord-mcp logs frontend --stderr

build-frontend:
	cd frontend && $(NPM) install
	cd frontend && $(NPM) run build
	mv frontend/dist/index.html src/aetherterm/agentserver/templates/index.html
	rm -rf src/aetherterm/agentserver/static/*
	cp -r frontend/dist/* src/aetherterm/agentserver/static/

release: build-frontend
	git pull
	$(eval VERSION := $(shell PROJECT_NAME=$(PROJECT_NAME) $(VENV)/bin/devcore bump $(LEVEL)))
	git commit -am "Bump $(VERSION)"
	git tag $(VERSION)
	$(PYTHON) setup.py sdist bdist_wheel upload
	git push
	git push --tags
