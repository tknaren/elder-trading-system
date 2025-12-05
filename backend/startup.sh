#!/bin/bash

# ============================================
# Elder Trading System - Azure Startup Script
# ============================================

echo "🚀 Starting Elder Trading System..."

# Create data directory for SQLite
mkdir -p /home/data

# Set environment variables
export DATABASE_PATH=${DATABASE_PATH:-/home/data/elder_trading.db}

# Ensure the backend directory is in PYTHONPATH
export PYTHONPATH="${PWD}:${PYTHONPATH}"

# Start the application with Gunicorn
exec gunicorn --bind=0.0.0.0:8000 --workers=2 --timeout=120 --access-logfile=- --error-logfile=- wsgi:app
