"""
Elder Trading System - API Routes
Flask Blueprint with all REST API endpoints
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
import json

from ..models.database import get_database
from ..services.screener import run_weekly_screen, run_daily_screen, scan_stock
from ..services.indicators import get_grading_criteria

api = Blueprint('api', __name__, url_prefix='/api')


def get_db():
    """Get database connection for current request"""
    if 'db' not in g:
        g.db = get_database().get_connection()
    return g.db


def get_user_id():
    """Get current user ID (default to 1 for now)"""
    return getattr(g, 'user_id', 1)


# ============ HEALTH CHECK ============
@api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '2.0.0'
    })


# ============ SCREENER ENDPOINTS ============
@api.route('/screener/weekly', methods=['POST'])
def weekly_screener():
    """
    Run weekly screener (Screen 1)
    
    Request body:
        market: 'US' or 'IN'
        watchlist_id: (optional) specific watchlist to scan
    
    Returns:
        Complete scan results with all stocks and indicators
    """
    data = request.get_json() or {}
    market = data.get('market', 'US')
    watchlist_id = data.get('watchlist_id')
    
    db = get_db()
    user_id = get_user_id()
    
    # Get symbols from watchlist
    symbols = None
    if watchlist_id:
        watchlist = db.execute(
            'SELECT symbols FROM watchlists WHERE id = ?', 
            (watchlist_id,)
        ).fetchone()
        if watchlist:
            symbols = json.loads(watchlist['symbols'])
    else:
        # Get default watchlist for market
        watchlist = db.execute('''
            SELECT symbols FROM watchlists 
            WHERE user_id = ? AND market = ? AND is_default = 1
        ''', (user_id, market)).fetchone()
        if watchlist:
            symbols = json.loads(watchlist['symbols'])
    
    # Run the screener
    results = run_weekly_screen(market, symbols)
    
    # Calculate week boundaries
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    # Save scan to database
    db.execute('''
        INSERT INTO weekly_scans 
        (user_id, market, scan_date, week_start, week_end, results, summary)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id, market, today, week_start, week_end,
        json.dumps(results['all_results']),
        json.dumps(results['summary'])
    ))
    db.commit()
    
    scan_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
    results['scan_id'] = scan_id
    results['week_start'] = week_start.isoformat()
    results['week_end'] = week_end.isoformat()
    
    return jsonify(results)


@api.route('/screener/daily', methods=['POST'])
def daily_screener():
    """
    Run daily screener (Screen 2) on weekly results
    
    Request body:
        weekly_scan_id: ID of weekly scan to use
    
    Returns:
        Daily screen results filtered from weekly
    """
    data = request.get_json() or {}
    weekly_scan_id = data.get('weekly_scan_id')
    
    if not weekly_scan_id:
        return jsonify({'error': 'weekly_scan_id required'}), 400
    
    db = get_db()
    user_id = get_user_id()
    
    # Get weekly scan results
    weekly_scan = db.execute(
        'SELECT * FROM weekly_scans WHERE id = ?',
        (weekly_scan_id,)
    ).fetchone()
    
    if not weekly_scan:
        return jsonify({'error': 'Weekly scan not found'}), 404
    
    # Get stocks that passed weekly screen
    weekly_results = json.loads(weekly_scan['results'])
    bullish_stocks = [r for r in weekly_results if r.get('weekly_bullish')]
    
    # Run daily screen
    results = run_daily_screen(bullish_stocks)
    
    # Save to database
    today = datetime.now().date()
    db.execute('''
        INSERT INTO daily_scans 
        (user_id, weekly_scan_id, market, scan_date, results)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        user_id, weekly_scan_id, weekly_scan['market'],
        today, json.dumps(results['all_results'])
    ))
    db.commit()
    
    scan_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
    results['scan_id'] = scan_id
    results['weekly_scan_id'] = weekly_scan_id
    
    return jsonify(results)


@api.route('/screener/criteria', methods=['GET'])
def get_criteria():
    """Get grading criteria explanation"""
    return jsonify({
        'criteria': get_grading_criteria(),
        'scoring': {
            'a_trade': 'Signal Strength ≥ 5 AND Impulse not RED',
            'b_trade': 'Signal Strength 3-4 AND Impulse GREEN/BLUE',
            'watch': 'Signal Strength 1-2',
            'avoid': 'Signal Strength ≤ 0 OR Impulse RED'
        }
    })


@api.route('/screener/weekly/latest', methods=['GET'])
def get_latest_weekly():
    """Get latest weekly scan for current week"""
    market = request.args.get('market', 'US')
    
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    
    db = get_db()
    user_id = get_user_id()
    
    scan = db.execute('''
        SELECT * FROM weekly_scans 
        WHERE user_id = ? AND market = ? AND week_start = ?
        ORDER BY created_at DESC LIMIT 1
    ''', (user_id, market, week_start)).fetchone()
    
    if scan:
        return jsonify({
            'scan_id': scan['id'],
            'market': scan['market'],
            'scan_date': scan['scan_date'],
            'week_start': scan['week_start'],
            'week_end': scan['week_end'],
            'results': json.loads(scan['results']),
            'summary': json.loads(scan['summary']) if scan['summary'] else None
        })
    
    return jsonify({'message': 'No weekly scan found for current week'}), 404


# ============ STOCK INFO ============
@api.route('/stock/<symbol>', methods=['GET'])
def get_stock_analysis(symbol):
    """Get complete analysis for a single stock"""
    analysis = scan_stock(symbol)
    if analysis:
        return jsonify(analysis)
    return jsonify({'error': f'Could not analyze {symbol}'}), 404


# ============ SETTINGS ============
@api.route('/settings', methods=['GET'])
def get_settings():
    """Get all account settings"""
    db = get_db()
    user_id = get_user_id()
    
    settings = db.execute(
        'SELECT * FROM account_settings WHERE user_id = ?',
        (user_id,)
    ).fetchall()
    
    return jsonify([dict(s) for s in settings])


@api.route('/settings', methods=['POST'])
def create_setting():
    """Create new account setting"""
    data = request.get_json()
    db = get_db()
    user_id = get_user_id()
    
    db.execute('''
        INSERT INTO account_settings 
        (user_id, account_name, market, trading_capital, risk_per_trade,
         max_monthly_drawdown, target_rr, max_open_positions, currency, broker)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id, data['account_name'], data['market'], data['trading_capital'],
        data.get('risk_per_trade', 2), data.get('max_monthly_drawdown', 6),
        data.get('target_rr', 2), data.get('max_open_positions', 5),
        data['currency'], data.get('broker')
    ))
    db.commit()
    
    return jsonify({'message': 'Setting created', 'id': db.execute('SELECT last_insert_rowid()').fetchone()[0]})


@api.route('/settings/<int:id>', methods=['PUT'])
def update_setting(id):
    """Update account setting"""
    data = request.get_json()
    db = get_db()
    user_id = get_user_id()
    
    db.execute('''
        UPDATE account_settings 
        SET account_name = ?, trading_capital = ?, risk_per_trade = ?,
            max_monthly_drawdown = ?, target_rr = ?, max_open_positions = ?,
            currency = ?, broker = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_id = ?
    ''', (
        data['account_name'], data['trading_capital'], data['risk_per_trade'],
        data['max_monthly_drawdown'], data['target_rr'], data['max_open_positions'],
        data['currency'], data.get('broker'), id, user_id
    ))
    db.commit()
    
    return jsonify({'message': 'Setting updated'})


# ============ STRATEGIES ============
@api.route('/strategies', methods=['GET'])
def get_strategies():
    """Get all strategies with APGAR parameters"""
    db = get_db()
    user_id = get_user_id()
    
    strategies = db.execute(
        'SELECT * FROM strategies WHERE user_id = ?',
        (user_id,)
    ).fetchall()
    
    result = []
    for s in strategies:
        strategy = dict(s)
        strategy['config'] = json.loads(strategy['config'])
        
        params = db.execute('''
            SELECT * FROM apgar_parameters 
            WHERE strategy_id = ? ORDER BY display_order
        ''', (s['id'],)).fetchall()
        
        strategy['apgar_parameters'] = [
            {**dict(p), 'options': json.loads(p['options'])} for p in params
        ]
        result.append(strategy)
    
    return jsonify(result)


# ============ WATCHLISTS ============
@api.route('/watchlists', methods=['GET'])
def get_watchlists():
    """Get all watchlists"""
    db = get_db()
    user_id = get_user_id()
    
    watchlists = db.execute(
        'SELECT * FROM watchlists WHERE user_id = ?',
        (user_id,)
    ).fetchall()
    
    return jsonify([
        {**dict(w), 'symbols': json.loads(w['symbols'])} for w in watchlists
    ])


@api.route('/watchlists', methods=['POST'])
def create_watchlist():
    """Create new watchlist"""
    data = request.get_json()
    db = get_db()
    user_id = get_user_id()
    
    db.execute('''
        INSERT INTO watchlists (user_id, name, market, symbols, is_default)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, data['name'], data['market'], json.dumps(data['symbols']), 0))
    db.commit()
    
    return jsonify({'message': 'Watchlist created'})


# ============ TRADE SETUPS ============
@api.route('/setups', methods=['GET'])
def get_setups():
    """Get trade setups"""
    status = request.args.get('status', 'pending')
    db = get_db()
    user_id = get_user_id()
    
    setups = db.execute('''
        SELECT ts.*, s.name as strategy_name 
        FROM trade_setups ts
        LEFT JOIN strategies s ON ts.strategy_id = s.id
        WHERE ts.user_id = ? AND ts.status = ?
        ORDER BY ts.created_at DESC
    ''', (user_id, status)).fetchall()
    
    return jsonify([
        {**dict(s), 'apgar_details': json.loads(s['apgar_details'] or '{}')} 
        for s in setups
    ])


@api.route('/setups', methods=['POST'])
def create_setup():
    """Create new trade setup"""
    data = request.get_json()
    db = get_db()
    user_id = get_user_id()
    
    db.execute('''
        INSERT INTO trade_setups 
        (user_id, daily_scan_id, symbol, market, strategy_id, apgar_score,
         apgar_details, entry_price, stop_loss, target_price, position_size,
         risk_amount, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id, data.get('daily_scan_id'), data['symbol'], data['market'],
        data.get('strategy_id', 1), data.get('apgar_score'),
        json.dumps(data.get('apgar_details', {})),
        data['entry_price'], data['stop_loss'], data['target_price'],
        data.get('position_size'), data.get('risk_amount'), 'pending'
    ))
    db.commit()
    
    return jsonify({'message': 'Setup created', 'id': db.execute('SELECT last_insert_rowid()').fetchone()[0]})


# ============ TRADE JOURNAL ============
@api.route('/journal', methods=['GET'])
def get_journal():
    """Get trade journal entries"""
    status = request.args.get('status')
    limit = request.args.get('limit', 50, type=int)
    
    db = get_db()
    user_id = get_user_id()
    
    if status:
        entries = db.execute('''
            SELECT * FROM trade_journal
            WHERE user_id = ? AND status = ?
            ORDER BY created_at DESC LIMIT ?
        ''', (user_id, status, limit)).fetchall()
    else:
        entries = db.execute('''
            SELECT * FROM trade_journal
            WHERE user_id = ?
            ORDER BY created_at DESC LIMIT ?
        ''', (user_id, limit)).fetchall()
    
    return jsonify([dict(e) for e in entries])


@api.route('/journal', methods=['POST'])
def create_journal_entry():
    """Create trade journal entry"""
    data = request.get_json()
    db = get_db()
    user_id = get_user_id()
    
    db.execute('''
        INSERT INTO trade_journal 
        (user_id, symbol, market, direction, entry_date, entry_price,
         position_size, stop_loss, target_price, strategy_id, apgar_score,
         notes, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id, data['symbol'], data['market'], data.get('direction', 'LONG'),
        data.get('entry_date'), data['entry_price'], data['position_size'],
        data['stop_loss'], data['target_price'], data.get('strategy_id'),
        data.get('apgar_score'), data.get('notes'), 'open'
    ))
    db.commit()
    
    return jsonify({'message': 'Entry created', 'id': db.execute('SELECT last_insert_rowid()').fetchone()[0]})


@api.route('/journal/<int:id>', methods=['PUT'])
def update_journal_entry(id):
    """Update/close trade journal entry"""
    data = request.get_json()
    db = get_db()
    user_id = get_user_id()
    
    entry = db.execute(
        'SELECT * FROM trade_journal WHERE id = ? AND user_id = ?',
        (id, user_id)
    ).fetchone()
    
    if not entry:
        return jsonify({'error': 'Entry not found'}), 404
    
    # Calculate P&L if closing
    pnl = pnl_percent = None
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
        SET exit_date = ?, exit_price = ?, pnl = ?, pnl_percent = ?,
            fees = ?, notes = ?, lessons_learned = ?, grade = ?,
            status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_id = ?
    ''', (
        data.get('exit_date'), data.get('exit_price'), pnl, pnl_percent,
        data.get('fees', 0), data.get('notes'), data.get('lessons_learned'),
        data.get('grade'), data.get('status', entry['status']), id, user_id
    ))
    db.commit()
    
    return jsonify({'message': 'Entry updated', 'pnl': pnl, 'pnl_percent': pnl_percent})


@api.route('/journal/stats', methods=['GET'])
def get_journal_stats():
    """Get trading statistics"""
    period = request.args.get('period', 'all')
    
    db = get_db()
    user_id = get_user_id()
    
    where = 'WHERE user_id = ? AND status = ?'
    params = [user_id, 'closed']
    
    if period == 'month':
        where += ' AND exit_date >= date("now", "-30 days")'
    elif period == 'year':
        where += ' AND exit_date >= date("now", "-365 days")'
    
    stats = db.execute(f'''
        SELECT 
            COUNT(*) as total_trades,
            SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
            SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
            SUM(pnl) as total_pnl,
            AVG(pnl) as avg_pnl,
            MAX(pnl) as best_trade,
            MIN(pnl) as worst_trade
        FROM trade_journal {where}
    ''', params).fetchone()
    
    result = dict(stats)
    result['win_rate'] = (
        (result['winning_trades'] / result['total_trades'] * 100) 
        if result['total_trades'] > 0 else 0
    )
    
    return jsonify(result)


# ============ CHECKLIST ============
@api.route('/checklist', methods=['GET'])
def get_checklist():
    """Get today's checklist"""
    today = datetime.now().date()
    db = get_db()
    user_id = get_user_id()
    
    checklist = db.execute('''
        SELECT * FROM daily_checklist 
        WHERE user_id = ? AND checklist_date = ?
    ''', (user_id, today)).fetchone()
    
    if checklist:
        return jsonify({
            'date': checklist['checklist_date'],
            'items': json.loads(checklist['items']),
            'completed': checklist['completed_at'] is not None
        })
    
    default_items = {f'step{i}': False for i in range(1, 8)}
    return jsonify({
        'date': today.isoformat(),
        'items': default_items,
        'completed': False
    })


@api.route('/checklist', methods=['POST'])
def update_checklist():
    """Update checklist"""
    data = request.get_json()
    today = datetime.now().date()
    db = get_db()
    user_id = get_user_id()
    
    all_done = all(data['items'].values())
    completed_at = datetime.now() if all_done else None
    
    db.execute('''
        INSERT OR REPLACE INTO daily_checklist 
        (user_id, checklist_date, items, completed_at)
        VALUES (?, ?, ?, ?)
    ''', (user_id, today, json.dumps(data['items']), completed_at))
    db.commit()
    
    return jsonify({'message': 'Checklist updated', 'completed': all_done})
