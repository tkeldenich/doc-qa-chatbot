#!/bin/bash
set -e

echo "Running tests with coverage..."
pytest --cov=app --cov-report=html --cov-report=term-missing

echo "Coverage report generated in htmlcov/"
echo "Open htmlcov/index.html in your browser to view detailed report"

# Optional: Open browser automatically (uncomment for your OS)
open htmlcov/index.html  # Mac
# start htmlcov/index.html # Windows
# xdg-open htmlcov/index.html # Linux
