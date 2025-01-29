################################################################################################
# API Service Makefile
#
# This Makefile is split into the following sections:
#   - Requirements: prerequisites for running the environment.
#   - Application: for building, testing, and publishing the project.
#   - Development: for formatting, linting, and other development tasks.
#   - Docker: for building, running, and publishing Docker images.
#
# We write our rule names in the following format: [verb]-[noun]-[noun], e.g. "build-app".
#
# Variables ####################################################################################

PROJECT_ROOT:=$(CURDIR)
PYTHON_VERSION:=`cat .python-version`

APP_VERSION?=DEV-SNAPSHOT
APP_NAME?=api

IMAGE_ID?=$(APP_NAME):$(APP_VERSION)
IMAGE_SAVE_LOCATION?=$(PROJECT_ROOT)/build/images
OPENAPI_SAVE_LOCATION?=$(PROJECT_ROOT)/build/openapi

# Requirements ##################################################################################

.PHONY: require-pyenv
require-pyenv:
	@command -v pyenv >/dev/null 2>&1 || (echo "Pyenv is required. Please install via 'make install-pyenv'." && exit 1)

.PHONY: require-poetry
require-poetry:
	@command -v poetry >/dev/null 2>&1 || (echo "Poetry is required. Please install via 'make install-poetry'." && exit 1)

.PHONY: require-docker
require-docker:
	@command -v docker >/dev/null 2>&1 || (echo "Docker is required. Please install via https://docs.docker.com/engine/install/." && exit 1)

.PHONY: install-pyenv
install-pyenv:
	@echo "Installing Pyenv..."
	@curl https://pyenv.run | bash

.PHONY: install-poetry
install-poetry:
	@echo "Installing Poetry..."
	@curl -sSL https://install.python-poetry.org | python3 -

# Application ##################################################################################

.PHONY: setup
setup: require-poetry require-pyenv
	@echo "Setting up the project..."
	@echo "Setting local shell Python version to $(PYTHON_VERSION)..."
	@deactivate 2>/dev/null || true
	@pyenv install -s $(PYTHON_VERSION)
	@pyenv local $(PYTHON_VERSION)
	@poetry env remove --all 2>/dev/null || true
	@poetry config virtualenvs.prefer-active-python true
	@echo "Installing Poetry dependencies..."
	@poetry install
	@echo "Setup complete."
	@echo "Your virtual environment python path is:"
	@echo "$$(poetry env info --path)/bin/python"

.PHONY: test
test:
	@echo "Running tests..."
	@poetry run pytest -s -v $(PROJECT_ROOT)/tests

.PHONY: run
run:
	@echo "Starting a local instance of the service..."
	@echo "Starting the Postgres database..."
	@docker compose -p api up -d postgres
	@echo "Starting the FastAPI instance..."
	@poetry run uvicorn main:app --app-dir $(PROJECT_ROOT)/src --host localhost --port 8000 --reload

# Development ##################################################################################

.PHONY: clean
clean:
	@echo "Cleaning application (e.g. cache, build files, virtual environment)..."
	@poetry run pyclean -v ./src
	@poetry env remove $$(basename $$(poetry env info --path))
	@echo "Cleaning complete."
	@echo "Running 'make setup' to setup the project again."
	@echo "NOTE: For PyCharm users, you might need to attach the new Poetry interpreter to the project."
	@$(MAKE) setup

.PHONY: update-dependencies
update-dependencies:
	@echo "Updating dependencies..."
	@poetry update

.PHONY: lock-dependencies
lock-dependencies:
	@echo "Locking dependencies..."
	@poetry lock

.PHONY: format-code
format-code:
	@echo "Formatting application..."
	@poetry run black $(PROJECT_ROOT)/src $(PROJECT_ROOT)/tests

.PHONY: lint-code
lint-code:
	@echo "Linting application..."
	@poetry run flake8 $(PROJECT_ROOT)/src $(PROJECT_ROOT)/tests

