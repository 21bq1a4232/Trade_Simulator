"""
Maker/Taker proportion prediction model using logistic regression.
"""
import numpy as np
from sklearn.linear_model import LogisticRegression
from loguru import logger
from collections import deque

class MakerTakerModel:
    """
    Model for predicting the maker/taker proportion for order execution
    using logistic regression.
    """
    
    def __init__(self, history_size=1000):
        """
        Initialize the maker/taker model.
        
        Args:
            history_size (int): Maximum size of execution history to maintain
        """
        self.history_size = history_size
        
        # Execution history for training the model
        self.execution_history = deque(maxlen=history_size)
        
        # Features used for prediction
        self.features = [
            "quantity_usd",      # Order size in USD
            "relative_size",     # Order size relative to available liquidity
            "spread_bps",        # Spread in basis points
            "volatility",        # Asset volatility
            "imbalance",         # Orderbook imbalance
            "best_bid_qty",      # Quantity at best bid
            "best_ask_qty"       # Quantity at best ask
        ]
        
        # Initialize model
        self.model = LogisticRegression(solver='liblinear')
        
        # Model metadata
        self.is_trained = False
        self.training_samples = 0
        self.last_training_accuracy = 0.0
    
    def add_observation(self, features, maker_percentage):
        """
        Add an execution observation to the history.
        
        Args:
            features (dict): Feature values used for prediction
            maker_percentage (float): Actual maker percentage observed (0.0-1.0)
        """
        try:
            # Extract feature values in the correct order
            feature_values = [features.get(f, 0.0) for f in self.features]
            
            # Add to history
            self.execution_history.append((feature_values, maker_percentage))
            
            # Log the observation
            logger.debug(f"Added maker/taker observation: features={feature_values}, maker_pct={maker_percentage}")
            
            # Retrain the model if we have enough data and haven't trained yet
            if len(self.execution_history) >= 50 and not self.is_trained:
                self.train_model()
                
        except Exception as e:
            logger.exception(f"Error adding maker/taker observation: {str(e)}")
    
    def train_model(self):
        """
        Train the logistic regression model using the current execution history.
        """
        try:
            if len(self.execution_history) < 10:
                logger.warning("Not enough data to train maker/taker model")
                return False
            
            # Extract features and targets from history
            X = np.array([obs[0] for obs in self.execution_history])
            y = np.array([1 if obs[1] > 0.5 else 0 for obs in self.execution_history])  # Binary classification
            
            # Train logistic regression model
            self.model.fit(X, y)
            
            # Calculate training accuracy
            y_pred = self.model.predict(X)
            accuracy = np.mean(y_pred == y)
            self.last_training_accuracy = accuracy
            
            # Update metadata
            self.is_trained = True
            self.training_samples = len(self.execution_history)
            
            logger.info(f"Trained maker/taker model on {self.training_samples} samples. Accuracy: {accuracy:.4f}")
            
            return True
            
        except Exception as e:
            logger.exception(f"Error training maker/taker model: {str(e)}")
            return False
    
    def predict_maker_percentage(self, features):
        """
        Predict the maker percentage for a given set of features.
        
        Args:
            features (dict): Feature values for prediction
        
        Returns:
            float: Predicted maker percentage (0.0-1.0)
        """
        try:
            # If model is not trained, use a simple heuristic
            if not self.is_trained:
                # Default heuristic based on order size and spread
                quantity_usd = features.get("quantity_usd", 100.0)
                spread_bps = features.get("spread_bps", 10.0)
                imbalance = features.get("imbalance", 1.0)
                is_buy = features.get("is_buy", True)
                
                # Simple heuristic: larger orders and wider spreads favor taker (lower maker %)
                # Base maker percentage: 30% for small orders, decreasing for larger orders
                base_maker_pct = 0.3 * (1.0 - min(0.8, np.log1p(quantity_usd / 1000) * 0.1))
                
                # Adjust for spread: wider spreads favor taker
                spread_factor = max(0.1, 1.0 - spread_bps / 50.0)  # Reduces maker % for wider spreads
                
                # Adjust for imbalance
                if (is_buy and imbalance > 1.5) or (not is_buy and imbalance < 0.5):
                    # Favorable imbalance: increase maker %
                    imbalance_factor = 1.5
                else:
                    # Neutral or unfavorable imbalance: normal maker %
                    imbalance_factor = 1.0
                
                # Calculate final maker percentage
                maker_percentage = base_maker_pct * spread_factor * imbalance_factor
                maker_percentage = max(0.0, min(1.0, maker_percentage))  # Clamp to [0, 1]
                
                logger.debug(f"Using heuristic maker percentage: {maker_percentage:.2%}")
                return maker_percentage
            
            # Extract feature values in the correct order
            feature_values = np.array([[features.get(f, 0.0) for f in self.features]])
            
            # Predict maker probability using logistic regression
            maker_prob = self.model.predict_proba(feature_values)[0][1]
            
            # Transform to expected maker percentage
            # Instead of binary 0/1, use a continuous range based on probability
            maker_percentage = maker_prob
            
            return maker_percentage
            
        except Exception as e:
            logger.exception(f"Error predicting maker percentage: {str(e)}")
            
            # Fallback to a conservative estimate
            return 0.1  # Assume 10% maker as a safe default
    
    def predict_maker_taker_from_orderbook(self, orderbook, quantity_usd, price, volatility=0.02, side="buy"):
        """
        Predict maker/taker proportion using the current orderbook state.
        
        Args:
            orderbook (Orderbook): Current orderbook state
            quantity_usd (float): Order size in USD
            price (float): Current price
            volatility (float): Asset volatility (decimal)
            side (str): 'buy' or 'sell'
        
        Returns:
            dict: Maker/taker prediction results
        """
        try:
            # Extract orderbook metrics
            metrics = orderbook.get_metrics()
            
            # Calculate derived features
            spread_bps = metrics.get("spread_bps", 10.0)
            imbalance = metrics.get("imbalance", 1.0)
            best_bid_qty = metrics.get("best_bid_qty", 0.0)
            best_ask_qty = metrics.get("best_ask_qty", 0.0)
            
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
                "best_bid_qty": best_bid_qty,
                "best_ask_qty": best_ask_qty,
                "is_buy": is_buy
            }
            
            # Get maker percentage prediction
            maker_percentage = self.predict_maker_percentage(features)
            taker_percentage = 1.0 - maker_percentage
            
            # Complete results dictionary
            results = {
                "maker_percentage": maker_percentage,
                "taker_percentage": taker_percentage,
                "features": features,
                "is_model_trained": self.is_trained,
                "training_samples": self.training_samples
            }
            
            return results
            
        except Exception as e:
            logger.exception(f"Error predicting maker/taker from orderbook: {str(e)}")
            
            # Return a conservative estimate
            return {
                "maker_percentage": 0.1,  # 10% maker as a safe default
                "taker_percentage": 0.9,  # 90% taker
                "features": {},
                "is_model_trained": False,
                "training_samples": 0
            }