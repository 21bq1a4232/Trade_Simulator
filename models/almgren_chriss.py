"""
Implementation of the Almgren-Chriss market impact model.

Reference: https://www.linkedin.com/pulse/understanding-almgren-chriss-model-optimal-portfolio-execution-pal-pmeqc/
"""
import numpy as np
from loguru import logger

class AlmgrenChrissModel:
    """
    Implementation of the Almgren-Chriss market impact model for estimating price impact.
    
    The model consists of two components:
    1. Temporary impact: immediate price impact that occurs during execution
    2. Permanent impact: lasting price impact that remains after execution
    
    The model is parameterized by:
    - market_impact_factor: factor for the market impact calculation
    - volatility_factor: factor for the volatility component
    - risk_aversion: trader's risk aversion parameter
    """
    
    def __init__(self, market_impact_factor=0.1, volatility_factor=0.5, risk_aversion=1.0):
        """
        Initialize the Almgren-Chriss model.
        
        Args:
            market_impact_factor (float): Factor for market impact calculation
            volatility_factor (float): Factor for volatility component
            risk_aversion (float): Trader's risk aversion parameter
        """
        self.market_impact_factor = market_impact_factor
        self.volatility_factor = volatility_factor
        self.risk_aversion = risk_aversion
    
    def estimate_market_impact(self, quantity, price, daily_volume, volatility, is_buy=True):
        """
        Estimate market impact using the Almgren-Chriss model.
        
        Args:
            quantity (float): Order quantity
            price (float): Current price
            daily_volume (float): Average daily volume
            volatility (float): Asset volatility (decimal, e.g., 0.02 for 2%)
            is_buy (bool): True if it's a buy order, False for sell
        
        Returns:
            tuple: (temporary_impact, permanent_impact, total_impact)
        """
        try:
            # Relative order size as a fraction of daily volume
            relative_size = quantity / daily_volume
            
            # Calculate temporary impact (immediate price reaction)
            # Temporary impact is proportional to order size and volatility
            temporary_impact = price * self.market_impact_factor * volatility * np.sqrt(relative_size)
            
            # Calculate permanent impact (lasting price change)
            # Permanent impact is proportional to order size
            permanent_impact = price * self.market_impact_factor * relative_size
            
            # Apply sign based on order direction
            sign = 1 if is_buy else -1
            temporary_impact *= sign
            permanent_impact *= sign
            
            # Total impact
            total_impact = temporary_impact + permanent_impact
            
            return {
                "temporary_impact": temporary_impact,
                "permanent_impact": permanent_impact,
                "total_impact": total_impact,
                "total_impact_bps": (total_impact / price) * 10000  # in basis points
            }
            
        except Exception as e:
            logger.exception(f"Error estimating market impact: {str(e)}")
            return {
                "temporary_impact": 0,
                "permanent_impact": 0,
                "total_impact": 0,
                "total_impact_bps": 0
            }
    
    def estimate_optimal_execution_time(self, quantity, price, daily_volume, volatility):
        """
        Estimate optimal execution time based on the Almgren-Chriss model.
        
        Args:
            quantity (float): Order quantity
            price (float): Current price
            daily_volume (float): Average daily volume
            volatility (float): Asset volatility (decimal)
        
        Returns:
            float: Optimal execution time in hours
        """
        try:
            # Relative order size
            relative_size = quantity / daily_volume
            
            # Calculate optimal trading time (simplified formula)
            # In the full model, this depends on the trader's risk aversion
            optimal_time = np.sqrt(
                self.risk_aversion * (volatility**2) * relative_size / 
                (2 * self.market_impact_factor * price)
            )
            
            # Convert to hours (assuming daily_volume is daily)
            optimal_time_hours = optimal_time * 24
            
            return optimal_time_hours
            
        except Exception as e:
            logger.exception(f"Error estimating optimal execution time: {str(e)}")
            return 0.5  # Default to 30 minutes
    
    def estimate_market_impact_from_orderbook(self, orderbook, quantity, price, daily_volume, volatility, is_buy=True):
        """
        Estimate market impact using the Almgren-Chriss model and current orderbook state.
        This method enhances the basic model by incorporating orderbook imbalance.
        
        Args:
            orderbook (Orderbook): Current orderbook state
            quantity (float): Order quantity
            price (float): Current price
            daily_volume (float): Average daily volume
            volatility (float): Asset volatility (decimal)
            is_buy (bool): True if it's a buy order, False for sell
        
        Returns:
            dict: Market impact components
        """
        # Get orderbook imbalance (bid/ask volume ratio)
        imbalance = orderbook.get_orderbook_imbalance()
        
        # Adjust market impact based on orderbook imbalance
        # If buying and imbalance > 1 (more bids than asks), impact increases
        # If selling and imbalance < 1 (more asks than bids), impact increases
        impact_multiplier = 1.0
        
        if is_buy and imbalance > 1:
            # More buying pressure, likely to increase impact
            impact_multiplier = 1.0 + 0.2 * (imbalance - 1)  # Increase impact by up to 20%
        elif not is_buy and imbalance < 1:
            # More selling pressure, likely to increase impact
            impact_multiplier = 1.0 + 0.2 * (1 - imbalance)  # Increase impact by up to 20%
        
        # Get base impact
        base_impact = self.estimate_market_impact(quantity, price, daily_volume, volatility, is_buy)
        
        # Apply multiplier
        adjusted_impact = {k: v * impact_multiplier for k, v in base_impact.items()}
        
        # Add diagnosis info
        adjusted_impact["orderbook_imbalance"] = imbalance
        adjusted_impact["impact_multiplier"] = impact_multiplier
        
        return adjusted_impact