.PHONY: check-format
check-format:
	@echo "Checking application formatting..."
	@poetry run black --check $(PROJECT_ROOT)/src $(PROJECT_ROOT)/tests

.PHONY: check-lint
check-lint:
	@echo "Checking application linting..."
	@poetry run flake8 --show-source --statistics --count $(PROJECT_ROOT)/src $(PROJECT_ROOT)/tests

.PHONY: enable-code-quality-pre-commit-hook
enable-code-quality-pre-commit-hook:
	@echo "Enabling pre-commit hook..."
	@ln -sf $(PROJECT_ROOT)/.hooks/pre-commit $(PROJECT_ROOT)/../.git/hooks/pre-commit
	@echo "Pre-commit hook enabled."
	@$(MAKE) setup

.PHONY: cleanup-local-deployment
cleanup-local-deployment:
	@echo "Starting all services..."
	docker compose down
	@echo "Removing cached image"
	docker rmi api-api
	@echo "Cleanup complete"

# Docker #######################################################################################

.PHONY: check-test-docker
check-test-docker: require-docker
	@echo "Testing application... (Containerised)"
	@$(call build_docker_image,development)
	@$(call run_docker_dev_mount,poetry run pytest -v /app/tests)

.PHONY: check-format-docker
check-format-docker: require-docker
	@echo "Checking application formatting... (Containerised)"
	@$(call build_docker_image,development)
	@$(call run_docker_dev_mount,poetry run black --check /app/src /app/tests)

.PHONY: check-lint-docker
check-lint-docker: require-docker
	@echo "Checking application linting... (Containerised)"
	@$(call build_docker_image,development)
	@$(call run_docker_dev_mount,poetry run flake8 --show-source --statistics --count /app/src /app/tests)

.PHONY: check-code-quality-docker
check-code-quality-docker: require-docker
	@echo "Checking application code quality... (Containerised)"
	@$(MAKE) check-format-docker
	@$(MAKE) check-lint-docker
	@$(MAKE) check-test-docker

.PHONY: run-app-docker-dev
run-app-docker-dev: require-docker
	@docker stop $(APP_NAME)-toolchain-dev || true
	@echo "Running application in development mode... (Containerised)"
	@$(call build_docker_image,development)
	@$(call run_docker_dev_mount,poetry run uvicorn src.main:app --app-dir /app/src --host localhost --port 8888 --reload,-d -p 8888:8888)

.PHONY: run-app-docker-prod
run-app-docker-prod: require-docker
	@echo "Running application in production mode... (Containerised)"
	@$(call build_docker_image,production)
	@docker run -p 8080:8080 --name $(APP_NAME)-toolchain-prod --rm $(IMAGE_ID)

.PHONY: export-production-image
export-production-image: require-docker
	@echo "Exporting Docker image..."
	@$(call build_docker_image,production)
	@mkdir -p $(IMAGE_SAVE_LOCATION)
	@docker save -o $(IMAGE_SAVE_LOCATION)/$(APP_NAME)-$(APP_VERSION).tar $(IMAGE_ID)

.PHONY: export-openapi-schema
export-openapi-schema: run-app-docker-dev
	@echo "Exporting OpenAPI schema..."
	@mkdir -p $(OPENAPI_SAVE_LOCATION)
	@sleep 5
	@curl -s http://0.0.0.0:8888/openapi.json > $(OPENAPI_SAVE_LOCATION)/openapi.json
	@docker stop $(APP_NAME)-toolchain-dev || true
	@docker run --rm -v $(OPENAPI_SAVE_LOCATION):/build redocly/cli build-docs --api=/build/openapi.json --output=/build/index.html

# Functions ####################################################################################

# NOTE:
#   For Dockerfile.optimised , you should use rely on --target $(1) to build the image:
#   @docker build --target $(1) --build-arg APP_VERSION=$(APP_VERSION) --build-arg APP_NAME=$(APP_NAME) -t $(IMAGE_ID) .
define build_docker_image
	@echo "Building Docker image for target: $(1)"
	@docker build --build-arg APP_VERSION=$(APP_VERSION) --build-arg APP_NAME=$(APP_NAME) -t $(IMAGE_ID) .
