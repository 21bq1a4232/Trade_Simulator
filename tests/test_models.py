"""
Unit tests for the models module.
"""
import unittest
from models.slippage import SlippageModel
from models.fees import FeeModel
from models.almgren_chriss import AlmgrenChrissModel
from models.maker_taker import MakerTakerModel
from services.orderbook import Orderbook

class TestSlippageModel(unittest.TestCase):
    """Tests for the SlippageModel class."""
    
    def setUp(self):
        """Set up test environment."""
        self.model = SlippageModel()
    
    def test_predict_slippage_heuristic(self):
        """Test slippage prediction with heuristic model (untrained)."""
        features = {
            "quantity_usd": 100.0,
            "relative_size": 0.1,
            "spread_bps": 10.0,
            "volatility": 0.02,
            "imbalance": 1.0,
            "is_buy": True
        }
        
        # Predict slippage
        slippage = self.model.predict_slippage(features, "expected")
        
        # Check that slippage is reasonable
        self.assertGreater(slippage, 0.0)
        self.assertLess(slippage, 100.0)  # Slippage should be less than 100 bps for small orders
    
    def test_add_observation(self):
        """Test adding observations to the model."""
        features = {
            "quantity_usd": 100.0,
            "relative_size": 0.1,
            "spread_bps": 10.0,
            "volatility": 0.02,
            "imbalance": 1.0
        }
        
        actual_slippage = 5.0  # 5 bps
        
        # Add observation
        self.model.add_observation(features, actual_slippage)
        
        # Check that observation was added to history
        self.assertEqual(len(self.model.slippage_history), 1)

class TestFeeModel(unittest.TestCase):
    """Tests for the FeeModel class."""
    
    def setUp(self):
        """Set up test environment."""
        self.model = FeeModel()
    
    def test_get_fee_rates(self):
        """Test getting fee rates for different exchanges and tiers."""
        # Test OKX fee rates
        okx_vip0 = self.model.get_fee_rates("OKX", "VIP0")
        self.assertEqual(okx_vip0["maker"], 0.0008)
        self.assertEqual(okx_vip0["taker"], 0.001)
        
        # Test unknown exchange (should default to OKX)
        unknown_exchange = self.model.get_fee_rates("UnknownExchange", "VIP0")
        self.assertEqual(unknown_exchange["maker"], 0.0008)
        self.assertEqual(unknown_exchange["taker"], 0.001)
        
        # Test unknown tier (should default to VIP0)
        unknown_tier = self.model.get_fee_rates("OKX", "UnknownTier")
        self.assertEqual(unknown_tier["maker"], 0.0008)
        self.assertEqual(unknown_tier["taker"], 0.001)
    
    def test_calculate_fees(self):
        """Test fee calculation."""
        # Test market order (100% taker)
        market_fees = self.model.calculate_fees("OKX", "market", 100.0, 50000.0, "VIP0")
        self.assertEqual(market_fees["maker_fee"], 0.0)
        self.assertEqual(market_fees["taker_fee"], 50.0)  # 0.1% of 50000
        self.assertEqual(market_fees["total_fee"], 50.0)
        
        # Test with custom maker percentage
        mixed_fees = self.model.calculate_fees("OKX", "market", 100.0, 50000.0, "VIP0", 0.3)
        self.assertEqual(mixed_fees["maker_fee"], 0.3 * 0.0008 * 100.0 * 50000.0 / 100.0)
        self.assertEqual(mixed_fees["taker_fee"], 0.7 * 0.001 * 100.0 * 50000.0 / 100.0)
        self.assertEqual(mixed_fees["total_fee"], mixed_fees["maker_fee"] + mixed_fees["taker_fee"])

class TestAlmgrenChrissModel(unittest.TestCase):
    """Tests for the AlmgrenChrissModel class."""
    
    def setUp(self):
        """Set up test environment."""
        self.model = AlmgrenChrissModel()
    
    def test_estimate_market_impact(self):
        """Test market impact estimation."""
        # Test buy order
        buy_impact = self.model.estimate_market_impact(10.0, 50000.0, 1000.0, 0.02, True)
        
        # Impact should be positive for buy orders
        self.assertGreater(buy_impact["temporary_impact"], 0)
        self.assertGreater(buy_impact["permanent_impact"], 0)
        self.assertGreater(buy_impact["total_impact"], 0)
        
        # Test sell order
        sell_impact = self.model.estimate_market_impact(10.0, 50000.0, 1000.0, 0.02, False)
        
        # Impact should be negative for sell orders
        self.assertLess(sell_impact["temporary_impact"], 0)
        self.assertLess(sell_impact["permanent_impact"], 0)
        self.assertLess(sell_impact["total_impact"], 0)
        
        # Absolute impact should be the same for buy and sell
        self.assertAlmostEqual(abs(buy_impact["temporary_impact"]), abs(sell_impact["temporary_impact"]))
        self.assertAlmostEqual(abs(buy_impact["permanent_impact"]), abs(sell_impact["permanent_impact"]))
        self.assertAlmostEqual(abs(buy_impact["total_impact"]), abs(sell_impact["total_impact"]))

class TestMakerTakerModel(unittest.TestCase):
    """Tests for the MakerTakerModel class."""
    
    def setUp(self):
        """Set up test environment."""
        self.model = MakerTakerModel()
    
    def test_predict_maker_percentage(self):
        """Test maker percentage prediction with heuristic model (untrained)."""
        features = {
            "quantity_usd": 100.0,
            "relative_size": 0.1,
            "spread_bps": 10.0,
            "volatility": 0.02,
            "imbalance": 1.0,
            "best_bid_qty": 10.0,
            "best_ask_qty": 5.0,
            "is_buy": True
        }
        
        # Predict maker percentage
        maker_pct = self.model.predict_maker_percentage(features)
        
        # Check that maker percentage is in valid range
        self.assertGreaterEqual(maker_pct, 0.0)
        self.assertLessEqual(maker_pct, 1.0)

