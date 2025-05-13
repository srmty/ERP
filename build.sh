#!/bin/bash
# Exit on error
set -e

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Setting up environment variables..."
export FLASK_APP=app.py
export FLASK_ENV=production

echo "Running database migrations..."
flask db upgrade

echo "Creating database tables..."
python -c "from app import app, db; app.app_context().push(); db.create_all()"

echo "Starting the application..."
gunicorn app:app 