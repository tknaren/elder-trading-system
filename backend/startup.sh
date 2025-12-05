#!/bin/bash

# ============================================
# Elder Trading System - Azure Deployment Script
# ============================================

echo "🚀 Starting Elder Trading System..."

# Create data directory (Required for SQLite persistence)
mkdir -p /home/data

# Initialize database
# Note: We run this in the background or ensure it's idempotent
python -c "from app import init_db, app; app.app_context().push(); init_db()"

# Start the application with Gunicorn
# Azure looks for the app on port 8000 by default
gunicorn --bind=0.0.0.0:8000 --workers=2 --timeout=120 app:app