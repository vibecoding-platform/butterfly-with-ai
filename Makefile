include Makefile.config
-include Makefile.custom.config

all: install lint check-outdated build-frontend run-debug

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

ARGS ?= --host=localhost --port=57575 --unsecure --debug
run-debug:
	uv run aetherterm-agentserver $(ARGS)


build-frontend:
	cd frontend && $(NPM) install
	cd frontend && $(NPM) run build
	mv frontend/dist/index.html src/aetherterm/templates/index.html
	rm -rf src/aetherterm/static/*
	cp -r frontend/dist/* src/aetherterm/static/

release: build-frontend
	git pull
	$(eval VERSION := $(shell PROJECT_NAME=$(PROJECT_NAME) $(VENV)/bin/devcore bump $(LEVEL)))
	git commit -am "Bump $(VERSION)"
	git tag $(VERSION)
	$(PYTHON) setup.py sdist bdist_wheel upload
	git push
	git push --tags
