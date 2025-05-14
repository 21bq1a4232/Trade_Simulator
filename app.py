"""
Main Flask application for the trade simulator.
"""
import os
import json
import threading
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO

import config
from utils.logging_config import setup_logging
from services.websocket import OrderbookWebsocketClient
from services.simulator import TradeSimulator

# Set up logging
logger = setup_logging(config)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize trade simulator
simulator = TradeSimulator(config)

# Initialize WebSocket client
def on_orderbook_message(data):
    """Callback for handling orderbook WebSocket messages."""
    # simulator.process_orderbook_data(data)
    # print(f"⭐ RECEIVED ORDERBOOK DATA: {data.get('timestamp')} - asks: {len(data.get('asks', []))}, bids: {len(data.get('bids', []))}")
    simulator.process_orderbook_data(data)
    # Emit updated simulation results to connected clients
    emit_simulation_results()

ws_client = OrderbookWebsocketClient(config.WEBSOCKET_URL, on_orderbook_message)

# Periodic update function
def emit_simulation_results():
    """Emit simulation results to all connected clients."""
    results = simulator.get_simulation_results()
    socketio.emit('simulation_results', results)

# Set up periodic updates
def periodic_update():
    """Send periodic updates to clients."""
    while True:
        socketio.sleep(1)  # Update every second
        emit_simulation_results()
        logger.info("Periodic update sent to clients")
# Flask routes
@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html', 
                          exchanges=config.EXCHANGES,
                          spot_assets=config.SPOT_ASSETS,
                          order_types=config.ORDER_TYPES,
                          fee_tiers=list(config.OKX_FEE_TIERS.keys()),
                          default_exchange=config.DEFAULT_EXCHANGE,
                          default_spot_asset=config.DEFAULT_SPOT_ASSET,
                          default_order_type=config.DEFAULT_ORDER_TYPE,
                          default_quantity=config.DEFAULT_QUANTITY,
                          default_volatility=config.DEFAULT_VOLATILITY,
                          default_fee_tier=config.DEFAULT_FEE_TIER)

@app.route('/api/parameters', methods=['GET'])
def get_parameters():
    """Get current simulation parameters."""
    return jsonify(simulator.get_parameters())

# In app.py

@app.route('/api/parameters', methods=['POST'])
def set_parameters():
    """Set simulation parameters."""
    try:
        params = request.json
        results = {}
        print("⭐ Received parameters to set:", params)
        logger.info(f"Received parameters to set: {params}")
        
        for param_name, param_value in params.items():
            success = simulator.set_parameter(param_name, param_value)
            results[param_name] = success
            print(f"⭐ Set parameter {param_name}: {success}")
        
        print("⭐ Set parameters results:", results)
        logger.info(f"Set parameters results: {results}")
        return jsonify({"success": True, "results": results})
    
    except Exception as e:
        print(f"⭐ ERROR setting parameters: {str(e)}")
        logger.exception(f"Error setting parameters: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/results')
def get_results():
    print("Simulation results requested-------->>>>>", simulator.get_simulation_results())
    logger.info("Simulation results requested")
    """Get current simulation results."""
    return jsonify(simulator.get_simulation_results())

@app.route('/api/performance')
def get_performance():
    """Get performance metrics."""
    print("Performance metrics requested")
    logger.info("Performance metrics requested")
    return jsonify(simulator.get_performance_metrics())

@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    logger.info("Client connected")
    
    # Send current simulation results to the new client
    emit_simulation_results()

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logger.info("Client disconnected")

@socketio.on('set_parameter')
def handle_set_parameter(data):
    """Handle parameter setting from WebSocket."""
    try:
        param_name = data.get('name')
        param_value = data.get('value')
        print(f"Received parameter update: {param_name} = {param_value}")
        logger.info(f"Received parameter update: {param_name} = {param_value}")
        if not param_name:
            return {"success": False, "error": "Missing parameter name"}
        
        success = simulator.set_parameter(param_name, param_value)
        
        return {"success": success}
    
    except Exception as e:
        logger.exception(f"Error setting parameter via WebSocket: {str(e)}")
        return {"success": False, "error": str(e)}

def start_server():
    """Start the WebSocket client and simulator."""
    print("⭐ Starting services...")
    # Start trade simulator
    simulator.start()
    
    # Connect WebSocket client
    print("⭐ Connecting to WebSocket...")
    ws_client.connect()
    print("⭐ WebSocket connection initiated")
    
    # Start periodic update thread
    socketio.start_background_task(periodic_update)

if __name__ == '__main__':
    # Start services
    start_server()
    
    # Run Flask server
    port = int(os.environ.get("PORT", config.PORT))
    socketio.run(app, host=config.HOST, port=port, debug=config.DEBUG)