"""
Configuration settings for the trade simulator application.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# WebSocket endpoints
WEBSOCKET_URL = "wss://ws.gomarket-cpp.goquant.io/ws/l2-orderbook/okx/BTC-USDT-SWAP"

# Exchange settings
EXCHANGES = ["OKX"]
DEFAULT_EXCHANGE = "OKX"

# Available spot assets on OKX
SPOT_ASSETS = [
    "BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT", "BNB-USDT",
    "ADA-USDT", "DOGE-USDT", "DOT-USDT", "MATIC-USDT", "LTC-USDT"
]
DEFAULT_SPOT_ASSET = "BTC-USDT"

# Order types
ORDER_TYPES = ["market"]
DEFAULT_ORDER_TYPE = "market"

# Default order quantity (in USD)
DEFAULT_QUANTITY = 100.0

# Default volatility
DEFAULT_VOLATILITY = 0.02  # 2%

# Fee tiers for OKX (based on their documentation)
OKX_FEE_TIERS = {
    "VIP0": {"maker": 0.0008, "taker": 0.001},
    "VIP1": {"maker": 0.0007, "taker": 0.0009},
    "VIP2": {"maker": 0.0006, "taker": 0.0008},
    "VIP3": {"maker": 0.0005, "taker": 0.0007},
    "VIP4": {"maker": 0.0003, "taker": 0.0005},
    "VIP5": {"maker": 0.0000, "taker": 0.0003},
}
DEFAULT_FEE_TIER = "VIP0"

# Almgren-Chriss model parameters
AC_MODEL_PARAMS = {
    "market_impact_factor": 0.1,
    "volatility_factor": 0.5,
    "risk_aversion": 1.0
}

# Performance settings
PROCESSING_BATCH_SIZE = 100  # Number of ticks to process in a batch
MAX_ORDERBOOK_DEPTH = 50  # Maximum depth of orderbook to maintain
BENCHMARK_INTERVAL = 100  # Number of ticks between benchmark measurements

# Logging settings
LOG_LEVEL = "INFO"
LOG_FILE = "trade_simulator.log"

# Flask app settings
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 5000))
SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_key")