"""
Orderbook processing logic for the trade simulator.
"""
import time
import numpy as np
from loguru import logger
from collections import deque

class Orderbook:
    """
    Class for processing and managing L2 orderbook data.
    Implements efficient data structures for fast access and updates.
    """
    
    def __init__(self, max_depth=50):
        """
        Initialize the orderbook.
        
        Args:
            max_depth (int): Maximum depth of orderbook to maintain
        """
        self.asks = {}  # price -> quantity
        self.bids = {}  # price -> quantity
        self.timestamp = None
        self.exchange = None
        self.symbol = None
        self.max_depth = max_depth
        
        # Performance metrics
        self.update_times = deque(maxlen=1000)
        self.last_update_time = None
        
        # Cached orderbook metrics
        self._cached_metrics = {}
        self._metrics_timestamp = 0
        self._metrics_cache_ttl = 0.1  # 100ms TTL for cached metrics
    
    def update(self, data):
        """
        Update the orderbook with new data.
        
        Args:
            data (dict): Orderbook data from WebSocket
        
        Returns:
            bool: True if update was successful, False otherwise
        """
        start_time = time.time()
        
        try:
            self.timestamp = data.get("timestamp")
            self.exchange = data.get("exchange")
            self.symbol = data.get("symbol")
            
            # Update asks
            asks_data = data.get("asks", [])
            new_asks = {}
            for price_str, quantity_str in asks_data:
                price = float(price_str)
                quantity = float(quantity_str)
                if quantity > 0:  # Only include non-zero quantities
                    new_asks[price] = quantity
            
            # Update bids
            bids_data = data.get("bids", [])
            new_bids = {}
            for price_str, quantity_str in bids_data:
                price = float(price_str)
                quantity = float(quantity_str)
                if quantity > 0:  # Only include non-zero quantities
                    new_bids[price] = quantity
            
            # Replace the orderbook completely with new data
            # This is more efficient for full snapshots than incremental updates
            self.asks = new_asks
            self.bids = new_bids
            
            # Limit the orderbook depth
            self._trim_orderbook()
            
            # Clear the cached metrics
            self._cached_metrics = {}
            
            # Update performance metrics
            update_time = time.time() - start_time
            self.update_times.append(update_time)
            self.last_update_time = time.time()
            
            return True
            
        except Exception as e:
            logger.exception(f"Error updating orderbook: {str(e)}")
            return False
    
    def _trim_orderbook(self):
        """Trim the orderbook to the maximum depth."""
        if len(self.asks) > self.max_depth:
            # Keep only the lowest ask prices
            sorted_asks = sorted(self.asks.items())
            self.asks = dict(sorted_asks[:self.max_depth])
        
        if len(self.bids) > self.max_depth:
            # Keep only the highest bid prices
            sorted_bids = sorted(self.bids.items(), reverse=True)
            self.bids = dict(sorted_bids[:self.max_depth])
    
    def get_best_ask(self):
        """
        Get the best (lowest) ask price and quantity.
        
        Returns:
            tuple: (price, quantity) or (None, None) if no asks
        """
        if not self.asks:
            return None, None
        
        best_ask_price = min(self.asks.keys())
        return best_ask_price, self.asks[best_ask_price]
    
    def get_best_bid(self):
        """
        Get the best (highest) bid price and quantity.
        
        Returns:
            tuple: (price, quantity) or (None, None) if no bids
        """
        if not self.bids:
            return None, None
        
        best_bid_price = max(self.bids.keys())
        return best_bid_price, self.bids[best_bid_price]
    
    def get_mid_price(self):
        """
        Get the mid price (average of best bid and best ask).
        
        Returns:
            float: Mid price or None if orderbook is empty
        """
        best_ask_price, _ = self.get_best_ask()
        best_bid_price, _ = self.get_best_bid()
        
        if best_ask_price is None or best_bid_price is None:
            return None
        
        return (best_ask_price + best_bid_price) / 2
    
    def get_spread(self):
        """
        Get the spread (difference between best ask and best bid).
        
        Returns:
            float: Spread or None if orderbook is empty
        """
        best_ask_price, _ = self.get_best_ask()
        best_bid_price, _ = self.get_best_bid()
        
        if best_ask_price is None or best_bid_price is None:
            return None
        
        return best_ask_price - best_bid_price
    
    def get_orderbook_imbalance(self):
        """
        Calculate orderbook imbalance as a ratio of bid to ask volume.
        
        Returns:
            float: Imbalance ratio (>1 means more bids than asks)
        """
        total_ask_volume = sum(self.asks.values())
        total_bid_volume = sum(self.bids.values())
        
        if total_ask_volume == 0:
            return float('inf')  # Infinite imbalance if no asks
        
        return total_bid_volume / total_ask_volume
    
    def get_volume_weighted_price(self, quantity, side='buy'):
        """
        Calculate the volume-weighted average price for a given quantity.
        
        Args:
            quantity (float): Quantity to buy/sell
            side (str): 'buy' or 'sell'
        
        Returns:
            tuple: (vwap, filled_quantity, remaining_quantity)
        """
        if side.lower() == 'buy':
            # For buys, we take liquidity from the asks
            prices = sorted(self.asks.keys())
            quantities = [self.asks[price] for price in prices]
        else:
            # For sells, we take liquidity from the bids
            prices = sorted(self.bids.keys(), reverse=True)
            quantities = [self.bids[price] for price in prices]
        
        total_value = 0
        filled_quantity = 0
        remaining_quantity = quantity
        
        for price, available_qty in zip(prices, quantities):
            # Calculate how much we can fill at this price level
            fill_qty = min(remaining_quantity, available_qty)
            
            # Add to the total value
            total_value += fill_qty * price
            filled_quantity += fill_qty
            remaining_quantity -= fill_qty
            
            # Check if we've filled the entire order
            if remaining_quantity <= 0:
                break
        
        # Calculate VWAP if we filled anything
        if filled_quantity > 0:
            vwap = total_value / filled_quantity
        else:
            vwap = None
        
        return vwap, filled_quantity, remaining_quantity
    
    def get_market_depth(self, levels=5):
        """
        Get a summary of the orderbook market depth.
        
        Args:
            levels (int): Number of price levels to include
        
        Returns:
            dict: Market depth summary
        """
        sorted_asks = sorted(self.asks.items())[:levels]
        sorted_bids = sorted(self.bids.items(), reverse=True)[:levels]
        
        return {
            "asks": sorted_asks,
            "bids": sorted_bids,
            "timestamp": self.timestamp,
            "spread": self.get_spread(),
            "mid_price": self.get_mid_price()
        }
    
    def estimate_slippage(self, quantity, side='buy'):
        """
        Estimate slippage for a market order of given quantity.
        
        Args:
            quantity (float): Quantity to buy/sell
            side (str): 'buy' or 'sell'
        
        Returns:
            float: Estimated slippage as a percentage
        """
        mid_price = self.get_mid_price()
        if mid_price is None:
            return None
        
        vwap, filled_qty, remaining_qty = self.get_volume_weighted_price(quantity, side)
        
        if vwap is None or filled_qty == 0:
            return None
        
        if side.lower() == 'buy':
            # For buys, slippage is positive when VWAP > mid_price
            slippage = (vwap / mid_price - 1) * 100
        else:
            # For sells, slippage is positive when VWAP < mid_price
            slippage = (1 - vwap / mid_price) * 100
        
        return slippage
    
    def get_volatility_estimate(self, window=100):
        """
        Estimate volatility based on recent price movements.
        This is a simplified estimate and would be replaced with a more robust
        calculation in a production system.
        
        Args:
            window (int): Window size for volatility calculation
        
        Returns:
            float: Estimated volatility or None if not enough data
        """
        # In a real system, we would maintain a price history
        # Here we just return a placeholder value
        return 0.02  # 2% (would be calculated from price history in a real system)
    
    def get_metrics(self):
        """
        Get all relevant orderbook metrics for the simulator.
        Uses caching to avoid recalculating metrics too frequently.
        
        Returns:
            dict: Orderbook metrics
        """
        current_time = time.time()
        
        # Return cached metrics if still valid
        if self._cached_metrics and (current_time - self._metrics_timestamp) < self._metrics_cache_ttl:
            return self._cached_metrics
        
        # Calculate all metrics
        best_ask, best_ask_qty = self.get_best_ask()
        best_bid, best_bid_qty = self.get_best_bid()
        mid_price = self.get_mid_price()
        spread = self.get_spread()
        imbalance = self.get_orderbook_imbalance()
        
        # Update cached metrics
        self._cached_metrics = {
            "timestamp": self.timestamp,
            "exchange": self.exchange,
            "symbol": self.symbol,
            "best_ask": best_ask,
            "best_ask_qty": best_ask_qty,
            "best_bid": best_bid,
            "best_bid_qty": best_bid_qty,
            "mid_price": mid_price,
            "spread": spread,
            "spread_bps": (spread / mid_price * 10000) if mid_price and spread else None,
            "imbalance": imbalance,
        }
        self._metrics_timestamp = current_time
        
        return self._cached_metrics
    
    def get_performance_metrics(self):
        """
        Get performance metrics for the orderbook processing.
        
        Returns:
            dict: Performance metrics
        """
        metrics = {
            "orderbook_size": {
                "asks": len(self.asks),
                "bids": len(self.bids),
                "total": len(self.asks) + len(self.bids)
            },
            "last_update": self.timestamp
        }
        
        if self.update_times:
            metrics.update({
                "avg_update_time_ms": sum(self.update_times) / len(self.update_times) * 1000,
                "min_update_time_ms": min(self.update_times) * 1000,
                "max_update_time_ms": max(self.update_times) * 1000,
            })
        
        return metrics