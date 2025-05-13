#!/bin/bash
set -e  # Exit on error

echo "Starting build process..."
echo "Current directory: $(pwd)"
echo "Listing files:"
ls -la

echo "Setting up Python environment..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "Running database migrations..."
export FLASK_APP=app.py
flask db upgrade

echo "Starting Gunicorn server..."
gunicorn --bind 0.0.0.0:$PORT app:app 