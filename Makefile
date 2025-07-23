.PHONY: test coverage coverage-html coverage-report install-dev clean

# Install development dependencies
install-dev:
	pip install -e .[dev]

# Run tests with coverage
test:
	pytest -m "not integration"

# Run all tests including integration tests (requires HTCondor)
test-all:
	pytest

# Run tests with coverage and generate HTML report
coverage:
	pytest --cov=dask_iclx --cov-report=html --cov-report=term-missing -m "not integration"

# Run coverage for all tests including integration
coverage-all:
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

test-integration-report:
    # Produce the report in markdown and convert it to HTML
	$(eval GIT_HASH := $(shell git rev-parse --short HEAD))
	@{ \
	pytest -m "integration" --md-report --md-report-verbose=2 --md-report-output=".reports/$(GIT_HASH).md"; \
	echo $$? > ".reports/$(GIT_HASH).status"; \
	}
	pandoc -s -o ".reports/$(GIT_HASH).html" ".reports/$(GIT_HASH).md" --css=./style.css

	jq -n --argjson status "$(shell cat .reports/$(GIT_HASH).status)" \
		--arg current_hash "$(GIT_HASH)" \
		--arg latest_hash "$(shell git rev-parse --short HEAD)" \
		'{"schemaVersion": 1, "label": "Local tests", "message": (if $$current_hash != $$latest_hash then "outdated" elif $$status == 0 then "passing" else "failing" end), "color": (if $$current_hash != $$latest_hash then "yellow" elif $$status == 0 then "green" else "red" end)}' \
		> ".reports/$(GIT_HASH).json"
	cp ".reports/$(GIT_HASH).json" "/home/hep/tr1123/public_html/dask-iclx/latest.json"
	cp ".reports/$(GIT_HASH).html" "/home/hep/tr1123/public_html/dask-iclx/latest.html"
	cp ".reports/style.css" "/home/hep/tr1123/public_html/dask-iclx/style.css"

test-slow:
	pytest -m slow

# Clean coverage files
clean:
	rm -rf htmlcov/
	rm -f .coverage
	rm -f coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
