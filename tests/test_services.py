"""
Unit tests for the services module.
"""
import unittest
from unittest.mock import MagicMock, patch
import config
from services.simulator import TradeSimulator
from services.websocket import OrderbookWebsocketClient

class TestTradeSimulator(unittest.TestCase):
    """Tests for the TradeSimulator class."""
    
    def setUp(self):
        """Set up test environment."""
        self.simulator = TradeSimulator(config)
    
    def test_set_parameter(self):
        """Test setting simulation parameters."""
        # Test setting exchange
        self.assertTrue(self.simulator.set_parameter("exchange", "OKX"))
        self.assertEqual(self.simulator.exchange, "OKX")
        
        # Test setting spot_asset
        self.assertTrue(self.simulator.set_parameter("spot_asset", "BTC-USDT"))
        self.assertEqual(self.simulator.spot_asset, "BTC-USDT")
        
        # Test setting order_type
        self.assertTrue(self.simulator.set_parameter("order_type", "market"))
        self.assertEqual(self.simulator.order_type, "market")
        
        # Test setting quantity
        self.assertTrue(self.simulator.set_parameter("quantity", 200.0))
        self.assertEqual(self.simulator.quantity, 200.0)
        
        # Test setting volatility
        self.assertTrue(self.simulator.set_parameter("volatility", 0.03))
        self.assertEqual(self.simulator.volatility, 0.03)
        
        # Test setting fee_tier
        self.assertTrue(self.simulator.set_parameter("fee_tier", "VIP1"))
        self.assertEqual(self.simulator.fee_tier, "VIP1")
        
        # Test setting invalid parameter
        self.assertFalse(self.simulator.set_parameter("invalid_param", "value"))
    
    def test_get_parameters(self):
        """Test getting simulation parameters."""
        params = self.simulator.get_parameters()
        
        # Check default parameters
        self.assertEqual(params["exchange"], config.DEFAULT_EXCHANGE)
        self.assertEqual(params["spot_asset"], config.DEFAULT_SPOT_ASSET)
        self.assertEqual(params["order_type"], config.DEFAULT_ORDER_TYPE)
        self.assertEqual(params["quantity"], config.DEFAULT_QUANTITY)
        self.assertEqual(params["volatility"], config.DEFAULT_VOLATILITY)
        self.assertEqual(params["fee_tier"], config.DEFAULT_FEE_TIER)
    
    def test_process_orderbook_data(self):
        """Test processing orderbook data."""
        # Create mock orderbook data
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
        
        # Process data
        result = self.simulator.process_orderbook_data(data)
        
        # Check that processing was successful
        self.assertTrue(result)
        
        # Check that orderbook was updated
        self.assertEqual(self.simulator.orderbook.timestamp, "2023-01-01T00:00:00Z")
        self.assertEqual(self.simulator.orderbook.exchange, "OKX")
        self.assertEqual(self.simulator.orderbook.symbol, "BTC-USDT")
    
    def test_run_simulation(self):
        """Test running a simulation."""
        # Create mock orderbook data
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
        
        # Update orderbook first
        self.simulator.orderbook.update(data)
        
        # Run simulation
        self.simulator.run_simulation()
        
        # Get results
        results = self.simulator.get_simulation_results()
        
        # Check that results were populated
        self.assertIsNotNone(results["timestamp"])
        self.assertIsNotNone(results["slippage"]["expected_bps"])
        self.assertIsNotNone(results["fees"]["total_fee"])
        self.assertIsNotNone(results["market_impact"]["total_bps"])
        self.assertIsNotNone(results["net_cost"]["expected_bps"])
        self.assertIsNotNone(results["maker_taker"]["maker_percentage"])
        self.assertIsNotNone(results["performance"]["internal_latency_ms"])

@patch('websocket.WebSocketApp')
class TestOrderbookWebsocketClient(unittest.TestCase):
    """Tests for the OrderbookWebsocketClient class."""
    
    def setUp(self):
        """Set up test environment."""
        self.callback = MagicMock()
        self.url = "wss://test.url/ws"
    
    def test_initialization(self, mock_ws):
        """Test client initialization."""
        client = OrderbookWebsocketClient(self.url, self.callback)
        
        self.assertEqual(client.url, self.url)
        self.assertEqual(client.on_message_callback, self.callback)
        self.assertFalse(client.is_connected)
        self.assertEqual(client.reconnect_attempts, 0)
    
    def test_connect(self, mock_ws):
        """Test connection establishment."""
        client = OrderbookWebsocketClient(self.url, self.callback)
        client.connect()
        
        # Check that WebSocketApp was created with correct parameters
        mock_ws.assert_called_once_with(
            self.url,
            on_message=client._on_message,
            on_error=client._on_error,
            on_close=client._on_close,
            on_open=client._on_open
        )
        
        # Check that run_forever was called in a thread
        mock_ws_instance = mock_ws.return_value
        self.assertTrue(mock_ws_instance.run_forever.called)
    
    def test_on_message_callback(self, mock_ws):
        """Test message handling."""
        client = OrderbookWebsocketClient(self.url, self.callback)
        
        # Create a valid JSON message
        message = '{"exchange": "OKX", "symbol": "BTC-USDT", "asks": [], "bids": []}'
        
        # Call _on_message directly
        client._on_message(None, message)
        
        # Check that callback was called with parsed message
        self.callback.assert_called_once()
        callback_arg = self.callback.call_args[0][0]
        self.assertEqual(callback_arg["exchange"], "OKX")
        self.assertEqual(callback_arg["symbol"], "BTC-USDT")
    
    def test_get_performance_metrics(self, mock_ws):
        """Test getting performance metrics."""
        client = OrderbookWebsocketClient(self.url, self.callback)
        
        # Simulate some message processing
        client.message_count = 100
        client.processing_times = [0.001, 0.002, 0.003]
        client.is_connected = True
        
        # Get metrics
        metrics = client.get_performance_metrics()
        
        # Check metrics
        self.assertEqual(metrics["message_count"], 100)
        self.assertEqual(metrics["connected"], True)
        self.assertAlmostEqual(metrics["avg_processing_time_ms"], 2.0)
        self.assertAlmostEqual(metrics["min_processing_time_ms"], 1.0)
        self.assertAlmostEqual(metrics["max_processing_time_ms"], 3.0)

if __name__ == '__main__':
    unittest.main()