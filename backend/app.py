"""
Elder Trading System - Main Application
Flask application entry point

Modular Structure:
- models/database.py    - Database operations
- services/indicators.py - Technical indicator calculations
- services/screener.py  - Stock screening logic
- routes/api.py         - REST API endpoints
"""

import os
from flask import Flask, render_template, g
from flask_cors import CORS

from routes.api import api
from models.database import get_database


def create_app():
    """Application factory"""
    app = Flask(__name__)
    CORS(app)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get(
        'SECRET_KEY', 
        'elder-trading-secret-key-change-in-production'
    )
    
    # Initialize database
    get_database()
    
    # Register blueprints
    app.register_blueprint(api)
    
    # Serve frontend
    @app.route('/')
    def index():
        return render_template('index.html')
    
    # Cleanup
    @app.teardown_appcontext
    def close_db(exception):
        db = g.pop('db', None)
        if db is not None:
            db.close()
    
    return app


# Create app instance
app = create_app()


if __name__ == '__main__':
    app.run(
        host='0.0.0.0', 
        port=int(os.environ.get('PORT', 8000)), 
        debug=os.environ.get('DEBUG', 'false').lower() == 'true'
    )