class TestOrderbook(unittest.TestCase):
    """Tests for the Orderbook class."""
    
    def setUp(self):
        """Set up test environment."""
        self.orderbook = Orderbook()
    
    def test_update_orderbook(self):
        """Test updating the orderbook."""
        # Create test data
        data = {
            "timestamp": "2023-01-01T00:00:00Z",
            "exchange": "OKX",
            "symbol": "BTC-USDT",
            "asks": [
                ["50000.0", "1.0"],
                ["50010.0", "2.0"],
                ["50020.0", "3.0"]
            ],
            "bids": [
                ["49990.0", "1.5"],
                ["49980.0", "2.5"],
                ["49970.0", "3.5"]
            ]
        }
        
        # Update orderbook
        result = self.orderbook.update(data)
        
        # Check that update was successful
        self.assertTrue(result)
        
        # Check orderbook state
        self.assertEqual(self.orderbook.timestamp, "2023-01-01T00:00:00Z")
        self.assertEqual(self.orderbook.exchange, "OKX")
        self.assertEqual(self.orderbook.symbol, "BTC-USDT")
        
        # Check asks
        self.assertEqual(len(self.orderbook.asks), 3)
        self.assertEqual(self.orderbook.asks[50000.0], 1.0)
        self.assertEqual(self.orderbook.asks[50010.0], 2.0)
        self.assertEqual(self.orderbook.asks[50020.0], 3.0)
        
        # Check bids
        self.assertEqual(len(self.orderbook.bids), 3)
        self.assertEqual(self.orderbook.bids[49990.0], 1.5)
        self.assertEqual(self.orderbook.bids[49980.0], 2.5)
        self.assertEqual(self.orderbook.bids[49970.0], 3.5)
    
    def test_get_best_ask_bid(self):
        """Test getting best ask and bid."""
        # Create test data
        data = {
            "timestamp": "2023-01-01T00:00:00Z",
            "exchange": "OKX",
            "symbol": "BTC-USDT",
            "asks": [
                ["50000.0", "1.0"],
                ["50010.0", "2.0"],
                ["50020.0", "3.0"]
            ],
            "bids": [
                ["49990.0", "1.5"],
                ["49980.0", "2.5"],
                ["49970.0", "3.5"]
            ]
        }
        
        # Update orderbook
        self.orderbook.update(data)
        
        # Check best ask and bid
        best_ask, best_ask_qty = self.orderbook.get_best_ask()
        best_bid, best_bid_qty = self.orderbook.get_best_bid()
        
        self.assertEqual(best_ask, 50000.0)
        self.assertEqual(best_ask_qty, 1.0)
        self.assertEqual(best_bid, 49990.0)
        self.assertEqual(best_bid_qty, 1.5)
    
    def test_get_mid_price_and_spread(self):
        """Test getting mid price and spread."""
        # Create test data
        data = {
            "timestamp": "2023-01-01T00:00:00Z",
            "exchange": "OKX",
            "symbol": "BTC-USDT",
            "asks": [
                ["50000.0", "1.0"],
                ["50010.0", "2.0"],
                ["50020.0", "3.0"]
            ],
            "bids": [
                ["49990.0", "1.5"],
                ["49980.0", "2.5"],
                ["49970.0", "3.5"]
            ]
        }
        
        # Update orderbook
        self.orderbook.update(data)
        
        # Check mid price and spread
        mid_price = self.orderbook.get_mid_price()
        spread = self.orderbook.get_spread()
        
        self.assertEqual(mid_price, (50000.0 + 49990.0) / 2)
        self.assertEqual(spread, 50000.0 - 49990.0)
    
    def test_get_volume_weighted_price(self):
        """Test VWAP calculation."""
        # Create test data
        data = {
            "timestamp": "2023-01-01T00:00:00Z",
            "exchange": "OKX",
            "symbol": "BTC-USDT",
            "asks": [
                ["50000.0", "1.0"],
                ["50010.0", "2.0"],
                ["50020.0", "3.0"]
            ],
            "bids": [
                ["49990.0", "1.5"],
                ["49980.0", "2.5"],
                ["49970.0", "3.5"]
            ]
        }
        
        # Update orderbook
        self.orderbook.update(data)
        
        # Test buy VWAP (taking from asks)
        buy_vwap, buy_filled, buy_remaining = self.orderbook.get_volume_weighted_price(2.0, "buy")
        
        # Should fill 1.0 at 50000.0 and 1.0 at 50010.0
        expected_buy_vwap = (1.0 * 50000.0 + 1.0 * 50010.0) / 2.0
        
        self.assertEqual(buy_filled, 2.0)
        self.assertEqual(buy_remaining, 0.0)
        self.assertEqual(buy_vwap, expected_buy_vwap)
        
        # Test sell VWAP (taking from bids)
        sell_vwap, sell_filled, sell_remaining = self.orderbook.get_volume_weighted_price(2.0, "sell")
        
        # Should fill 1.5 at 49990.0 and 0.5 at 49980.0
        expected_sell_vwap = (1.5 * 49990.0 + 0.5 * 49980.0) / 2.0
        
        self.assertEqual(sell_filled, 2.0)
        self.assertEqual(sell_remaining, 0.0)
        self.assertAlmostEqual(sell_vwap, expected_sell_vwap)

if __name__ == '__main__':
    unittest.main()