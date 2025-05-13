#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Starting build process..."
echo "Current directory: $(pwd)"
echo "Listing files:"
ls -la

echo "Setting up Python environment..."
pip install -r requirements.txt

echo "Running database migrations..."
export FLASK_APP=app.py
flask db upgrade

echo "Initializing database and creating admin user..."
python init_db.py

echo "Build process completed!"

echo "Starting Gunicorn server..."
gunicorn --bind 0.0.0.0:$PORT app:app 