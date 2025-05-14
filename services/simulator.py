"""
Trade simulator service that integrates all models and provides simulation results.
"""
import time
import threading
from datetime import datetime
import numpy as np
from loguru import logger

from models.slippage import SlippageModel
from models.fees import FeeModel
from models.almgren_chriss import AlmgrenChrissModel
from models.maker_taker import MakerTakerModel
from services.orderbook import Orderbook
from utils.benchmarking import Benchmarker

class TradeSimulator:
    """
    Core trade simulator service that integrates all components:
    - Orderbook processing
    - Slippage estimation
    - Fee calculation
    - Market impact modeling
    - Maker/Taker proportion prediction
    """
    
    def __init__(self, config):
        """
        Initialize the trade simulator.
        
        Args:
            config (module): Configuration module
        """
        self.config = config
        
        # Initialize models
        self.slippage_model = SlippageModel()
        self.fee_model = FeeModel()
        self.market_impact_model = AlmgrenChrissModel(
            market_impact_factor=config.AC_MODEL_PARAMS["market_impact_factor"],
            volatility_factor=config.AC_MODEL_PARAMS["volatility_factor"],
            risk_aversion=config.AC_MODEL_PARAMS["risk_aversion"]
        )
        self.maker_taker_model = MakerTakerModel()
        
        # Initialize orderbook
        self.orderbook = Orderbook(max_depth=config.MAX_ORDERBOOK_DEPTH)
        
        # Simulation parameters (default values)
        self.exchange = config.DEFAULT_EXCHANGE
        self.spot_asset = config.DEFAULT_SPOT_ASSET
        self.order_type = config.DEFAULT_ORDER_TYPE
        self.quantity = config.DEFAULT_QUANTITY
        self.volatility = config.DEFAULT_VOLATILITY
        self.fee_tier = config.DEFAULT_FEE_TIER
        
        # Simulation results
        self.simulation_results = {
            "timestamp": None,
            "exchange": self.exchange,
            "spot_asset": self.spot_asset,
            "order_type": self.order_type,
            "quantity": self.quantity,
            "volatility": self.volatility,
            "fee_tier": self.fee_tier,
            "slippage": {
                "expected_bps": 0.0,
                "conservative_bps": 0.0
            },
            "fees": {
                "maker_fee": 0.0,
                "taker_fee": 0.0,
                "total_fee": 0.0,
                "effective_rate_bps": 0.0
            },
            "market_impact": {
                "temporary_bps": 0.0,
                "permanent_bps": 0.0,
                "total_bps": 0.0
            },
            "net_cost": {
                "expected_bps": 0.0,
                "conservative_bps": 0.0
            },
            "maker_taker": {
                "maker_percentage": 0.0,
                "taker_percentage": 1.0
            },
            "performance": {
                "internal_latency_ms": 0.0
            },
            "orderbook": {
                "best_bid": 0.0,
                "best_ask": 0.0,
                "mid_price": 0.0,
                "spread_bps": 0.0
            }
        }
        
        # Performance benchmarking
        self.benchmarker = Benchmarker()
        
        # Status and locking
        self.is_running = False
        self.lock = threading.Lock()
        self.last_update_time = None
        self.update_count = 0
    
    def start(self):
        """Start the simulator."""
        logger.info("Starting trade simulator")
        self.is_running = True
        
        # Initialize benchmarking
        self.benchmarker.start()
    
    def stop(self):
        """Stop the simulator."""
        logger.info("Stopping trade simulator")
        self.is_running = False
        
        # Finalize benchmarking
        self.benchmarker.stop()
    
    def set_parameter(self, param_name, param_value):
        """
        Set a simulation parameter.
        
        Args:
            param_name (str): Parameter name
            param_value: Parameter value
        
        Returns:
            bool: True if parameter was set, False otherwise
        """
        try:
            with self.lock:
                if param_name == "exchange":
                    self.exchange = param_value
                elif param_name == "spot_asset":
                    self.spot_asset = param_value
                elif param_name == "order_type":
                    self.order_type = param_value
                elif param_name == "quantity":
                    self.quantity = float(param_value)
                elif param_name == "volatility":
                    self.volatility = float(param_value)
                elif param_name == "fee_tier":
                    self.fee_tier = param_value
                else:
                    logger.warning(f"Unknown parameter: {param_name}")
                    return False
                
                # Update simulation results
                self.simulation_results[param_name] = param_value
                
                # Run simulation with new parameters
                self.run_simulation()
                
                return True
                
        except Exception as e:
            logger.exception(f"Error setting parameter {param_name}: {str(e)}")
            return False
    
    # In services/simulator.py

    def set_parameter(self, param_name, param_value):
        """
        Set a simulation parameter.
        
        Args:
            param_name (str): Parameter name
            param_value: Parameter value
        
        Returns:
            bool: True if parameter was set, False otherwise
        """
        try:
            print(f"⭐ Setting parameter {param_name} to {param_value}")
            
            # Don't use a lock for the entire operation - it blocks the UI
            if param_name == "exchange":
                self.exchange = param_value
            elif param_name == "spot_asset":
                self.spot_asset = param_value
            elif param_name == "order_type":
                self.order_type = param_value
            elif param_name == "quantity":
                self.quantity = float(param_value)
            elif param_name == "volatility":
                self.volatility = float(param_value)
            elif param_name == "fee_tier":
                self.fee_tier = param_value
            else:
                logger.warning(f"Unknown parameter: {param_name}")
                return False
            
            # Update simulation results
            self.simulation_results[param_name] = param_value
            
            # Run simulation in a non-blocking way
            # Either use a very quick timeout or run in a separate thread
            threading.Thread(target=self._run_simulation_safe).start()
            
            print(f"⭐ Successfully set parameter {param_name} to {param_value}")
            return True
                
        except Exception as e:
            print(f"⭐ ERROR setting parameter {param_name}: {str(e)}")
            logger.exception(f"Error setting parameter {param_name}: {str(e)}")
            return False

    def _run_simulation_safe(self):
        """Run simulation with proper error handling."""
        try:
            self.run_simulation()
        except Exception as e:
            print(f"⭐ ERROR in simulation: {str(e)}")
            logger.exception(f"Error in simulation: {str(e)}")
    def process_orderbook_data(self, data):
        """
        Process new orderbook data from WebSocket.
        
        Args:
            data (dict): Orderbook data from WebSocket
        
        Returns:
            bool: True if processing was successful, False otherwise
        """
        try:
            # Start benchmarking
            with self.benchmarker.measure("orderbook_update"):
                # Update the orderbook
                update_success = self.orderbook.update(data)
                
                if not update_success:
                    logger.warning("Failed to update orderbook")
                    return False
                
                # Update counters
                self.update_count += 1
                self.last_update_time = time.time()
                
                # Run simulation after every N updates
                if self.update_count % self.config.PROCESSING_BATCH_SIZE == 0:
                    self.run_simulation()
                
                # Log benchmark results periodically
                if self.update_count % self.config.BENCHMARK_INTERVAL == 0:
                    benchmark_results = self.benchmarker.get_results()
                    logger.info(f"Benchmark results: {benchmark_results}")
                
                return True
                
        except Exception as e:
            logger.exception(f"Error processing orderbook data: {str(e)}")
            return False
    
    def run_simulation(self):
        """
        Run a complete simulation with current parameters and orderbook state.
        Updates the simulation_results dictionary with new results.
        """
        try:
            with self.lock:
                # Start benchmarking
                with self.benchmarker.measure("full_simulation"):
                    # Get current timestamp
                    current_time = datetime.now().isoformat()
                    
                    # Get orderbook metrics
                    orderbook_metrics = self.orderbook.get_metrics()
                    mid_price = orderbook_metrics.get("mid_price")
                    
                    # Skip simulation if orderbook is empty
                    if mid_price is None:
                        logger.warning("Cannot run simulation: orderbook is empty")
                        return
                    
                    # Get daily volume estimate (placeholder)
                    # In a real system, this would be fetched from market data
                    daily_volume = mid_price * 1000  # Simplified approximation
                    
                    # 1. Estimate slippage
                    with self.benchmarker.measure("slippage_estimation"):
                        slippage_results = self.slippage_model.estimate_slippage_from_orderbook(
                            self.orderbook, self.quantity, mid_price, self.volatility, "buy"
                        )
                        
                        expected_slippage_bps = slippage_results["expected_slippage_bps"]
                        conservative_slippage_bps = slippage_results["conservative_slippage_bps"]
                    
                    # 2. Predict maker/taker proportion
                    with self.benchmarker.measure("maker_taker_prediction"):
                        maker_taker_results = self.maker_taker_model.predict_maker_taker_from_orderbook(
                            self.orderbook, self.quantity, mid_price, self.volatility, "buy"
                        )
                        
                        maker_percentage = maker_taker_results["maker_percentage"]
                        taker_percentage = maker_taker_results["taker_percentage"]
                    
                    # 3. Calculate fees
                    with self.benchmarker.measure("fee_calculation"):
                        fee_results = self.fee_model.calculate_fees(
                            self.exchange, self.order_type, self.quantity, mid_price,
                            self.fee_tier, maker_percentage
                        )
                        
                        maker_fee = fee_results["maker_fee"]
                        taker_fee = fee_results["taker_fee"]
                        total_fee = fee_results["total_fee"]
                        effective_fee_rate = fee_results["effective_fee_rate"]
                    
                    # 4. Calculate market impact
                    with self.benchmarker.measure("market_impact_calculation"):
                        impact_results = self.market_impact_model.estimate_market_impact_from_orderbook(
                            self.orderbook, self.quantity, mid_price, daily_volume, self.volatility, True
                        )
                        
                        temporary_impact = impact_results["temporary_impact"]
                        permanent_impact = impact_results["permanent_impact"]
                        total_impact = impact_results["total_impact"]
                        total_impact_bps = impact_results["total_impact_bps"]
                    
                    # 5. Calculate net cost
                    with self.benchmarker.measure("net_cost_calculation"):
                        # Expected net cost (in basis points)
                        expected_net_cost_bps = (
                            expected_slippage_bps +
                            effective_fee_rate * 10000 +  # Convert to basis points
                            total_impact_bps
                        )
                        
                        # Conservative net cost (in basis points)
                        conservative_net_cost_bps = (
                            conservative_slippage_bps +
                            effective_fee_rate * 10000 +  # Convert to basis points
                            total_impact_bps * 1.2  # Add safety margin to impact
                        )
                    
                    # 6. Update simulation results
                    with self.benchmarker.measure("results_update"):
                        self.simulation_results.update({
                            "timestamp": current_time,
                            "slippage": {
                                "expected_bps": float(expected_slippage_bps),
                                "conservative_bps": float(conservative_slippage_bps)
                            },
                            "fees": {
                                "maker_fee": float(maker_fee),
                                "taker_fee": float(taker_fee),
                                "total_fee": float(total_fee),
                                "effective_rate_bps": float(effective_fee_rate * 10000)  # Convert to basis points
                            },
                            "market_impact": {
                                "temporary_bps": float(temporary_impact / mid_price * 10000),
                                "permanent_bps": float(permanent_impact / mid_price * 10000),
                                "total_bps": float(total_impact_bps)
                            },
                            "net_cost": {
                                "expected_bps": float(expected_net_cost_bps),
                                "conservative_bps": float(conservative_net_cost_bps)
                            },
                            "maker_taker": {
                                "maker_percentage": float(maker_percentage),
                                "taker_percentage": float(taker_percentage)
                            },
                            "orderbook": {
                                "best_bid": float(orderbook_metrics.get("best_bid", 0.0)),
                                "best_ask": float(orderbook_metrics.get("best_ask", 0.0)),
                                "mid_price": float(mid_price),
                                "spread_bps": float(orderbook_metrics.get("spread_bps", 0.0))
                            }
                        })
                    
                    # 7. Update performance metrics
                    benchmark_results = self.benchmarker.get_results()
                    internal_latency = benchmark_results.get("full_simulation", {}).get("last_ms", 0.0)
                    
                    self.simulation_results["performance"] = {
                        "internal_latency_ms": float(internal_latency)
                    }
                    
                    logger.debug(f"Simulation complete. Net cost (expected): {expected_net_cost_bps:.2f} bps")
                    
        except Exception as e:
            logger.exception(f"Error running simulation: {str(e)}")
    
    def get_simulation_results(self):
        """
        Get the current simulation results.
        
        Returns:
            dict: Current simulation results
        """
        with self.lock:
            return self.simulation_results.copy()
    
    def get_performance_metrics(self):
        """
        Get performance metrics for the simulator.
        
        Returns:
            dict: Performance metrics
        """
        benchmark_results = self.benchmarker.get_results()
        
        orderbook_metrics = self.orderbook.get_performance_metrics()
        
        return {
            "benchmark": benchmark_results,
            "orderbook": orderbook_metrics,
            "update_count": self.update_count,
            "last_update": self.last_update_time
        }