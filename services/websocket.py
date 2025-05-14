"""
WebSocket client for connecting to orderbook data streams.
"""
import json
import threading
import time
from datetime import datetime
import websocket
from loguru import logger

class OrderbookWebsocketClient:
    """
    WebSocket client for connecting to L2 orderbook data streams.
    Uses the websocket-client library for handling the connection.
    """
    
    def __init__(self, url, on_message_callback, on_error_callback=None, on_close_callback=None):
        """
        Initialize the WebSocket client.
        
        Args:
            url (str): WebSocket endpoint URL
            on_message_callback (callable): Callback function to handle received messages
            on_error_callback (callable, optional): Callback function to handle errors
            on_close_callback (callable, optional): Callback function to handle connection close
        """
        self.url = url
        self.on_message_callback = on_message_callback
        self.on_error_callback = on_error_callback or self._default_on_error
        self.on_close_callback = on_close_callback or self._default_on_close
        
        self.ws = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 5  # seconds
        
        # Performance metrics
        self.message_count = 0
        self.last_message_time = None
        self.processing_times = []
        
    def connect(self):
        """Establish connection to the WebSocket endpoint."""
        logger.info(f"Connecting to WebSocket endpoint: {self.url}")
        
        # Initialize WebSocket connection
        self.ws = websocket.WebSocketApp(
            self.url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open
        )
        
        # Start WebSocket connection in a separate thread
        self.ws_thread = threading.Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()
        
    def disconnect(self):
        """Close the WebSocket connection."""
        if self.ws and self.is_connected:
            logger.info("Disconnecting from WebSocket endpoint")
            self.ws.close()
            self.is_connected = False
    
    def _on_message(self, ws, message):
        """
        Handle incoming WebSocket messages.
        
        Args:
            ws (websocket.WebSocketApp): WebSocket instance
            message (str): Received message
        """
        start_time = time.time()
        
        try:
            # Parse JSON message
            data = json.loads(message)
            
            # Update performance metrics
            self.message_count += 1
            current_time = time.time()
            
            if self.last_message_time:
                interval = current_time - self.last_message_time
                if interval > 1.0:  # Log only if interval exceeds 1 second
                    logger.debug(f"Message interval: {interval:.6f}s")
            
            self.last_message_time = current_time
            
            # Process the message through the callback
            self.on_message_callback(data)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            self.processing_times.append(processing_time)
            
            # Log processing time periodically
            if self.message_count % 100 == 0:
                avg_processing_time = sum(self.processing_times[-100:]) / min(100, len(self.processing_times))
                logger.info(f"Processed {self.message_count} messages. Avg processing time: {avg_processing_time*1000:.2f}ms")
                
        except json.JSONDecodeError:
            logger.error(f"Failed to parse message as JSON: {message[:100]}...")
        except Exception as e:
            logger.exception(f"Error processing message: {str(e)}")
    
    def _on_error(self, ws, error):
        """
        Handle WebSocket errors.
        
        Args:
            ws (websocket.WebSocketApp): WebSocket instance
            error (Exception): Error that occurred
        """
        logger.error(f"WebSocket error: {str(error)}")
        
        if self.on_error_callback:
            self.on_error_callback(error)
    
    def _on_close(self, ws, close_status_code, close_msg):
        """
        Handle WebSocket connection close.
        
        Args:
            ws (websocket.WebSocketApp): WebSocket instance
            close_status_code (int): Status code for the connection close
            close_msg (str): Close message
        """
        self.is_connected = False
        logger.warning(f"WebSocket connection closed: {close_status_code} - {close_msg}")
        
        # Attempt to reconnect
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            reconnect_wait = self.reconnect_delay * self.reconnect_attempts
            logger.info(f"Attempting to reconnect in {reconnect_wait} seconds (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})")
            
            time.sleep(reconnect_wait)
            self.connect()
        else:
            logger.error(f"Maximum reconnection attempts ({self.max_reconnect_attempts}) reached. Giving up.")
        
        if self.on_close_callback:
            self.on_close_callback(close_status_code, close_msg)
    
    def _on_open(self, ws):
        """
        Handle WebSocket connection open.
        
        Args:
            ws (websocket.WebSocketApp): WebSocket instance
        """
        self.is_connected = True
        self.reconnect_attempts = 0
        logger.info("WebSocket connection established")
    
    def _default_on_error(self, error):
        """Default error handler."""
        pass
    
    def _default_on_close(self, close_status_code, close_msg):
        """Default close handler."""
        pass
    
    def get_performance_metrics(self):
        """
        Get performance metrics for the WebSocket client.
        
        Returns:
            dict: Performance metrics
        """
        metrics = {
            "message_count": self.message_count,
            "connected": self.is_connected,
        }
        
        if self.processing_times:
            metrics.update({
                "avg_processing_time_ms": sum(self.processing_times) / len(self.processing_times) * 1000,
                "min_processing_time_ms": min(self.processing_times) * 1000,
                "max_processing_time_ms": max(self.processing_times) * 1000,
            })
        
        return metrics
    def _on_message(self, ws, message):
        """
        Handle incoming WebSocket messages.
        
        Args:
            ws (websocket.WebSocketApp): WebSocket instance
            message (str): Received message
        """
        start_time = time.time()
        
        try:
            # Print raw message for debugging
            # print(f"⭐ RAW WEBSOCKET MESSAGE: {message[:200]}...")
            
            # Parse JSON message
            data = json.loads(message)
            
            # Print parsed data
            # print(f"⭐ PARSED DATA: timestamp={data.get('timestamp')}, asks={len(data.get('asks', []))}, bids={len(data.get('bids', []))}")
            
            # Update performance metrics
            self.message_count += 1
            current_time = time.time()
            
            if self.last_message_time:
                interval = current_time - self.last_message_time
                if interval > 1.0:  # Log only if interval exceeds 1 second
                    logger.debug(f"Message interval: {interval:.6f}s")
            
            self.last_message_time = current_time
            
            # Process the message through the callback
            self.on_message_callback(data)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            self.processing_times.append(processing_time)
            
            # Log processing time periodically
            if self.message_count % 100 == 0:
                avg_processing_time = sum(self.processing_times[-100:]) / min(100, len(self.processing_times))
                logger.info(f"Processed {self.message_count} messages. Avg processing time: {avg_processing_time*1000:.2f}ms")
                
        except json.JSONDecodeError:
            print(f"⭐ ERROR: Failed to parse message as JSON: {message[:100]}...")
            logger.error(f"Failed to parse message as JSON: {message[:100]}...")
        except Exception as e:
            print(f"⭐ ERROR: Error processing message: {str(e)}")
            logger.exception(f"Error processing message: {str(e)}")