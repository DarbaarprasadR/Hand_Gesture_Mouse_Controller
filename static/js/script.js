// DOM Elements
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const enableTrackingBtn = document.getElementById('enableTrackingBtn');
const disableTrackingBtn = document.getElementById('disableTrackingBtn');
const statusText = document.getElementById('statusText');
const coordinatesElement = document.getElementById('coordinates');
const debugInfo = document.getElementById('debugInfo');
const clickDistanceInput = document.getElementById('clickDistance');
const smoothingInput = document.getElementById('smoothing');

// Application state
let isRunning = false;
let isTracking = false;
let smoothingFactor = 0.5;

// Log debug information
function log(message) {
    const timestamp = new Date().toLocaleTimeString();
    debugInfo.innerHTML = `[${timestamp}] ${message}\n` + debugInfo.innerHTML;
    
    // Limit debug log length
    if (debugInfo.innerHTML.length > 5000) {
        debugInfo.innerHTML = debugInfo.innerHTML.substring(0, 5000);
    }
}

// API request helper
async function makeRequest(endpoint, method = 'POST', data = {}) {
    try {
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json'
            }
        };
        
        if (method !== 'GET') {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(endpoint, options);
        return await response.json();
    } catch (error) {
        log(`Error making request to ${endpoint}: ${error.message}`);
        return { status: 'error', message: error.message };
    }
}

// Start camera
async function startCamera() {
    if (isRunning) return;
    
    const result = await makeRequest('/api/start_camera');
    if (result.status === 'success') {
        isRunning = true;
        startBtn.disabled = true;
        stopBtn.disabled = false;
        enableTrackingBtn.disabled = false;
        statusText.textContent = 'Camera started. Hand tracking initialized.';
        log('Camera started successfully');
    } else {
        log(`Failed to start camera: ${result.message}`);
        statusText.textContent = `Error: ${result.message}`;
    }
}

// Stop camera
async function stopCamera() {
    if (!isRunning) return;
    
    const result = await makeRequest('/api/stop_camera');
    if (result.status === 'success') {
        isRunning = false;
        isTracking = false;
        startBtn.disabled = false;
        stopBtn.disabled = true;
        enableTrackingBtn.disabled = true;
        disableTrackingBtn.disabled = true;
        statusText.textContent = 'Camera stopped';
        log('Camera stopped');
    } else {
        log(`Failed to stop camera: ${result.message}`);
    }
}

// Enable hand tracking for mouse control
async function enableTracking() {
    if (!isRunning || isTracking) return;
    
    const result = await makeRequest('/api/enable_tracking');
    if (result.status === 'success') {
        isTracking = true;
        enableTrackingBtn.disabled = true;
        disableTrackingBtn.disabled = false;
        statusText.textContent = 'Mouse control enabled';
        log('Hand tracking enabled for mouse control');
    } else {
        log(`Failed to enable tracking: ${result.message}`);
    }
}

// Disable hand tracking for mouse control
async function disableTracking() {
    if (!isRunning || !isTracking) return;
    
    const result = await makeRequest('/api/disable_tracking');
    if (result.status === 'success') {
        isTracking = false;
        enableTrackingBtn.disabled = false;
        disableTrackingBtn.disabled = true;
        statusText.textContent = 'Mouse control disabled';
        log('Hand tracking disabled for mouse control');
    } else {
        log(`Failed to disable tracking: ${result.message}`);
    }
}

// Update click distance threshold
async function updateClickDistance() {
    const distance = parseInt(clickDistanceInput.value);
    if (isNaN(distance)) return;
    
    const result = await makeRequest('/api/set_click_distance', 'POST', { distance });
    if (result.status === 'success') {
        log(`Click distance threshold updated to ${distance}`);
    } else {
        log(`Failed to update click distance: ${result.message}`);
    }
}

// Update smoothing factor
function updateSmoothing() {
    smoothingFactor = parseFloat(smoothingInput.value);
    log(`Smoothing factor updated to ${smoothingFactor}`);
}

// Initialize the application
function init() {
    // Event listeners
    startBtn.addEventListener('click', startCamera);
    stopBtn.addEventListener('click', stopCamera);
    enableTrackingBtn.addEventListener('click', enableTracking);
    disableTrackingBtn.addEventListener('click', disableTracking);
    clickDistanceInput.addEventListener('change', updateClickDistance);
    smoothingInput.addEventListener('change', updateSmoothing);
    
    // Log initialization
    log('Application initialized');
}

// Initialize when the DOM is loaded
document.addEventListener('DOMContentLoaded', init);

// Handle window unload to stop the camera
window.addEventListener('beforeunload', async () => {
    if (isRunning) {
        await stopCamera();
    }
});