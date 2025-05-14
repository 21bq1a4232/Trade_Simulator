"""
Fee calculation model for cryptocurrency exchanges.
"""
from loguru import logger

class FeeModel:
    """
    Model for calculating trading fees based on exchange fee structures.
    Supports different fee tiers and maker/taker fee types.
    """
    
    def __init__(self, fee_structure=None):
        """
        Initialize the fee model.
        
        Args:
            fee_structure (dict): Fee structure dictionary. If None, will use defaults.
        """
        # Default fee structure (OKX)
        self.default_fee_structure = {
            "OKX": {
                "VIP0": {"maker": 0.0008, "taker": 0.001},
                "VIP1": {"maker": 0.0007, "taker": 0.0009},
                "VIP2": {"maker": 0.0006, "taker": 0.0008},
                "VIP3": {"maker": 0.0005, "taker": 0.0007},
                "VIP4": {"maker": 0.0003, "taker": 0.0005},
                "VIP5": {"maker": 0.0000, "taker": 0.0003},
            }
        }
        
        self.fee_structure = fee_structure or self.default_fee_structure
    
    def get_fee_rates(self, exchange, fee_tier="VIP0"):
        """
        Get the fee rates for a specific exchange and tier.
        
        Args:
            exchange (str): Exchange name
            fee_tier (str): Fee tier level
        
        Returns:
            dict: Maker and taker fee rates
        """
        try:
            # Get fee rates for the specified exchange and tier
            exchange_fees = self.fee_structure.get(exchange)
            if not exchange_fees:
                logger.warning(f"No fee structure found for exchange: {exchange}, using default OKX fees")
                exchange_fees = self.fee_structure.get("OKX")
            
            tier_fees = exchange_fees.get(fee_tier)
            if not tier_fees:
                logger.warning(f"No fee tier found for {fee_tier}, using VIP0")
                tier_fees = exchange_fees.get("VIP0")
            
            return tier_fees
        
        except Exception as e:
            logger.exception(f"Error getting fee rates: {str(e)}")
            # Return a default fee structure
            return {"maker": 0.001, "taker": 0.002}
    
    def calculate_fees(self, exchange, order_type, quantity, price, fee_tier="VIP0", maker_percentage=0.0):
        """
        Calculate trading fees for an order.
        
        Args:
            exchange (str): Exchange name
            order_type (str): Order type (e.g., 'market', 'limit')
            quantity (float): Order quantity
            price (float): Execution price
            fee_tier (str): Fee tier level
            maker_percentage (float): Percentage of order executed as maker (0.0-1.0)
        
        Returns:
            dict: Fee calculation results
        """
        try:
            # Get fee rates
            fee_rates = self.get_fee_rates(exchange, fee_tier)
            maker_rate = fee_rates.get("maker", 0.001)
            taker_rate = fee_rates.get("taker", 0.002)
            
            # For market orders, assume 100% taker unless specified otherwise
            if order_type.lower() == "market":
                if maker_percentage is None:
                    maker_percentage = 0.0
            
            # Ensure maker_percentage is in valid range
            maker_percentage = max(0.0, min(1.0, maker_percentage))
            taker_percentage = 1.0 - maker_percentage
            
            # Calculate notional value (total value of the order)
            notional_value = quantity * price
            
            # Calculate fees
            maker_fee = notional_value * maker_rate * maker_percentage
            taker_fee = notional_value * taker_rate * taker_percentage
            total_fee = maker_fee + taker_fee
            
            # Calculate effective fee rate
            effective_fee_rate = total_fee / notional_value if notional_value > 0 else 0.0
            
            return {
                "maker_fee": maker_fee,
                "taker_fee": taker_fee,
                "total_fee": total_fee,
                "maker_fee_rate": maker_rate,
                "taker_fee_rate": taker_rate,
                "effective_fee_rate": effective_fee_rate,
                "maker_percentage": maker_percentage,
                "taker_percentage": taker_percentage,
                "fee_tier": fee_tier,
                "notional_value": notional_value
            }
            
        except Exception as e:
            logger.exception(f"Error calculating fees: {str(e)}")
            return {
                "maker_fee": 0,
                "taker_fee": 0,
                "total_fee": 0,
                "maker_fee_rate": 0,
                "taker_fee_rate": 0,
                "effective_fee_rate": 0,
                "maker_percentage": 0,
                "taker_percentage": 0,
                "fee_tier": fee_tier,
                "notional_value": 0
            }