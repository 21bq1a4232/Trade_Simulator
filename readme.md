# Trade Simulator

## Project Overview

The Trade Simulator is a high-performance application for estimating transaction costs and market impact in cryptocurrency trading. It connects to WebSocket endpoints for real-time orderbook data and provides comprehensive cost analysis.

## Features

- **Real-time L2 Orderbook Processing**: Connects to exchange WebSocket endpoints to process full L2 orderbook data.
- **Advanced Cost Models**: Implements sophisticated models for slippage, fees, and market impact.
- **Interactive UI**: Provides a user-friendly interface for parameter input and result visualization.
- **High Performance**: Optimized for low-latency processing and efficient resource utilization.
- **Comprehensive Analysis**: Provides detailed breakdown of all cost components.

## Technical Stack

- **Backend**: Python with Flask and SocketIO
- **Frontend**: HTML, CSS, JavaScript with Chart.js
- **WebSocket Client**: websocket-client library
- **Models**: scikit-learn for regression models
- **Data Processing**: NumPy and Pandas

## Project Structure

```
trade_simulator/
├── app.py                 # Main Flask application
├── config.py              # Configuration settings
├── requirements.txt       # Project dependencies
├── static/                # Static files (CSS, JS)
│   ├── css/
│   │   └── styles.css
│   └── js/
│       └── main.js        # Client-side WebSocket handling and UI updates
├── templates/             # HTML templates
│   └── index.html         # Main UI page
├── models/                # Model implementations
│   ├── __init__.py
│   ├── almgren_chriss.py  # Almgren-Chriss market impact model
│   ├── fees.py            # Fee calculation model
│   ├── maker_taker.py     # Maker/Taker proportion prediction
│   └── slippage.py        # Slippage estimation model
├── services/              # Service layer
│   ├── __init__.py
│   ├── orderbook.py       # Orderbook processing logic
│   ├── simulator.py       # Trade simulation logic
│   └── websocket.py       # WebSocket client implementation
├── utils/                 # Utility functions
│   ├── __init__.py
│   ├── benchmarking.py    # Performance measurement utilities
│   └── logging_config.py  # Logging configuration
└── tests/                 # Unit tests
    ├── __init__.py
    ├── test_models.py
    └── test_services.py
```

## Getting Started

### Prerequisites

- Python 3.8 or higher
- VPN access to OKX (for certain regions)

### Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the application:
   ```
   python app.py
   ```
4. Open in browser:
   ```
   http://localhost:5000
   ```

## Usage

1. **Configure Parameters**:
   - Select exchange (OKX)
   - Choose spot asset (e.g., BTC-USDT)
   - Set order type (market)
   - Enter quantity (~100 USD equivalent)
   - Adjust volatility
   - Select fee tier

2. **View Results**:
   - Expected slippage
   - Expected fees
   - Expected market impact
   - Net cost
   - Maker/taker proportion
   - Internal latency

## Documentation

- [Full Documentation](DOCUMENTATION.md)
- [Performance Analysis](PERFORMANCE_ANALYSIS.md)

## Testing

Run the test suite:
```
python -m unittest discover
```

## Contact

For questions or support, please email:
- pranavkrishna317@gmail.com