"""
Elder Trading System - Backend API
Flask application with SQLite database for Azure Web App deployment
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, g, render_template, send_from_directory
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import numpy as np
from werkzeug.security import generate_password_hash, check_password_hash
import jwt

# ============ APP CONFIGURATION ============
app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'elder-trading-secret-key-change-in-production')
app.config['DATABASE'] = os.environ.get('DATABASE_PATH', '/home/data/elder_trading.db')

# Ensure data directory exists
os.makedirs(os.path.dirname(app.config['DATABASE']), exist_ok=True)

# ============ DATABASE SETUP ============
def get_db():
    """Get database connection for current request"""
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    """Close database connection at end of request"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize database with all required tables"""
    db = get_db()
    db.executescript('''
        -- Users table
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Account settings
        CREATE TABLE IF NOT EXISTS account_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            account_name TEXT NOT NULL,
            market TEXT NOT NULL,  -- 'US' or 'IN'
            trading_capital REAL NOT NULL,
            risk_per_trade REAL DEFAULT 2.0,
            max_monthly_drawdown REAL DEFAULT 6.0,
            target_rr REAL DEFAULT 2.0,
            max_open_positions INTEGER DEFAULT 5,
            currency TEXT DEFAULT 'USD',
            broker TEXT,  -- 'IBKR' or 'ZERODHA'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        
        -- Strategies (configurable)
        CREATE TABLE IF NOT EXISTS strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            is_active BOOLEAN DEFAULT 1,
            config JSON NOT NULL,  -- Strategy configuration
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        
        -- APGAR scoring parameters (configurable per strategy)
        CREATE TABLE IF NOT EXISTS apgar_parameters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_id INTEGER NOT NULL,
            parameter_name TEXT NOT NULL,
            parameter_label TEXT NOT NULL,
            options JSON NOT NULL,  -- [{score: 2, label: "..."}, ...]
            display_order INTEGER DEFAULT 0,
            FOREIGN KEY (strategy_id) REFERENCES strategies(id)
        );
        
        -- Weekly scans
        CREATE TABLE IF NOT EXISTS weekly_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            market TEXT NOT NULL,
            scan_date DATE NOT NULL,
            week_start DATE NOT NULL,
            week_end DATE NOT NULL,
            results JSON NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        
        -- Daily scans (linked to weekly)
        CREATE TABLE IF NOT EXISTS daily_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            weekly_scan_id INTEGER NOT NULL,
            market TEXT NOT NULL,
            scan_date DATE NOT NULL,
            results JSON NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (weekly_scan_id) REFERENCES weekly_scans(id)
        );
        
        -- Trade setups (A-trades picked from daily scan)
        CREATE TABLE IF NOT EXISTS trade_setups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            daily_scan_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            market TEXT NOT NULL,
            strategy_id INTEGER NOT NULL,
            apgar_score INTEGER,
            apgar_details JSON,
            entry_price REAL,
            stop_loss REAL,
            target_price REAL,
            position_size INTEGER,
            risk_amount REAL,
            status TEXT DEFAULT 'pending',  -- pending, active, closed
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (daily_scan_id) REFERENCES daily_scans(id),
            FOREIGN KEY (strategy_id) REFERENCES strategies(id)
        );
        
        -- Trade journal
        CREATE TABLE IF NOT EXISTS trade_journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            trade_setup_id INTEGER,
            symbol TEXT NOT NULL,
            market TEXT NOT NULL,
            direction TEXT DEFAULT 'LONG',
            entry_date DATE,
            entry_price REAL,
            exit_date DATE,
            exit_price REAL,
            position_size INTEGER,
            stop_loss REAL,
            target_price REAL,
            pnl REAL,
            pnl_percent REAL,
            fees REAL DEFAULT 0,
            strategy_id INTEGER,
            apgar_score INTEGER,
            notes TEXT,
            chart_screenshot TEXT,  -- Base64 or URL
            lessons_learned TEXT,
            grade TEXT,  -- A, B, C, D, F
            status TEXT DEFAULT 'open',  -- open, closed, cancelled
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (trade_setup_id) REFERENCES trade_setups(id),
            FOREIGN KEY (strategy_id) REFERENCES strategies(id)
        );
        
        -- Daily checklist
        CREATE TABLE IF NOT EXISTS daily_checklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            checklist_date DATE NOT NULL,
            items JSON NOT NULL,  -- {step1: true, step2: false, ...}
            completed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, checklist_date)
        );
        
        -- Watchlists
        CREATE TABLE IF NOT EXISTS watchlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            market TEXT NOT NULL,
            symbols JSON NOT NULL,
            is_default BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    ''')
    
    # Insert default strategy (Elder Triple Screen)
    cursor = db.execute('SELECT COUNT(*) FROM strategies')
    if cursor.fetchone()[0] == 0:
        # Create default user
        db.execute('''
            INSERT OR IGNORE INTO users (username, password_hash)
            VALUES (?, ?)
        ''', ('default', generate_password_hash('elder2024')))
        
        # Get user id
        cursor = db.execute('SELECT id FROM users WHERE username = ?', ('default',))
        user_id = cursor.fetchone()[0]
        
        # Insert Elder Triple Screen strategy
        elder_config = {
            "name": "Elder Triple Screen",
            "timeframes": {
                "screen1": "weekly",
                "screen2": "daily",
                "screen3": "intraday"
            },
            "indicators": {
                "weekly": ["EMA_22", "MACD_Histogram"],
                "daily": ["Force_Index_2", "Stochastic_14", "EMA_22"]
            }
        }
        
        db.execute('''
            INSERT INTO strategies (user_id, name, description, config)
            VALUES (?, ?, ?, ?)
        ''', (user_id, 'Elder Triple Screen', 
              'Dr. Alexander Elder\'s Triple Screen Trading System', 
              json.dumps(elder_config)))
        
        strategy_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
        
        # Insert APGAR parameters for Elder strategy
        apgar_params = [
            ('weekly_ema', 'Weekly EMA (22) Slope', [
                {"score": 2, "label": "Strongly Rising"},
                {"score": 1, "label": "Rising"},
                {"score": 0, "label": "Flat/Falling"}
            ], 1),
            ('weekly_macd', 'Weekly MACD-Histogram', [
                {"score": 2, "label": "Rising + Divergence"},
                {"score": 1, "label": "Rising"},
                {"score": 0, "label": "Falling"}
            ], 2),
            ('force_index', 'Daily Force Index (2-EMA)', [
                {"score": 2, "label": "Below Zero + Uptick"},
                {"score": 1, "label": "Below Zero"},
                {"score": 0, "label": "Above Zero"}
            ], 3),
            ('stochastic', 'Daily Stochastic', [
                {"score": 2, "label": "Below 30 (Oversold)"},
                {"score": 1, "label": "30-50"},
                {"score": 0, "label": "Above 50"}
            ], 4),
            ('price_ema', 'Price vs 22-Day EMA', [
                {"score": 2, "label": "At or Below EMA"},
                {"score": 1, "label": "Slightly Above (<2%)"},
                {"score": 0, "label": "Far Above (Overpaying)"}
            ], 5)
        ]
        
        for param in apgar_params:
            db.execute('''
                INSERT INTO apgar_parameters (strategy_id, parameter_name, parameter_label, options, display_order)
                VALUES (?, ?, ?, ?, ?)
            ''', (strategy_id, param[0], param[1], json.dumps(param[2]), param[3]))
        
        # Insert default watchlists
        nasdaq_100 = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AMD', 'AVGO', 'NFLX',
                      'COST', 'PEP', 'ADBE', 'CSCO', 'INTC', 'QCOM', 'TXN', 'INTU', 'AMAT', 'MU',
                      'LRCX', 'KLAC', 'SNPS', 'CDNS', 'MRVL', 'ON', 'NXPI', 'ADI', 'MCHP', 'FTNT']
        
        nifty_50 = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS', 'HINDUNILVR.NS',
                    'SBIN.NS', 'BHARTIARTL.NS', 'ITC.NS', 'KOTAKBANK.NS', 'LT.NS', 'AXISBANK.NS',
                    'ASIANPAINT.NS', 'MARUTI.NS', 'TITAN.NS', 'SUNPHARMA.NS', 'ULTRACEMCO.NS',
                    'BAJFINANCE.NS', 'WIPRO.NS', 'HCLTECH.NS', 'TATAMOTORS.NS', 'POWERGRID.NS',
                    'NTPC.NS', 'M&M.NS', 'JSWSTEEL.NS', 'TATASTEEL.NS', 'TECHM.NS', 'INDUSINDBK.NS',
                    'HINDALCO.NS', 'ADANIENT.NS']
        
        db.execute('''
            INSERT INTO watchlists (user_id, name, market, symbols, is_default)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, 'NASDAQ 100', 'US', json.dumps(nasdaq_100), 1))
        
        db.execute('''
            INSERT INTO watchlists (user_id, name, market, symbols, is_default)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, 'NIFTY 50', 'IN', json.dumps(nifty_50), 1))
        
        # Insert default account settings
        db.execute('''
            INSERT INTO account_settings (user_id, account_name, market, trading_capital, currency, broker)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, 'ISA Account', 'US', 6000, 'GBP', 'IBKR'))
        
        db.execute('''
            INSERT INTO account_settings (user_id, account_name, market, trading_capital, currency, broker)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, 'Zerodha Account', 'IN', 570749, 'INR', 'ZERODHA'))
    
    db.commit()

