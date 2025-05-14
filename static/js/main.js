// Main JavaScript for the Trade Simulator UI

// Global variables
let socket = null;
let costChart = null;
let lastUpdateTime = 0;
let connectionStatus = false;
let dataStatus = false;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    // Set up form submission handler
    document.getElementById('param-form').addEventListener('submit', handleFormSubmit);

    // Format volatility as percentage
    const volatilityInput = document.getElementById('volatility');
    volatilityInput.value = parseFloat(volatilityInput.value) * 100;
    volatilityInput.addEventListener('change', function() {
        // Ensure the value is within bounds
        if (parseFloat(this.value) < 0.1) this.value = 0.1;
        if (parseFloat(this.value) > 100) this.value = 100;
    });

    // Initialize the cost breakdown chart
    initializeCostChart();

    // Connect to WebSocket
    connectWebSocket();
});

// Initialize the cost breakdown chart
function initializeCostChart() {
    const ctx = document.getElementById('cost-chart').getContext('2d');
    
    costChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Slippage', 'Fees', 'Market Impact', 'Net Cost'],
            datasets: [{
                label: 'Cost Components (bps)',
                data: [0, 0, 0, 0],
                backgroundColor: [
                    'rgba(54, 162, 235, 0.7)',
                    'rgba(255, 159, 64, 0.7)',
                    'rgba(255, 99, 132, 0.7)',
                    'rgba(75, 192, 192, 0.7)'
                ],
                borderColor: [
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 159, 64, 1)',
                    'rgba(255, 99, 132, 1)',
                    'rgba(75, 192, 192, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Basis Points (bps)'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${context.raw.toFixed(2)} bps`;
                        }
                    }
                }
            }
        }
    });
}

// Connect to WebSocket
function connectWebSocket() {
    // Initialize the socket.io connection
    socket = io();

    // Connection events
    socket.on('connect', function() {
        connectionStatus = true;
        updateConnectionStatus();
        console.log('Connected to WebSocket');
    });

    socket.on('disconnect', function() {
        connectionStatus = false;
        dataStatus = false;
        updateConnectionStatus();
        updateDataStatus();
        console.log('Disconnected from WebSocket');
    });

    // Simulation results events
    socket.on('simulation_results', function(data) {
        dataStatus = true;
        updateDataStatus();
        updateSimulationResults(data);
    });
}

// Handle form submission
// In static/js/main.js

function handleFormSubmit(event) {
    event.preventDefault();
    
    // Show loading indicator
    const submitButton = event.target.querySelector('button[type="submit"]');
    const originalText = submitButton.textContent;
    submitButton.textContent = "Updating...";
    submitButton.disabled = true;
    
    // Get form data
    const formData = new FormData(event.target);
    const params = {};
    
    // Convert form data to object
    for (const [name, value] of formData.entries()) {
        // Special handling for volatility (convert from percentage to decimal)
        if (name === 'volatility') {
            params[name] = parseFloat(value) / 100;
        } else if (name === 'quantity') {
            params[name] = parseFloat(value);
        } else {
            params[name] = value;
        }
    }
    
    console.log("Sending parameters:", params);
    
    // Send parameters to server with timeout
    const fetchPromise = fetch('/api/parameters', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(params)
    });
    
    // Add timeout to prevent hanging
    const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('Request timed out')), 5000)
    );
    
    Promise.race([fetchPromise, timeoutPromise])
        .then(response => response.json())
        .then(data => {
            // Reset button
            submitButton.textContent = originalText;
            submitButton.disabled = false;
            
            if (data.success) {
                console.log('Parameters updated successfully');
            } else {
                console.error('Error updating parameters', data.error);
                alert('Error updating parameters: ' + data.error);
            }
        })
        .catch(error => {
            // Reset button even on error
            submitButton.textContent = originalText;
            submitButton.disabled = false;
            
            console.error('Error:', error);
            alert('Error updating parameters: ' + error.message);
        });
}

// Update connection status indicator
function updateConnectionStatus() {
    const indicator = document.getElementById('connection-status');
    const text = document.getElementById('connection-text');
    
    if (connectionStatus) {
        indicator.classList.remove('disconnected');
        indicator.classList.add('connected');
        text.textContent = 'Connected';
    } else {
        indicator.classList.remove('connected');
        indicator.classList.add('disconnected');
        text.textContent = 'Disconnected';
    }
}

// Update data status indicator
function updateDataStatus() {
    const indicator = document.getElementById('data-status');
    const text = document.getElementById('data-text');
    
    if (dataStatus) {
        indicator.classList.remove('inactive');
        indicator.classList.add('active');
        text.textContent = 'Live Data';
    } else {
        indicator.classList.remove('active');
        indicator.classList.add('inactive');
        text.textContent = 'No Data';
    }
}

// Update simulation results UI
function updateSimulationResults(data) {
    // Check if we received a real update
    const timestamp = new Date(data.timestamp);
    if (data.timestamp && timestamp > lastUpdateTime) {
        lastUpdateTime = timestamp;
        
        // Format timestamp
        const formattedTime = timestamp.toLocaleTimeString();
        document.getElementById('results-timestamp').textContent = formattedTime;
        
        // Update slippage
        const expectedSlippage = data.slippage.expected_bps.toFixed(2);
        updateElementWithPulse('expected-slippage', expectedSlippage);
        
        // Update fees
        const expectedFees = data.fees.effective_rate_bps.toFixed(2);
        updateElementWithPulse('expected-fees', expectedFees);
        
        // Update market impact
        const expectedImpact = data.market_impact.total_bps.toFixed(2);
        updateElementWithPulse('expected-impact', expectedImpact);
        
        // Update net cost
        const netCost = data.net_cost.expected_bps.toFixed(2);
        updateElementWithPulse('net-cost', netCost);
        
        // Update maker/taker proportion
        const makerPercentage = data.maker_taker.maker_percentage * 100;
        const takerPercentage = data.maker_taker.taker_percentage * 100;
        
        const makerProgress = document.getElementById('maker-progress');
        const takerProgress = document.getElementById('taker-progress');
        
        makerProgress.style.width = `${makerPercentage}%`;
        makerProgress.textContent = `Maker: ${makerPercentage.toFixed(1)}%`;
        makerProgress.setAttribute('aria-valuenow', makerPercentage);
        
        takerProgress.style.width = `${takerPercentage}%`;
        takerProgress.textContent = `Taker: ${takerPercentage.toFixed(1)}%`;
        takerProgress.setAttribute('aria-valuenow', takerPercentage);
        
        // Update orderbook data
        if (data.orderbook) {
            updateOrderbookData(data.orderbook);
        }
        
        // Update performance metrics
        if (data.performance) {
            const latency = data.performance.internal_latency_ms.toFixed(2);
            updateElementWithPulse('internal-latency', `${latency} ms`);
        }
        
        // Update cost chart
        updateCostChart(data);
    }
}

// Update orderbook data
function updateOrderbookData(orderbook) {
    // Format orderbook timestamp
    if (orderbook.mid_price) {
        const price = orderbook.mid_price.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
        updateElementWithPulse('mid-price', `$${price}`);
    }
    
    if (orderbook.best_ask) {
        const askPrice = orderbook.best_ask.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
        updateElementWithPulse('best-ask', `$${askPrice}`);
    }
    
    if (orderbook.best_bid) {
        const bidPrice = orderbook.best_bid.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
        updateElementWithPulse('best-bid', `$${bidPrice}`);
    }
    
    if (orderbook.spread_bps) {
        updateElementWithPulse('spread', `${orderbook.spread_bps.toFixed(2)} bps`);
    }
}

// Update cost chart
function updateCostChart(data) {
    if (costChart) {
        costChart.data.datasets[0].data = [
            data.slippage.expected_bps,
            data.fees.effective_rate_bps,
            data.market_impact.total_bps,
            data.net_cost.expected_bps
        ];
        costChart.update();
    }
}

// Helper function to update an element with a pulse animation
function updateElementWithPulse(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = value;
        element.classList.remove('update-pulse');
        // Trigger reflow
        void element.offsetWidth;
        element.classList.add('update-pulse');
    }
}