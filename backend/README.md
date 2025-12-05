# 📈 Elder Trading System

A web application implementing **Dr. Alexander Elder's Triple Screen Trading System** for NASDAQ/S&P 500 and NSE markets.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-green)
![Azure](https://img.shields.io/badge/Azure-Web%20App-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

| Feature | Description |
|---------|-------------|
| **📋 Daily Checklist** | 7-step evening analysis workflow with progress tracking |
| **🔍 Weekly Screener** | Screen 1 - EMA slope + MACD-Histogram trend analysis |
| **📊 Daily Screener** | Screen 2 - Force Index, Stochastic, price vs EMA |
| **📋 Trade APGAR** | Configurable scoring system to validate trades before entry |
| **📐 Position Sizing** | Automatic calculation based on risk parameters |
| **📖 Trade Journal** | Complete P&L tracking with statistics |
| **⚙️ Multi-Account** | Support for US (IBKR) and Indian (Zerodha) markets |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Azure Web App (F1 Free)               │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   Flask     │    │   SQLite    │    │   Yahoo     │  │
│  │   Backend   │◄──►│   Database  │    │   Finance   │  │
│  │   (Python)  │    │   (Azure    │    │   API       │  │
│  │             │    │    Files)   │    │             │  │
│  └──────┬──────┘    └─────────────┘    └──────┬──────┘  │
│         │                                      │         │
│         ▼                                      │         │
│  ┌─────────────────────────────────────────────▼──────┐  │
│  │              React Frontend (Single HTML)          │  │
│  │              Tailwind CSS + Vanilla JS             │  │
│  └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Local Development

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/elder-trading-system.git
cd elder-trading-system/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py

# Open http://localhost:8000
```

### Deploy to Azure

See [SETUP.md](SETUP.md) for detailed deployment instructions.

**Quick deploy:**
```bash
az webapp up --name elder-trading-app --resource-group elder-trading-rg
```

## 📊 Elder Triple Screen Methodology

The system implements Dr. Alexander Elder's trading approach:

### Screen 1 (Weekly - Trend)
- **22-Week EMA Slope**: Determines primary trend direction
- **MACD Histogram**: Confirms trend momentum

### Screen 2 (Daily - Entry)
- **Force Index (2-EMA)**: Identifies pullbacks in uptrend
- **Stochastic (14)**: Spots oversold conditions
- **Price vs 22-Day EMA**: Buy value, not momentum

### Screen 3 (Entry Execution)
- **Position Sizing**: Based on 2% risk rule
- **Stop Loss**: Below recent swing low
- **Target**: Minimum 1:2 Risk:Reward

## 🎯 Trade APGAR Scoring

| Score | Category | Criteria |
|-------|----------|----------|
| 0-2 | Weekly EMA | Flat/Falling → Strongly Rising |
| 0-2 | Weekly MACD-H | Falling → Rising with Divergence |
| 0-2 | Force Index | Above Zero → Below Zero + Uptick |
| 0-2 | Stochastic | Above 50 → Below 30 |
| 0-2 | Price vs EMA | Far Above → At/Below EMA |

**Total Score Interpretation:**
- **8-10**: 🎯 Excellent A-Trade
- **6-7**: ✅ Good B-Trade  
- **4-5**: ⚠️ Fair - Consider waiting
- **0-3**: ❌ Poor - Do NOT trade

## 💰 Risk Management

| Parameter | Default | Description |
|-----------|---------|-------------|
| Risk per Trade | 2% | Maximum loss per position |
| Monthly Drawdown | 6% | Stop trading if reached |
| Target R:R | 1:2 | Minimum reward:risk ratio |
| Max Positions | 5 | Maximum concurrent trades |

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/screener/weekly` | Run weekly scan |
| POST | `/api/screener/daily` | Run daily scan |
| GET | `/api/stock/<symbol>` | Get stock analysis |
| GET | `/api/strategies` | Get APGAR strategies |
| GET/POST | `/api/journal` | Trade journal CRUD |
| GET/POST | `/api/settings` | Account settings |
| GET/POST | `/api/checklist` | Daily checklist |

## 📁 Project Structure

```
elder-trading-system/
├── .github/workflows/
│   └── azure-deploy.yml    # CI/CD pipeline
├── backend/
│   ├── app.py              # Flask application + all APIs
│   ├── requirements.txt    # Python dependencies
│   ├── startup.sh          # Azure startup script
│   └── templates/
│       └── index.html      # Frontend (React + Tailwind)
├── SETUP.md                # Deployment guide
└── README.md               # This file
```

## 🔧 Configuration

Environment variables (set in Azure App Settings):

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_PATH` | SQLite database location | `/home/data/elder_trading.db` |
| `SECRET_KEY` | Flask secret key | Auto-generated |

## 📈 Markets Supported

- **US Markets**: NASDAQ 100, S&P 500 (via Yahoo Finance)
- **Indian Markets**: NIFTY 50, NIFTY Next 50 (via Yahoo Finance)

## 🛣️ Roadmap

- [ ] IBKR Web API integration (order placement)
- [ ] Kite Connect API integration (NSE trading)
- [ ] Email/SMS alerts for signals
- [ ] Backtesting module
- [ ] Mobile responsive improvements

## 📚 References

- [Come Into My Trading Room](https://www.amazon.com/Come-Into-My-Trading-Room/dp/0471225347) by Dr. Alexander Elder
- [Trading for a Living](https://www.amazon.com/Trading-Living-Psychology-Tactics-Management/dp/0471592242) by Dr. Alexander Elder

## 📄 License

MIT License - feel free to use for personal trading.

---

**Disclaimer**: This software is for educational purposes only. Trading involves risk. Past performance is not indicative of future results. Always do your own research before making investment decisions.