# ============ AUTHENTICATION ============
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            # For development, use default user
            g.user_id = 1
            return f(*args, **kwargs)
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            g.user_id = data['user_id']
        except:
            g.user_id = 1  # Fallback to default user
        return f(*args, **kwargs)
    return decorated

# ============ TECHNICAL ANALYSIS FUNCTIONS ============
def calculate_ema(data, period):
    """Calculate Exponential Moving Average"""
    return data.ewm(span=period, adjust=False).mean()

def calculate_macd(closes, fast=12, slow=26, signal=9):
    """Calculate MACD, Signal line, and Histogram"""
    ema_fast = calculate_ema(closes, fast)
    ema_slow = calculate_ema(closes, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_force_index(closes, volumes, period=2):
    """Calculate Force Index"""
    fi = (closes - closes.shift(1)) * volumes
    return calculate_ema(fi, period)

def calculate_stochastic(highs, lows, closes, period=14):
    """Calculate Stochastic Oscillator"""
    lowest_low = lows.rolling(window=period).min()
    highest_high = highs.rolling(window=period).max()
    k = 100 * (closes - lowest_low) / (highest_high - lowest_low)
    return k

def calculate_rsi(closes, period=14):
    """Calculate RSI"""
    delta = closes.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_atr(highs, lows, closes, period=14):
    """Calculate Average True Range"""
    tr1 = highs - lows
    tr2 = abs(highs - closes.shift(1))
    tr3 = abs(lows - closes.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def analyze_stock(symbol, period='6mo'):
    """Fetch and analyze a stock with all technical indicators"""
    try:
        ticker = yf.Ticker(symbol)
        
        # Get historical data
        hist = ticker.history(period=period)
        if hist.empty:
            return None
        
        # Get quote info
        info = ticker.info
        
        closes = hist['Close']
        highs = hist['High']
        lows = hist['Low']
        volumes = hist['Volume']
        
        # Calculate indicators
        ema_22 = calculate_ema(closes, 22)
        ema_13 = calculate_ema(closes, 13)
        macd_line, macd_signal, macd_hist = calculate_macd(closes)
        force_index = calculate_force_index(closes, volumes, 2)
        stochastic = calculate_stochastic(highs, lows, closes, 14)
        rsi = calculate_rsi(closes, 14)
        atr = calculate_atr(highs, lows, closes, 14)
        
        # Get latest values
        current_price = closes.iloc[-1]
        prev_close = closes.iloc[-2] if len(closes) > 1 else current_price
        
        # Calculate weekly trend (using last 5 days as proxy)
        ema_slope = ema_22.iloc[-1] - ema_22.iloc[-6] if len(ema_22) > 6 else 0
        weekly_trend = 'up' if ema_slope > 0 else 'down' if ema_slope < 0 else 'neutral'
        
        # MACD histogram trend
        macd_hist_rising = macd_hist.iloc[-1] > macd_hist.iloc[-2] if len(macd_hist) > 1 else False
        
        # Signal strength calculation
        signal_strength = 5
        if weekly_trend == 'up': signal_strength += 2
        if macd_hist_rising: signal_strength += 1
        if force_index.iloc[-1] < 0: signal_strength += 1
        if stochastic.iloc[-1] < 50: signal_strength += 1
        if current_price <= ema_22.iloc[-1] * 1.02: signal_strength += 1
        signal_strength = min(10, max(1, signal_strength))
        
        # Calculate channel width
        channel_width = ((atr.iloc[-1] * 2) / current_price * 100)
        
        # Price vs EMA percentage
        price_vs_ema = ((current_price / ema_22.iloc[-1]) - 1) * 100
        
        return {
            'symbol': symbol,
            'name': info.get('shortName', info.get('longName', symbol)),
            'sector': info.get('sector', 'Unknown'),
            'price': round(current_price, 2),
            'change': round(current_price - prev_close, 2),
            'changePercent': round(((current_price - prev_close) / prev_close) * 100, 2),
            'volume': int(volumes.iloc[-1]),
            'avgVolume': int(info.get('averageDailyVolume10Day', 0)),
            'high52w': info.get('fiftyTwoWeekHigh', 0),
            'low52w': info.get('fiftyTwoWeekLow', 0),
            'marketCap': info.get('marketCap', 0),
            
            # Technical indicators
            'ema22': round(ema_22.iloc[-1], 2),
            'ema13': round(ema_13.iloc[-1], 2),
            'macdLine': round(macd_line.iloc[-1], 4),
            'macdSignal': round(macd_signal.iloc[-1], 4),
            'macdHistogram': round(macd_hist.iloc[-1], 4),
            'macdHistogramPrev': round(macd_hist.iloc[-2], 4) if len(macd_hist) > 1 else 0,
            'forceIndex': round(force_index.iloc[-1], 2),
            'stochastic': round(stochastic.iloc[-1], 2),
            'rsi': round(rsi.iloc[-1], 2),
            'atr': round(atr.iloc[-1], 2),
            
            # Analysis
            'weeklyTrend': weekly_trend,
            'macdRising': macd_hist_rising,
            'signalStrength': signal_strength,
            'channelWidth': round(channel_width, 1),
            'grade': 'A' if signal_strength >= 8 else 'B' if signal_strength >= 6 else 'C',
            'priceVsEma': round(price_vs_ema, 2),
            
            # Suggested levels (3% stop by default)
            'suggestedEntry': round(current_price, 2),
            'suggestedStop': round(current_price * 0.97, 2),
            'suggestedTarget': round(current_price * 1.06, 2)  # 1:2 R:R
        }
    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        return None

# ============ API ROUTES ============

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

# --- Authentication ---
@app.route('/api/auth/login', methods=['POST'])
def login():
    """User login"""
    data = request.get_json()
    db = get_db()
    
    user = db.execute('SELECT * FROM users WHERE username = ?', 
                      (data.get('username'),)).fetchone()
    
    if user and check_password_hash(user['password_hash'], data.get('password', '')):
        token = jwt.encode({
            'user_id': user['id'],
            'exp': datetime.utcnow() + timedelta(days=7)
        }, app.config['SECRET_KEY'])
        
        return jsonify({'token': token, 'username': user['username']})
    
    return jsonify({'error': 'Invalid credentials'}), 401

# --- Account Settings ---
@app.route('/api/settings', methods=['GET'])
@token_required
def get_settings():
    """Get all account settings for user"""
    db = get_db()
    settings = db.execute('''
        SELECT * FROM account_settings WHERE user_id = ?
    ''', (g.user_id,)).fetchall()
    
    return jsonify([dict(s) for s in settings])

@app.route('/api/settings', methods=['POST'])
@token_required
def create_setting():
    """Create new account setting"""
    data = request.get_json()
    db = get_db()
    
    db.execute('''
        INSERT INTO account_settings (user_id, account_name, market, trading_capital, 
                                       risk_per_trade, max_monthly_drawdown, target_rr, 
                                       max_open_positions, currency, broker)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (g.user_id, data['account_name'], data['market'], data['trading_capital'],
          data.get('risk_per_trade', 2), data.get('max_monthly_drawdown', 6),
          data.get('target_rr', 2), data.get('max_open_positions', 5),
          data['currency'], data.get('broker')))
    db.commit()
    
    return jsonify({'message': 'Setting created successfully'})

@app.route('/api/settings/<int:id>', methods=['PUT'])
@token_required
def update_setting(id):
    """Update account setting"""
    data = request.get_json()
    db = get_db()
    
    db.execute('''
        UPDATE account_settings 
        SET account_name = ?, trading_capital = ?, risk_per_trade = ?,
            max_monthly_drawdown = ?, target_rr = ?, max_open_positions = ?,
            currency = ?, broker = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_id = ?
    ''', (data['account_name'], data['trading_capital'], data['risk_per_trade'],
          data['max_monthly_drawdown'], data['target_rr'], data['max_open_positions'],
          data['currency'], data.get('broker'), id, g.user_id))
    db.commit()
    
    return jsonify({'message': 'Setting updated successfully'})

# --- Strategies ---
@app.route('/api/strategies', methods=['GET'])
@token_required
def get_strategies():
    """Get all strategies"""
    db = get_db()
    strategies = db.execute('''
        SELECT * FROM strategies WHERE user_id = ?
    ''', (g.user_id,)).fetchall()
    
    result = []
    for s in strategies:
        strategy = dict(s)
        strategy['config'] = json.loads(strategy['config'])
        
        # Get APGAR parameters
        params = db.execute('''
            SELECT * FROM apgar_parameters WHERE strategy_id = ? ORDER BY display_order
        ''', (s['id'],)).fetchall()
        strategy['apgar_parameters'] = [
            {**dict(p), 'options': json.loads(p['options'])} for p in params
        ]
        
        result.append(strategy)
    
    return jsonify(result)

@app.route('/api/strategies', methods=['POST'])
@token_required
def create_strategy():
    """Create new strategy with APGAR parameters"""
    data = request.get_json()
    db = get_db()
    
    db.execute('''
        INSERT INTO strategies (user_id, name, description, config)
        VALUES (?, ?, ?, ?)
    ''', (g.user_id, data['name'], data.get('description', ''), json.dumps(data['config'])))
    
    strategy_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
    
    # Insert APGAR parameters
    for i, param in enumerate(data.get('apgar_parameters', [])):
        db.execute('''
            INSERT INTO apgar_parameters (strategy_id, parameter_name, parameter_label, options, display_order)
            VALUES (?, ?, ?, ?, ?)
        ''', (strategy_id, param['parameter_name'], param['parameter_label'], 
              json.dumps(param['options']), i))
    
    db.commit()
    return jsonify({'message': 'Strategy created', 'id': strategy_id})

# --- Watchlists ---
@app.route('/api/watchlists', methods=['GET'])
@token_required
def get_watchlists():
    """Get all watchlists"""
    db = get_db()
    watchlists = db.execute('''
        SELECT * FROM watchlists WHERE user_id = ?
    ''', (g.user_id,)).fetchall()
    
    return jsonify([{**dict(w), 'symbols': json.loads(w['symbols'])} for w in watchlists])

@app.route('/api/watchlists', methods=['POST'])
@token_required
def create_watchlist():
    """Create new watchlist"""
    data = request.get_json()
    db = get_db()
    
    db.execute('''
        INSERT INTO watchlists (user_id, name, market, symbols, is_default)
        VALUES (?, ?, ?, ?, ?)
    ''', (g.user_id, data['name'], data['market'], json.dumps(data['symbols']), 
          data.get('is_default', 0)))
    db.commit()
    
    return jsonify({'message': 'Watchlist created'})

@app.route('/api/watchlists/<int:id>', methods=['PUT'])
@token_required
def update_watchlist(id):
    """Update watchlist"""
    data = request.get_json()
    db = get_db()
    
    db.execute('''
        UPDATE watchlists SET name = ?, symbols = ? WHERE id = ? AND user_id = ?
    ''', (data['name'], json.dumps(data['symbols']), id, g.user_id))
    db.commit()
    
    return jsonify({'message': 'Watchlist updated'})

# --- Screener ---
@app.route('/api/screener/weekly', methods=['POST'])
@token_required
def run_weekly_screener():
    """Run weekly screener on watchlist"""
    data = request.get_json()
    market = data.get('market', 'US')
    watchlist_id = data.get('watchlist_id')
    
    db = get_db()
    
    # Get watchlist symbols
    if watchlist_id:
        watchlist = db.execute('SELECT symbols FROM watchlists WHERE id = ?', 
                               (watchlist_id,)).fetchone()
        symbols = json.loads(watchlist['symbols']) if watchlist else []
    else:
        # Get default watchlist for market
        watchlist = db.execute('''
            SELECT symbols FROM watchlists WHERE user_id = ? AND market = ? AND is_default = 1
        ''', (g.user_id, market)).fetchone()
        symbols = json.loads(watchlist['symbols']) if watchlist else []
    
    # Analyze each symbol
    results = []
    for symbol in symbols:
        analysis = analyze_stock(symbol)
        if analysis:
            # Weekly filter: Check if weekly trend is bullish
            if analysis['weeklyTrend'] == 'up' and analysis['macdRising']:
                results.append(analysis)
    
    # Sort by signal strength
    results.sort(key=lambda x: x['signalStrength'], reverse=True)
    
    # Calculate week boundaries
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    # Save scan results
    db.execute('''
        INSERT INTO weekly_scans (user_id, market, scan_date, week_start, week_end, results)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (g.user_id, market, today, week_start, week_end, json.dumps(results)))
    db.commit()
    
    scan_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
    
    return jsonify({
        'scan_id': scan_id,
        'market': market,
        'week_start': week_start.isoformat(),
        'week_end': week_end.isoformat(),
        'total_scanned': len(symbols),
        'passed_filter': len(results),
        'results': results
    })

@app.route('/api/screener/daily', methods=['POST'])
@token_required
def run_daily_screener():
    """Run daily screener on weekly scan results"""
    data = request.get_json()
    weekly_scan_id = data.get('weekly_scan_id')
    
    if not weekly_scan_id:
        return jsonify({'error': 'Weekly scan ID required'}), 400
    
    db = get_db()
    
    # Get weekly scan
    weekly_scan = db.execute('SELECT * FROM weekly_scans WHERE id = ?', 
                             (weekly_scan_id,)).fetchone()
    if not weekly_scan:
        return jsonify({'error': 'Weekly scan not found'}), 404
    
    weekly_results = json.loads(weekly_scan['results'])
    symbols = [r['symbol'] for r in weekly_results]
    
    # Re-analyze with daily focus
    results = []
    for symbol in symbols:
        analysis = analyze_stock(symbol)
        if analysis:
            # Daily filter: Force Index below zero, reasonable Stochastic
            if analysis['forceIndex'] < 0 or analysis['stochastic'] < 50:
                results.append(analysis)
    
    # Sort by signal strength
    results.sort(key=lambda x: x['signalStrength'], reverse=True)
    
    # Save daily scan
    today = datetime.now().date()
    db.execute('''
        INSERT INTO daily_scans (user_id, weekly_scan_id, market, scan_date, results)
        VALUES (?, ?, ?, ?, ?)
    ''', (g.user_id, weekly_scan_id, weekly_scan['market'], today, json.dumps(results)))
    db.commit()
    
    scan_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
    
    return jsonify({
        'scan_id': scan_id,
        'weekly_scan_id': weekly_scan_id,
        'total_from_weekly': len(symbols),
        'passed_daily_filter': len(results),
        'results': results
    })

@app.route('/api/screener/weekly/latest', methods=['GET'])
@token_required
def get_latest_weekly_scan():
    """Get latest weekly scan for current week"""
    market = request.args.get('market', 'US')
    
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    
    db = get_db()
    scan = db.execute('''
        SELECT * FROM weekly_scans 
        WHERE user_id = ? AND market = ? AND week_start = ?
        ORDER BY created_at DESC LIMIT 1
    ''', (g.user_id, market, week_start)).fetchone()
    
    if scan:
        return jsonify({
            'scan_id': scan['id'],
            'market': scan['market'],
            'scan_date': scan['scan_date'],
            'week_start': scan['week_start'],
            'week_end': scan['week_end'],
            'results': json.loads(scan['results'])
        })
    
    return jsonify({'message': 'No weekly scan found for current week'}), 404

# --- Stock Info ---
@app.route('/api/stock/<symbol>', methods=['GET'])
def get_stock_info(symbol):
    """Get detailed stock information and analysis"""
    analysis = analyze_stock(symbol)
    if analysis:
        return jsonify(analysis)
    return jsonify({'error': 'Stock not found'}), 404

@app.route('/api/stock/<symbol>/quote', methods=['GET'])
def get_stock_quote(symbol):
    """Get quick quote for a stock"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        hist = ticker.history(period='2d')
        
        current = hist['Close'].iloc[-1]
        prev = hist['Close'].iloc[-2] if len(hist) > 1 else current
        
        return jsonify({
            'symbol': symbol,
            'name': info.get('shortName', symbol),
            'price': round(current, 2),
            'change': round(current - prev, 2),
            'changePercent': round(((current - prev) / prev) * 100, 2),
            'volume': int(hist['Volume'].iloc[-1])
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Trade Setups ---
@app.route('/api/setups', methods=['GET'])
@token_required
def get_trade_setups():
    """Get trade setups"""
    status = request.args.get('status', 'pending')
    
    db = get_db()
    setups = db.execute('''
        SELECT ts.*, s.name as strategy_name 
        FROM trade_setups ts
        LEFT JOIN strategies s ON ts.strategy_id = s.id
        WHERE ts.user_id = ? AND ts.status = ?
        ORDER BY ts.created_at DESC
    ''', (g.user_id, status)).fetchall()
    
    return jsonify([{**dict(s), 'apgar_details': json.loads(s['apgar_details'] or '{}')} for s in setups])

@app.route('/api/setups', methods=['POST'])
@token_required
def create_trade_setup():
    """Create new trade setup from daily scan"""
    data = request.get_json()
    db = get_db()
    
    db.execute('''
        INSERT INTO trade_setups (user_id, daily_scan_id, symbol, market, strategy_id,
                                   apgar_score, apgar_details, entry_price, stop_loss,
                                   target_price, position_size, risk_amount, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (g.user_id, data['daily_scan_id'], data['symbol'], data['market'],
          data['strategy_id'], data['apgar_score'], json.dumps(data.get('apgar_details', {})),
          data['entry_price'], data['stop_loss'], data['target_price'],
          data['position_size'], data['risk_amount'], 'pending'))
    db.commit()
    
    setup_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
    return jsonify({'message': 'Trade setup created', 'id': setup_id})

@app.route('/api/setups/<int:id>/activate', methods=['POST'])
@token_required
def activate_trade_setup(id):
    """Activate a trade setup (create journal entry)"""
    db = get_db()
    
    setup = db.execute('SELECT * FROM trade_setups WHERE id = ? AND user_id = ?',
                       (id, g.user_id)).fetchone()
    if not setup:
        return jsonify({'error': 'Setup not found'}), 404
    
    # Update setup status
    db.execute('UPDATE trade_setups SET status = ? WHERE id = ?', ('active', id))
    
    # Create journal entry
    db.execute('''
        INSERT INTO trade_journal (user_id, trade_setup_id, symbol, market, entry_date,
                                    entry_price, position_size, stop_loss, target_price,
                                    strategy_id, apgar_score, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (g.user_id, id, setup['symbol'], setup['market'], datetime.now().date(),
          setup['entry_price'], setup['position_size'], setup['stop_loss'],
          setup['target_price'], setup['strategy_id'], setup['apgar_score'], 'open'))
    db.commit()
    
    journal_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
    return jsonify({'message': 'Trade activated', 'journal_id': journal_id})

# --- Trade Journal ---
@app.route('/api/journal', methods=['GET'])
@token_required
def get_journal_entries():
    """Get trade journal entries"""
    status = request.args.get('status')
    limit = request.args.get('limit', 50, type=int)
    
    db = get_db()
    
    if status:
        entries = db.execute('''
            SELECT tj.*, s.name as strategy_name 
            FROM trade_journal tj
            LEFT JOIN strategies s ON tj.strategy_id = s.id
            WHERE tj.user_id = ? AND tj.status = ?
            ORDER BY tj.created_at DESC LIMIT ?
        ''', (g.user_id, status, limit)).fetchall()
    else:
        entries = db.execute('''
            SELECT tj.*, s.name as strategy_name 
            FROM trade_journal tj
            LEFT JOIN strategies s ON tj.strategy_id = s.id
            WHERE tj.user_id = ?
            ORDER BY tj.created_at DESC LIMIT ?
        ''', (g.user_id, limit)).fetchall()
    
    return jsonify([dict(e) for e in entries])

@app.route('/api/journal', methods=['POST'])
@token_required
def create_journal_entry():
    """Create manual journal entry"""
    data = request.get_json()
    db = get_db()
    
    db.execute('''
        INSERT INTO trade_journal (user_id, symbol, market, direction, entry_date,
                                    entry_price, position_size, stop_loss, target_price,
                                    strategy_id, apgar_score, notes, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (g.user_id, data['symbol'], data['market'], data.get('direction', 'LONG'),
          data.get('entry_date'), data['entry_price'], data['position_size'],
          data['stop_loss'], data['target_price'], data.get('strategy_id'),
          data.get('apgar_score'), data.get('notes'), 'open'))
    db.commit()
    
    entry_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
    return jsonify({'message': 'Journal entry created', 'id': entry_id})

@app.route('/api/journal/<int:id>', methods=['PUT'])
@token_required
def update_journal_entry(id):
    """Update journal entry (close trade, add notes, etc.)"""
    data = request.get_json()
    db = get_db()
    
    entry = db.execute('SELECT * FROM trade_journal WHERE id = ? AND user_id = ?',
                       (id, g.user_id)).fetchone()
    if not entry:
        return jsonify({'error': 'Entry not found'}), 404
    
    # Calculate P&L if closing
    pnl = None
    pnl_percent = None
    if data.get('status') == 'closed' and data.get('exit_price'):
        exit_price = data['exit_price']
        entry_price = entry['entry_price']
        position_size = entry['position_size']
        
        pnl = (exit_price - entry_price) * position_size
        if entry['direction'] == 'SHORT':
            pnl = -pnl
        pnl -= data.get('fees', 0)
        pnl_percent = (pnl / (entry_price * position_size)) * 100
    
    db.execute('''
        UPDATE trade_journal 
        SET exit_date = ?, exit_price = ?, pnl = ?, pnl_percent = ?, fees = ?,
            notes = ?, lessons_learned = ?, grade = ?, status = ?, 
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_id = ?
    ''', (data.get('exit_date'), data.get('exit_price'), pnl, pnl_percent,
          data.get('fees', 0), data.get('notes'), data.get('lessons_learned'),
          data.get('grade'), data.get('status', entry['status']), id, g.user_id))
    
    # Also update trade setup status if linked
    if entry['trade_setup_id']:
        db.execute('UPDATE trade_setups SET status = ? WHERE id = ?',
                   (data.get('status', 'closed'), entry['trade_setup_id']))
    
    db.commit()
    return jsonify({'message': 'Entry updated', 'pnl': pnl, 'pnl_percent': pnl_percent})

@app.route('/api/journal/stats', methods=['GET'])
@token_required
def get_journal_stats():
    """Get trading statistics"""
    period = request.args.get('period', 'all')  # all, month, year
    
    db = get_db()
    
    # Base query
    where_clause = 'WHERE user_id = ? AND status = ?'
    params = [g.user_id, 'closed']
    
    if period == 'month':
        where_clause += ' AND exit_date >= date("now", "-30 days")'
    elif period == 'year':
        where_clause += ' AND exit_date >= date("now", "-365 days")'
    
    stats = db.execute(f'''
        SELECT 
            COUNT(*) as total_trades,
            SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
            SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
            SUM(pnl) as total_pnl,
            AVG(pnl) as avg_pnl,
            AVG(CASE WHEN pnl > 0 THEN pnl END) as avg_win,
            AVG(CASE WHEN pnl < 0 THEN pnl END) as avg_loss,
            MAX(pnl) as best_trade,
            MIN(pnl) as worst_trade
        FROM trade_journal
        {where_clause}
    ''', params).fetchone()
    
    result = dict(stats)
    result['win_rate'] = (result['winning_trades'] / result['total_trades'] * 100) if result['total_trades'] > 0 else 0
    
    return jsonify(result)

# --- Daily Checklist ---
@app.route('/api/checklist', methods=['GET'])
@token_required
def get_checklist():
    """Get today's checklist"""
    today = datetime.now().date()
    
    db = get_db()
    checklist = db.execute('''
        SELECT * FROM daily_checklist WHERE user_id = ? AND checklist_date = ?
    ''', (g.user_id, today)).fetchone()
    
    if checklist:
        return jsonify({
            'date': checklist['checklist_date'],
            'items': json.loads(checklist['items']),
            'completed': checklist['completed_at'] is not None
        })
    
    # Return default checklist items
    default_items = {
        'step1': False,
        'step2': False,
        'step3': False,
        'step4': False,
        'step5': False,
        'step6': False,
        'step7': False
    }
    
    return jsonify({
        'date': today.isoformat(),
        'items': default_items,
        'completed': False
    })

@app.route('/api/checklist', methods=['POST'])
@token_required
def update_checklist():
    """Update checklist items"""
    data = request.get_json()
    today = datetime.now().date()
    
    db = get_db()
    
    # Check if all items completed
    all_completed = all(data['items'].values())
    completed_at = datetime.now() if all_completed else None
    
    db.execute('''
        INSERT OR REPLACE INTO daily_checklist (user_id, checklist_date, items, completed_at)
        VALUES (?, ?, ?, ?)
    ''', (g.user_id, today, json.dumps(data['items']), completed_at))
    db.commit()
    
    return jsonify({'message': 'Checklist updated', 'completed': all_completed})

# ============ MAIN ============

# Serve frontend
@app.route('/')
def index():
    return render_template('index.html')

with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)), debug=False)
