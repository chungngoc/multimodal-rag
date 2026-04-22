# multimodal-rag - Developer Commands
# ============================

.PHONY: help install install-dev lint format test clean \
        qdrant-up qdrant-down ollama-pull ollama-up \
        docker-build docker-up docker-down run

# Configuration
PYTHON := python
VENV := venv
VENV_BIN := $(VENV)/bin

# Auto-detect: use venv if it exists, otherwise use system Python
# This makes Makefile work both locally (with venv) and in CI (without venv)
ifeq ($(wildcard $(VENV_BIN)/pip),)
    # venv doesn't exist — use system binaries (CI environment)
    PIP     := pip
    PYTEST  := pytest
    RUFF    := ruff
	BLACK   := black
else
    # venv exists — use venv binaries (local environment)
    PIP     := $(VENV_BIN)/pip
    PYTEST  := $(VENV_BIN)/pytest
    RUFF    := $(VENV_BIN)/ruff
	BLACK   := $(VENV_BIN)/black

endif

# Default target: show help
help:
	@echo "Available commands:"
	@echo ""
	@echo "  Setup"
	@echo "    make install        Install production dependencies"
	@echo "    make install-dev    Install dev dependencies + pre-commit hooks"
	@echo ""
	@echo "  Code quality"
	@echo "    make lint           Run ruff linter"
	@echo "    make format         Run black formatter"
	@echo ""
	@echo "  Tests"
	@echo "    make test           Run all tests"
	@echo "    make test-cov       Run tests with coverage report"
	@echo ""
	@echo "  Services (local)"
	@echo "    make qdrant-up      Start Qdrant container"
	@echo "    make qdrant-down    Stop Qdrant container"
	@echo "    make ollama-pull    Pull Mistral + LLaVA models"
	@echo "    make ollama-up      Start Ollama server"
	@echo ""
	@echo "  Docker"
	@echo "    make docker-build   Build app Docker image"
	@echo "    make docker-up      Start full stack (app + qdrant + ollama)"
	@echo "    make docker-down    Stop full stack"
	@echo ""
	@echo "  App"
	@echo "    make run            Run Gradio app locally"
	@echo "    make clean          Remove cache and temp files"
	@echo ""

# Setup
install:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -e .

install-dev:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt
	$(PIP) install -e .
	pre-commit install
	@echo " Dev environment setup complete! "

# Code quality
lint:
	$(RUFF) check .

format:
	$(BLACK) .
	$(RUFF) check . --fix

# Tests
test:
	$(PYTEST) tests/ -v

test-cov:
	$(PYTEST) tests/ -v --cov=app --cov-report=term-missing --cov-report=html
	@echo "HTML coverage report generated at htmlcov/index.html"

# Local services
qdrant-up:
	docker run -d --name qdrant \
		-p 6333:6333 \
		-v qdrant_data:/qdrant/storage \
		qdrant/qdrant:latest
	@echo "Qdrant running at http://localhost:6333"

qdrant-down:
	docker stop qdrant && docker rm qdrant
	@echo "Qdrant stopped and removed"

ollama-pull:
	ollama pull mistral:7b-instruct
	ollama pull llava:7b
	@echo "Ollama models downloaded"

ollama-up:
	ollama serve &
	@echo "Ollama server started"

# Docker
docker-build:
	docker build -f docker/Dockerfile -t multimodal-rag:latest .

docker-up:
	docker compose -f docker/docker-compose.yml up -d
	@echo "Stack running - Gradio at http://localhost:7860"

docker-down:
	docker compose -f docker/docker-compose.yml down
	@echo "Stack stopped"

# App
run:
	python -m app.ui.gradio_app

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete
	@echo "🧹 Cleaned"