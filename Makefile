# Makefile for warehouse management system
.PHONY: help test test-unit test-integration test-fast test-coverage clean install lint format

# Default target
help:
	@echo "Available targets:"
	@echo "  install      - Install dependencies"
	@echo "  test         - Run all tests"
	@echo "  test-unit    - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-fast    - Run fast tests only"
	@echo "  test-coverage - Run tests with coverage report"
	@echo "  lint         - Run code linting"
	@echo "  format       - Format code"
	@echo "  clean        - Clean generated files"

# Install dependencies
install:
	pip install -r requirements.txt

# Test targets
test:
	python -m pytest tests/ -v

test-unit:
	python -m pytest tests/unit/ -v

test-integration:
	python -m pytest tests/integration/ -v

test-fast:
	python -m pytest -m "not slow" -v

test-coverage:
	python -m pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

# Code quality
lint:
	python -m flake8 app/ --max-line-length=100 --ignore=E501,W503
	python -m pylint app/ --disable=C0103,R0903,W0622

format:
	python -m black app/ tests/ --line-length=100
	python -m isort app/ tests/

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf *.egg-info/

# Development setup
dev-setup: install
	pip install black flake8 pylint isort
	@echo "Development environment ready!"

# Run application
run:
	python main.py

# Database tests (with real DB connection)
test-db:
	python -m pytest tests/ -m database -v --tb=short