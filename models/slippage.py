"""
Slippage estimation model using regression techniques.
"""
import numpy as np
from sklearn.linear_model import LinearRegression
# Remove the incorrect import of QuantileRegression
from loguru import logger
from collections import deque

class SlippageModel:
    """
    Model for estimating slippage using linear and quantile regression.
    Maintains a history of actual slippage observations to train the model.
    """
    
    def __init__(self, history_size=1000):
        """
        Initialize the slippage model.
        
        Args:
            history_size (int): Maximum size of slippage history to maintain
        """
        self.history_size = history_size
        
        # Slippage history for training the model
        self.slippage_history = deque(maxlen=history_size)
        
        # Features used for prediction
        self.features = [
            "quantity_usd",         # Order size in USD
            "relative_size",        # Order size relative to available liquidity
            "spread_bps",           # Spread in basis points
            "volatility",           # Asset volatility
            "imbalance"             # Orderbook imbalance
        ]
        
        # Initialize models
        self.linear_model = LinearRegression()
        self.quantile_model = None  # Will be initialized when training
        
        # Model metadata
        self.is_trained = False
        self.training_samples = 0
        self.last_training_error = float('inf')
    
    def add_observation(self, features, actual_slippage):
        """
        Add a slippage observation to the history.
        
        Args:
            features (dict): Feature values used for prediction
            actual_slippage (float): Actual slippage observed
        """
        try:
            # Extract feature values in the correct order
            feature_values = [features.get(f, 0.0) for f in self.features]
            
            # Add to history
            self.slippage_history.append((feature_values, actual_slippage))
            
            # Log the observation
            logger.debug(f"Added slippage observation: features={feature_values}, slippage={actual_slippage}")
            
            # Retrain the model if we have enough data and haven't trained yet
            if len(self.slippage_history) >= 50 and not self.is_trained:
                self.train_model()
                
        except Exception as e:
            logger.exception(f"Error adding slippage observation: {str(e)}")
    
    def train_model(self):
        """
        Train the regression models using the current slippage history.
        """
        try:
            if len(self.slippage_history) < 10:
                logger.warning("Not enough data to train slippage model")
                return False
            
            # Extract features and targets from history
            X = np.array([obs[0] for obs in self.slippage_history])
            y = np.array([obs[1] for obs in self.slippage_history])
            
            # Train linear regression model
            self.linear_model.fit(X, y)
            
            # Train quantile regression model for 90th percentile
            # Only available in newer scikit-learn versions
            try:
                from sklearn.linear_model import QuantileRegressor
                self.quantile_model = QuantileRegressor(quantile=0.9, alpha=0.5)
                self.quantile_model.fit(X, y)
            except (ImportError, AttributeError):
                # Fallback to using linear model with a safety factor
                self.quantile_model = None
                logger.warning("QuantileRegressor not available, using linear model with safety factor")
            
            # Calculate training error
            y_pred = self.linear_model.predict(X)
            mse = np.mean((y - y_pred) ** 2)
            self.last_training_error = mse
            
            # Update metadata
            self.is_trained = True
            self.training_samples = len(self.slippage_history)
            
            logger.info(f"Trained slippage model on {self.training_samples} samples. MSE: {mse:.6f}")
            
            return True
            
        except Exception as e:
            logger.exception(f"Error training slippage model: {str(e)}")
            return False
    
    def predict_slippage(self, features, confidence_level="expected"):
        """
        Predict slippage for a given set of features.
        
        Args:
            features (dict): Feature values for prediction
            confidence_level (str): 'expected' for mean estimation, 'conservative' for higher quantile
        
        Returns:
            float: Predicted slippage
        """
        try:
            # If model is not trained, use a simple heuristic
            if not self.is_trained:
                # Default heuristic based on order size and spread
                quantity_usd = features.get("quantity_usd", 100.0)
                spread_bps = features.get("spread_bps", 10.0)
                
                # Simple heuristic model: slippage ~ spread + log(size) * volatility
                # 0.5 * spread as a starting point, then scale with order size
                heuristic_slippage = 0.5 * spread_bps * (1 + np.log1p(quantity_usd / 100) * 0.2)
                
                # Add volatility factor if available
                volatility = features.get("volatility", 0.02)
                heuristic_slippage *= (1 + 5 * volatility)
                
                # Add imbalance factor if available
                imbalance = features.get("imbalance", 1.0)
                # If imbalance > 1, more bids than asks, reduce buy slippage
                # If imbalance < 1, more asks than bids, reduce sell slippage
                is_buy = features.get("is_buy", True)
                if (is_buy and imbalance < 1) or (not is_buy and imbalance > 1):
                    # Adverse conditions: increase slippage
                    imbalance_factor = 1 + 0.5 * abs(1 - imbalance)
                    heuristic_slippage *= imbalance_factor
                
                logger.debug(f"Using heuristic slippage estimate: {heuristic_slippage:.2f} bps")
                return heuristic_slippage
            
            # Extract feature values in the correct order
            feature_values = np.array([[features.get(f, 0.0) for f in self.features]])
            
            # Predict using the appropriate model
            if confidence_level.lower() == "conservative" and self.quantile_model is not None:
                # Use quantile regression for conservative estimate
                predicted_slippage = self.quantile_model.predict(feature_values)[0]
            else:
                # Use linear regression for expected estimate
                predicted_slippage = self.linear_model.predict(feature_values)[0]
                
                # If quantile model not available but conservative estimate requested,
                # add a safety factor based on training error
                if confidence_level.lower() == "conservative":
                    safety_factor = 1.0 + 2.0 * np.sqrt(self.last_training_error)
                    predicted_slippage *= safety_factor
            
            return predicted_slippage
            
        except Exception as e:
            logger.exception(f"Error predicting slippage: {str(e)}")
            
            # Fallback to simple heuristic
            quantity_usd = features.get("quantity_usd", 100.0)
            spread_bps = features.get("spread_bps", 10.0)
            
            # Simple model: slippage ~ 0.5 * spread + log(size)
            return 0.5 * spread_bps * (1 + np.log1p(quantity_usd / 100) * 0.2)
    
    def estimate_slippage_from_orderbook(self, orderbook, quantity_usd, price, volatility=0.02, side="buy"):
        """
        Estimate slippage using the current orderbook state.
        
        Args:
            orderbook (Orderbook): Current orderbook state
            quantity_usd (float): Order size in USD
            price (float): Current price
            volatility (float): Asset volatility (decimal)
            side (str): 'buy' or 'sell'
        
        Returns:
            dict: Slippage estimation results
        """
        try:
            # Extract orderbook metrics
            metrics = orderbook.get_metrics()
            
            # Calculate derived features
            mid_price = metrics.get("mid_price", price)
            spread_bps = metrics.get("spread_bps", 10.0)
            imbalance = metrics.get("imbalance", 1.0)
            
            # Calculate quantity in base asset
            quantity_asset = quantity_usd / price if price > 0 else 0
            
            # Calculate relative size
            # Estimate available liquidity (5 levels of depth)
            is_buy = side.lower() == "buy"
            available_liquidity = 0
            
            if is_buy:
                # For buys, sum up ask quantities
                for ask_price, ask_qty in sorted(orderbook.asks.items())[:5]:
                    available_liquidity += ask_qty
            else:
                # For sells, sum up bid quantities
                for bid_price, bid_qty in sorted(orderbook.bids.items(), reverse=True)[:5]:
                    available_liquidity += bid_qty
            
            # Relative size (capped at 1.0)
            relative_size = min(1.0, quantity_asset / available_liquidity) if available_liquidity > 0 else 1.0
            
            # Create feature dictionary
            features = {
                "quantity_usd": quantity_usd,
                "relative_size": relative_size,
                "spread_bps": spread_bps,
                "volatility": volatility,
                "imbalance": imbalance,
                "is_buy": is_buy
            }
            
            # Get slippage predictions
            expected_slippage = self.predict_slippage(features, "expected")
            conservative_slippage = self.predict_slippage(features, "conservative")
            
            # Calculate direct slippage from orderbook simulation
            simulated_slippage = None
            vwap, filled_qty, remaining_qty = orderbook.get_volume_weighted_price(quantity_asset, side)
            
            if vwap is not None and filled_qty > 0:
                if is_buy:
                    # For buys, slippage is positive when VWAP > mid_price
                    simulated_slippage = (vwap / mid_price - 1) * 10000  # in basis points
                else:
                    # For sells, slippage is positive when VWAP < mid_price
                    simulated_slippage = (1 - vwap / mid_price) * 10000  # in basis points
            
            # If we have a direct simulation, blend with the model prediction
            if simulated_slippage is not None:
                # Weight more heavily toward simulation if enough liquidity
                fill_ratio = filled_qty / quantity_asset if quantity_asset > 0 else 0
                simulation_weight = fill_ratio
                model_weight = 1.0 - simulation_weight
                
                # Blend the estimates
                blended_slippage = (simulated_slippage * simulation_weight + 
                                  expected_slippage * model_weight)
                
                # Update expected slippage with the blended value
                expected_slippage = blended_slippage
            
            # Complete results dictionary
            results = {
                "expected_slippage_bps": expected_slippage,
                "conservative_slippage_bps": conservative_slippage,
                "simulated_slippage_bps": simulated_slippage,
                "features": features,
                "fill_ratio": filled_qty / quantity_asset if quantity_asset > 0 else 0,
                "available_liquidity": available_liquidity,
                "is_model_trained": self.is_trained,
                "training_samples": self.training_samples
            }
            
            return results
            
        except Exception as e:
            logger.exception(f"Error estimating slippage from orderbook: {str(e)}")
            
            # Return a default estimate
            return {
                "expected_slippage_bps": 10.0,  # 10 bps default
                "conservative_slippage_bps": 20.0,  # 20 bps default
                "simulated_slippage_bps": None,
                "features": {},
                "fill_ratio": 0,
                "available_liquidity": 0,
                "is_model_trained": False,
                "training_samples": 0
            }