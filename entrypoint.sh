#!/bin/bash
set -e

# Run database migrations
echo "Running database migrations..."
flask db upgrade

# Start the application
echo "Starting application with Gunicorn..."
exec "$@"
