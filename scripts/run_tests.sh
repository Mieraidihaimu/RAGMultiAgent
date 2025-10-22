#!/bin/bash

# Integration Test Runner Script
# This script helps run integration tests with various options

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default values
PROFILE="test"
VERBOSE=""
SPECIFIC_TEST=""
KEEP_RUNNING=false

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Run integration tests for AI Thought Processor

OPTIONS:
    -h, --help              Show this help message
    -v, --verbose           Run tests with verbose output
    -t, --test FILE         Run specific test file (e.g., test_health.py)
    -k, --keep              Keep test container running after tests
    -c, --coverage          Run with coverage report
    -d, --debug             Run container in interactive mode for debugging

EXAMPLES:
    # Run all tests
    $0

    # Run with verbose output
    $0 -v

    # Run specific test file
    $0 -t test_anonymous_user.py

    # Run with coverage
    $0 -c

    # Debug mode (interactive shell)
    $0 -d

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -v|--verbose)
            VERBOSE="-v"
            shift
            ;;
        -t|--test)
            SPECIFIC_TEST="tests/$2"
            shift 2
            ;;
        -k|--keep)
            KEEP_RUNNING=true
            shift
            ;;
        -c|--coverage)
            VERBOSE="--cov=. -v"
            shift
            ;;
        -d|--debug)
            print_info "Starting test container in debug mode..."
            docker-compose --profile test run --rm integration-tests bash
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose is not installed or not in PATH"
    exit 1
fi

# Ensure services are running
print_info "Checking if required services are running..."
if ! docker ps | grep -q thoughtprocessor-api; then
    print_warning "API service not running. Starting services..."
    docker-compose up -d api db redis kafka
    print_info "Waiting for services to be ready..."
    sleep 10
fi

# Build test image
print_info "Building test container..."
docker-compose --profile test build integration-tests

# Run tests
if [ -n "$SPECIFIC_TEST" ]; then
    print_info "Running specific test: $SPECIFIC_TEST"
    TEST_CMD="pytest $SPECIFIC_TEST $VERBOSE"
else
    print_info "Running all integration tests..."
    TEST_CMD="pytest $VERBOSE"
fi

if [ "$KEEP_RUNNING" = true ]; then
    docker-compose --profile test run integration-tests $TEST_CMD
else
    docker-compose --profile test run --rm integration-tests $TEST_CMD
fi

TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
    print_info "✅ All tests passed!"
else
    print_error "❌ Some tests failed. Exit code: $TEST_EXIT_CODE"
    exit $TEST_EXIT_CODE
fi
