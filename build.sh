#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Starting build process..."
echo "Current directory: $(pwd)"
echo "Listing files:"
ls -la

echo "Setting up Python environment..."
pip install -r requirements.txt

echo "Setting up environment variables..."
export FLASK_APP=app.py
export FLASK_ENV=production

echo "Running database migrations..."
flask db upgrade

echo "Initializing database and creating admin user..."
python init_db.py

echo "Verifying admin user..."
python -c "from app import app, db, User; app.app_context().push(); admin = User.query.filter_by(username='admin').first(); print(f'Admin exists: {admin is not None}')"

echo "Build process completed!"

echo "Starting Gunicorn server..."
gunicorn --bind 0.0.0.0:$PORT app:app 