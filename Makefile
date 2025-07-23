.PHONY: test coverage coverage-html coverage-report install-dev clean

# Install development dependencies
install-dev:
	pip install -e .[dev]

# Run tests with coverage
test:
	pytest

# Run tests with coverage and generate HTML report
coverage:
	pytest --cov=dask_iclx --cov-report=html --cov-report=term-missing

# Generate only HTML coverage report
coverage-html:
	pytest --cov=dask_iclx --cov-report=html

# Show coverage report in terminal
coverage-report:
	coverage report

# Run specific test markers
test-unit:
	pytest -m unit

test-integration:
	pytest -m integration

test-slow:
	pytest -m slow

# Clean coverage files
clean:
	rm -rf htmlcov/
	rm -f .coverage
	rm -f coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