endef

define run_docker_dev_mount
	@docker run $(2) \
		-v /var/run/docker.sock:/var/run/docker.sock \
		-v $(PROJECT_ROOT)/src:/app/src \
		-v $(PROJECT_ROOT)/tests:/app/tests \
		-v $(PROJECT_ROOT)/environment:/app/environment \
		-v $(PROJECT_ROOT)/pyproject.toml:/app/pyproject.toml \
		-v $(PROJECT_ROOT)/poetry.lock:/app/poetry.lock \
		--rm --name $(APP_NAME)-toolchain-dev $(IMAGE_ID) $(1)
endef

# Concourse #######################################################################################

CURRENT_BRANCH := $(shell git rev-parse --abbrev-ref HEAD)
DEPLOYMENT_NAME := feature-branch
SERVICE_NAME := feature-branch-service
PIPELINE_NAME := api-feature-branch-deployment
PIPELINE_FILE := cd/feature-branch-deployment.yaml
FLY_TARGET := target

# USAGE EXAMPLE:
#   make deploy-feature-branch TARGET_BRANCH=[GIVEN_BRANCH_NAME]
.PHONY: set-pipeline-feature-branch-deployment
set-pipeline-feature-branch-deployment:
	@echo "Setting pipeline $(PIPELINE_NAME)..."
	@if [ -z "$${TARGET_BRANCH}" ] || [ "$${TARGET_BRANCH}" = "" ]; then \
  		echo "TARGET_BRANCH variable is not set. Defaulting to current branch: $(CURRENT_BRANCH)"; \
		TARGET_BRANCH="$(CURRENT_BRANCH)"; \
	fi; \
	fly -t $(FLY_TARGET) set-pipeline -p $(PIPELINE_NAME) -c $(PIPELINE_FILE) -v branch_name=$${TARGET_BRANCH}

.PHONY: unpause-pipeline-feature-branch-deployment
unpause-pipeline-feature-branch-deployment:
	@echo "Unpausing pipeline $(PIPELINE_NAME)..."
	fly -t $(FLY_TARGET) unpause-pipeline -p $(PIPELINE_NAME)

.PHONY: trigger-pipeline-job-feature-branch-deployment
trigger-pipeline-job-feature-branch-deployment:
	@echo "Triggering job $(PIPELINE_NAME)/build-and-deploy-feature-branch..."
	fly -t $(FLY_TARGET) trigger-job -j $(PIPELINE_NAME)/build-and-deploy-feature-branch -w

.PHONY: cleanup-feature-branch-deployment
cleanup-feature-branch-deployment:
	@echo "Cleaning up feature branch deployment..."
	@kubectl delete deployment $(DEPLOYMENT_NAME) -n dev --ignore-not-found=true -n namespace
	@kubectl get pods -n namespace
	@kubectl delete service $(SERVICE_NAME) -n dev --ignore-not-found=true -n namespace
	@kubectl get services -n namespace
	@echo "Stopping port forwarding"
	@pkill -f "kubectl port-forward service/feature-branch-service 8888:80" || true

.PHONY: port-forward-api-feature-branch
port-forward-api-feature-branch:
	@echo "port forwarding"
	@kubectl port-forward service/feature-branch-service 8886:80 -n namespace

.PHONY: deploy-feature-branch
deploy-feature-branch:
	@echo "Deploying feature branch..."
	@$(MAKE) set-pipeline-feature-branch-deployment
	@$(MAKE) unpause-pipeline-feature-branch-deployment
	@$(MAKE) trigger-pipeline-job-feature-branch-deployment
	@echo "Deployment complete."
	@echo "TIP: Don't forget to cleanup the deployment after you're done"
	@echo "     via 'make cleanup-feature-branch-deployment'"
	@sleep 10
	@$(MAKE) port-forward-api-feature-branch
