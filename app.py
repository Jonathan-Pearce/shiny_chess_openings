from shiny import App, ui, render, reactive
import chess
import chess.pgn
from typing import Dict, Any
import asyncio
import sys

# Conditional imports for Pyodide vs local development
try:
    import js  # Available in Shinylive/Pyodide
    IN_BROWSER = True
except ImportError:
    import httpx  # Use for local development
    IN_BROWSER = False

# Preset openings for quick selection
PRESETS = {
    "Queen's Gambit": "d4 d5 c4",
    "French Defense": "e4 e6",
    "Ruy Lopez": "e4 e5 Nf3 Nc6 Bb5",
}

# Custom CSS for styling - LiChess inspired
custom_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;500;700&display=swap');

* {
    font-family: 'Noto Sans', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

body {
    background-color: hsl(37, 10%, 8%) !important;
    color: hsl(0, 0%, 73%);
}

.card {
    background-color: hsl(37, 7%, 14%);
    border: none;
    box-shadow: 0 2px 5px rgba(0,0,0,0.3);
    border-radius: 4px;
}

.card-header {
    background-color: hsl(37, 7%, 19%);
    border-bottom: 1px solid hsl(0, 0%, 25%);
    padding: 12px 15px;
}

.eval-bar {
    height: 40px;
    background: linear-gradient(to right, #2c2c2c 0%, #2c2c2c 50%, #e8e8e8 50%, #e8e8e8 100%);
    border: 2px solid hsl(0, 0%, 25%);
    border-radius: 6px;
    position: relative;
    margin: 15px 0;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.3);
}

.eval-bar-label {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-weight: 700;
    font-size: 0.9em;
    z-index: 3;
    color: hsl(0, 0%, 100%);
    text-shadow: 0 1px 2px rgba(0,0,0,0.8);
}

.eval-indicator {
    position: absolute;
    height: 100%;
    background-color: #759900;
    transition: width 0.4s ease, left 0.4s ease;
    border-radius: 4px;
    box-shadow: 0 0 8px rgba(117, 153, 0, 0.5);
}

.metric-card {
    padding: 12px;
    margin: 8px 0;
    border-radius: 4px;
    background-color: hsl(37, 5%, 19%);
    border: 1px solid hsl(0, 0%, 25%);
}

.better {
    background-color: rgba(88, 153, 0, 0.2) !important;
    border-left: 3px solid hsl(88, 62%, 37%);
}

.worse {
    background-color: rgba(220, 50, 47, 0.2) !important;
    border-left: 3px solid hsl(0, 60%, 50%);
}

.board-container {
    max-width: 100%;
    margin: 10px auto;
    width: 75%;
}

@media (max-width: 768px) {
    .board-container {
        width: 100%;
    }
    
    .move-btn {
        width: calc(50% - 10px);
        margin: 5px;
    }
    
    .comparison-table {
        font-size: 0.85em;
    }
    
    .comparison-table th, .comparison-table td {
        padding: 8px;
    }
}

@media (max-width: 576px) {
    .selection-legend {
        flex-direction: column;
        gap: 10px;
    }
    
    .move-btn {
        width: 100%;
    }
    
    input[type="text"], select {
        font-size: 16px !important; /* Prevent zoom on iOS */
    }
}

.board-container > div {
    width: 100% !important;
}

.move-history {
    font-family: 'Noto Sans', monospace;
    padding: 12px;
    background-color: hsl(37, 5%, 19%);
    border-radius: 4px;
    max-height: 100px;
    overflow-y: auto;
    margin-top: 10px;
    border: 1px solid hsl(0, 0%, 25%);
    font-size: 0.95em;
    color: hsl(0, 0%, 80%);
}

.loading {
    text-align: center;
    padding: 20px;
    color: hsl(0, 0%, 58%);
}

.welcome-section {
    background-color: hsl(37, 7%, 14%);
    padding: 20px;
    border-radius: 4px;
    margin-bottom: 20px;
    border-left: 4px solid hsl(22, 100%, 42%);
    box-shadow: 0 2px 5px rgba(0,0,0,0.3);
}

.move-selector-panel {
    background-color: hsl(37, 7%, 14%);
    padding: 15px;
    border-radius: 4px;
    margin-bottom: 15px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.3);
}

.move-btn {
    margin: 5px;
    padding: 10px 16px;
    border: 2px solid hsl(0, 0%, 30%);
    border-radius: 4px;
    background-color: hsl(37, 5%, 19%);
    cursor: pointer;
    transition: all 0.15s ease;
    font-weight: 500;
    color: hsl(0, 0%, 80%);
    position: relative;
    overflow: hidden;
}

.move-btn-content {
    position: relative;
    z-index: 2;
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.move-btn-popularity {
    position: absolute;
    bottom: 0;
    left: 0;
    height: 4px;
    background: linear-gradient(90deg, hsl(209, 79%, 56%), hsl(88, 62%, 37%));
    opacity: 0.6;
    z-index: 1;
    transition: opacity 0.15s ease;
}

.move-btn:hover .move-btn-popularity {
    opacity: 0.8;
}

.move-stats {
    font-size: 0.75em;
    color: hsl(0, 0%, 65%);
    font-weight: 400;
}

.move-btn:hover:not(:disabled) {
    background-color: hsl(37, 7%, 22%);
    border-color: hsl(0, 0%, 40%);
    transform: translateY(-1px);
    box-shadow: 0 3px 8px rgba(0,0,0,0.4);
}

.move-btn.selected-a {
    background-color: hsl(209, 79%, 56%);
    border-color: hsl(209, 79%, 46%);
    color: white;
    font-weight: 700;
}

.move-btn.selected-b {
    background-color: hsl(88, 62%, 37%);
    border-color: hsl(88, 62%, 27%);
    color: white;
    font-weight: 700;
}

.move-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.selection-legend {
    display: flex;
    gap: 20px;
    margin-bottom: 12px;
    font-size: 0.9em;
    color: hsl(0, 0%, 80%);
}

.legend-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 500;
}

.legend-color {
    width: 24px;
    height: 24px;
    border-radius: 3px;
    border: 2px solid hsl(0, 0%, 50%);
}

.legend-color.color-a {
    background-color: hsl(209, 79%, 56%);
}

.legend-color.color-b {
    background-color: hsl(88, 62%, 37%);
}

.comparison-panel {
    background-color: hsl(37, 7%, 14%);
    padding: 15px;
    border-radius: 4px;
    margin-top: 15px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.3);
}

.comparison-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
}

.comparison-table th {
    padding: 12px;
    text-align: center;
    background-color: hsl(37, 5%, 19%);
    border: 1px solid hsl(0, 0%, 25%);
    font-weight: 700;
    color: hsl(0, 0%, 80%);
}

.comparison-table td {
    padding: 12px;
    text-align: center;
    border: 1px solid hsl(0, 0%, 25%);
    font-weight: 500;
    color: hsl(0, 0%, 73%);
}

.comparison-table .metric-name {
    text-align: left;
    font-weight: 600;
    background-color: hsl(37, 7%, 16%);
}

.comparison-table .winner {
    background-color: rgba(88, 153, 0, 0.2);
    font-weight: 700;
    color: hsl(88, 62%, 50%);
}

.comparison-table .loser {
    background-color: rgba(220, 50, 47, 0.2);
    font-weight: 700;
    color: hsl(0, 60%, 60%);
}

.comparison-table .tie {
    background-color: rgba(181, 137, 0, 0.2);
    font-weight: 600;
    color: hsl(37, 74%, 53%);
}

.delta-indicator {
    font-size: 0.85em;
    margin-left: 6px;
    font-weight: 600;
}

.delta-positive {
    color: hsl(88, 62%, 50%);
}

.delta-negative {
    color: hsl(0, 60%, 60%);
}

.metric-better {
    box-shadow: 0 0 0 2px hsl(88, 62%, 37%) inset;
}

.btn-primary {
    background-color: hsl(22, 100%, 42%) !important;
    border-color: hsl(22, 100%, 42%) !important;
    font-weight: 600;
    color: white;
}

.btn-primary:hover {
    background-color: hsl(22, 100%, 35%) !important;
    border-color: hsl(22, 100%, 35%) !important;
}

.btn-secondary {
    background-color: hsl(0, 0%, 25%) !important;
    border-color: hsl(0, 0%, 25%) !important;
    font-weight: 600;
    color: hsl(0, 0%, 80%);
}

.btn-secondary:hover {
    background-color: hsl(0, 0%, 30%) !important;
    border-color: hsl(0, 0%, 30%) !important;
}

.btn-info {
    background-color: hsl(209, 79%, 56%) !important;
    border-color: hsl(209, 79%, 46%) !important;
    font-weight: 600;
    color: white;
}

.btn-info:hover {
    background-color: hsl(209, 79%, 46%) !important;
    border-color: hsl(209, 79%, 36%) !important;
}

input[type="text"], select {
    border: 2px solid hsl(0, 0%, 30%) !important;
    border-radius: 4px !important;
    padding: 8px 12px !important;
    font-family: 'Noto Sans', sans-serif !important;
    background-color: hsl(37, 7%, 13%) !important;
    color: hsl(0, 0%, 80%) !important;
}

input[type="text"]:focus, select:focus {
    border-color: hsl(22, 100%, 42%) !important;
    outline: none !important;
    box-shadow: 0 0 0 2px rgba(216, 80, 0, 0.2) !important;
}

hr {
    border-top: 1px solid hsl(0, 0%, 25%);
}

h4, h5, h6 {
    color: hsl(0, 0%, 80%);
    font-weight: 700;
}

a {
    color: hsl(209, 79%, 56%);
    text-decoration: none;
}

a:hover {
    color: hsl(209, 79%, 66%);
    text-decoration: underline;
}

/* LiChess box patterns */
.box__pad {
    padding: 20px;
}

/* Better shadows and depth */
.card:hover {
    box-shadow: 0 4px 10px rgba(0,0,0,0.5);
    transition: box-shadow 0.15s ease;
}

/* LiChess-style headers */
h1, h2, h3 {
    font-weight: 700;
    margin-bottom: 0.5em;
    color: hsl(0, 0%, 89%);
}

/* Better spacing for lists */
ul {
    margin: 0.5em 0;
}

/* Smooth all transitions */
button, .move-btn, .card {
    transition: all 0.15s ease;
}

/* Focus states */
button:focus, .move-btn:focus {
    outline: 2px solid hsl(22, 100%, 42%);
    outline-offset: 2px;
}

/* Loading states */
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.loading {
    animation: pulse 1.5s ease-in-out infinite;
}

/* Better table styling */
table {
    border-collapse: collapse;
}

/* LiChess-style emphasis */
strong {
    font-weight: 700;
    color: hsl(0, 0%, 89%);
}

/* Small text styling */
small {
    font-size: 0.85em;
    color: hsl(0, 0%, 58%);
}

/* Position type badge */
.position-badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 0.8em;
    font-weight: 600;
    margin-left: 8px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.position-badge.opening {
    background-color: rgba(88, 153, 0, 0.3);
    color: hsl(88, 62%, 50%);
    border: 1px solid hsl(88, 62%, 37%);
}

.position-badge.middlegame {
    background-color: rgba(209, 154, 56, 0.3);
    color: hsl(37, 74%, 53%);
    border: 1px solid hsl(37, 74%, 43%);
}

.position-badge.endgame {
    background-color: rgba(209, 79, 156, 0.3);
    color: hsl(330, 79%, 56%);
    border: 1px solid hsl(330, 79%, 46%);
}

/* Skeleton loader */
.skeleton {
    background: linear-gradient(90deg, hsl(37, 5%, 19%) 25%, hsl(37, 7%, 22%) 50%, hsl(37, 5%, 19%) 75%);
    background-size: 200% 100%;
    animation: skeleton-loading 1.5s infinite;
    border-radius: 4px;
    height: 20px;
    margin: 8px 0;
}

@keyframes skeleton-loading {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

/* Focus visible for better accessibility */
*:focus-visible {
    outline: 2px solid hsl(22, 100%, 42%);
    outline-offset: 2px;
}
</style>
"""

# Chess board JavaScript integration
chessboard_js = r"""
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<link rel="stylesheet" href="https://unpkg.com/@chrisoakman/chessboardjs@1.0.0/dist/chessboard-1.0.0.min.css">
<script src="https://unpkg.com/@chrisoakman/chessboardjs@1.0.0/dist/chessboard-1.0.0.min.js"></script>
<script>
console.log('Chessboard scripts loaded');

// IMPORTANT: don't store the Chessboard instance on window.mainBoard.
// Browsers may auto-create window.mainBoard from the element id="mainBoard",
// which is a plain DOM element and does not have .position().
window.mainBoardWidget = null;
window.pendingMainBoardFen = null;

// Initialize Stockfish engine using inline worker to avoid CORS issues
let stockfishWorker = null;
let stockfishReady = false;
let evaluationQueue = {};
let evalId = 0;
let currentEvalId = null;

try {
    // Create Stockfish worker from inline code to avoid CORS issues
    const stockfishCode = `
        importScripts('https://unpkg.com/stockfish.js@10.0.2/stockfish.js');
    `;
    
    const blob = new Blob([stockfishCode], { type: 'application/javascript' });
    const workerUrl = URL.createObjectURL(blob);
    stockfishWorker = new Worker(workerUrl);
    console.log('✓ Stockfish worker created from blob');
    
    stockfishWorker.onmessage = function(event) {
        const line = event.data;
        console.log('Stockfish:', line);
        
        if (line === 'uciok') {
            stockfishReady = true;
            console.log('✓ Stockfish engine ready');
        }
        
        // Parse evaluation results - use best score from last info line before bestmove
        if (line.startsWith('info') && currentEvalId && (line.includes('score cp') || line.includes('score mate'))) {
            let cp = null;
            let mate = null;
            
            if (line.includes('score cp')) {
                const cpMatch = line.match(/score cp (-?\d+)/);
                if (cpMatch) cp = parseInt(cpMatch[1]);
            } else if (line.includes('score mate')) {
                const mateMatch = line.match(/score mate (-?\d+)/);
                if (mateMatch) mate = parseInt(mateMatch[1]);
            }
            
            // Store latest evaluation
            if (cp !== null || mate !== null) {
                if (evaluationQueue[currentEvalId]) {
                    evaluationQueue[currentEvalId].lastResult = {cp, mate};
                }
            }
        }
        
        // When bestmove is received, resolve with the last evaluation
        if (line.startsWith('bestmove') && currentEvalId) {
            if (evaluationQueue[currentEvalId] && evaluationQueue[currentEvalId].lastResult) {
                const result = evaluationQueue[currentEvalId].lastResult;
                console.log('Sending final result to Shiny:', result, 'for ID:', currentEvalId);
                if (typeof Shiny !== 'undefined') {
                    Shiny.setInputValue('stockfish_result_' + currentEvalId, JSON.stringify(result), {priority: 'event'});
                }
                evaluationQueue[currentEvalId].resolve(result);
                delete evaluationQueue[currentEvalId];
            }
            currentEvalId = null;
        }
    };
    
    // Initialize engine
    stockfishWorker.postMessage('uci');
    
} catch (e) {
    console.error('✗ Failed to initialize Stockfish:', e);
}

// Evaluate position with Stockfish
window.evaluateWithStockfish = function(fen, depth = 9) {
    return new Promise((resolve, reject) => {
        if (!stockfishWorker || !stockfishReady) {
            reject(new Error('Stockfish not ready'));
            return;
        }
        
        const id = (++evalId).toString();
        evaluationQueue[id] = {resolve, reject, lastResult: null};
        currentEvalId = id;
        
        // Set a timeout - 30 seconds to allow for depth 18 analysis
        setTimeout(() => {
            if (evaluationQueue[id]) {
                delete evaluationQueue[id];
                if (currentEvalId === id) currentEvalId = null;
                reject(new Error('Evaluation timeout'));
            }
        }, 30000); // 30 second timeout
        
        stockfishWorker.postMessage('position fen ' + fen);
        stockfishWorker.postMessage('go depth ' + depth);
    });
};

// Initialize main board after page load
window.addEventListener('load', function() {
    console.log('Window loaded, checking for Chessboard...');
    console.log('Chessboard available:', typeof Chessboard !== 'undefined');
    console.log('jQuery available:', typeof $ !== 'undefined');
    console.log('mainBoard element:', document.getElementById('mainBoard'));
    
    // Wait a bit for Shiny to be ready
    setTimeout(function() {
        console.log('Attempting to initialize main board...');
        
        try {
            if (document.getElementById('mainBoard')) {
                window.mainBoardWidget = Chessboard('mainBoard', {
                    position: 'start',
                    draggable: true,
                    pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png',
                    onDrop: function(source, target) {
                        console.log('Move attempted:', source, target);
                        if (typeof Shiny !== 'undefined') {
                            Shiny.setInputValue('board_move', source + target, {priority: 'event'});
                        }
                        return 'snapback';
                    }
                });
                console.log('✓ Main board initialized successfully');

                // Apply any queued update that arrived before init.
                if (window.pendingMainBoardFen) {
                    try {
                        window.mainBoardWidget.position(window.pendingMainBoardFen);
                        console.log('✓ Applied queued board update');
                    } catch (e) {
                        console.error('✗ Failed applying queued board update:', e);
                    }
                    window.pendingMainBoardFen = null;
                }
            } else {
                console.error('✗ mainBoard element not found');
            }
        } catch(e) {
            console.error('✗ Error initializing mainBoard:', e);
        }
    }, 1000);
});

// Handle custom messages from server to update board position
// Register handlers when Shiny becomes available
function registerShinyHandlers() {
    if (typeof Shiny !== 'undefined' && Shiny.addCustomMessageHandler) {
        console.log('✓ Shiny is available! Registering message handlers...');
        
        Shiny.addCustomMessageHandler('update_board', function(message) {
            console.log('Update board message received:', message);
            if (window.mainBoardWidget && typeof window.mainBoardWidget.position === 'function') {
                try {
                    window.mainBoardWidget.position(message.fen);
                    console.log('Board position updated');
                } catch(e) {
                    console.error('Error updating board:', e);
                }
            } else {
                // Board not ready yet; queue the latest fen and apply after init.
                window.pendingMainBoardFen = message.fen;
            }
        });
        
        // Handle Stockfish evaluation requests
        Shiny.addCustomMessageHandler('evaluate_stockfish', function(message) {
            console.log('📥 Stockfish evaluation request received:', message);
            console.log('   FEN:', message.fen);
            console.log('   Depth:', message.depth);
            console.log('   Request ID:', message.request_id);
            
            window.evaluateWithStockfish(message.fen, message.depth || 9)
                .then(result => {
                    console.log('✓ Stockfish evaluation complete:', result);
                    console.log('📤 Sending to Shiny as stockfish_response');
                    const response = {
                        request_id: message.request_id,
                        cp: result.cp,
                        mate: result.mate
                    };
                    Shiny.setInputValue('stockfish_response', JSON.stringify(response), {priority: 'event'});
                    console.log('✓ Result sent to Shiny');
                })
                .catch(error => {
                    console.error('✗ Stockfish evaluation failed:', error);
                    console.log('📤 Sending error to Shiny as stockfish_response');
                    const response = {
                        request_id: message.request_id,
                        error: error.message
                    };
                    Shiny.setInputValue('stockfish_response', JSON.stringify(response), {priority: 'event'});
                    console.log('✓ Error sent to Shiny');
                });
        });
        
        console.log('✓ Message handlers registered: update_board, evaluate_stockfish');
        return true;
    }
    return false;
}

// Try to register immediately
if (!registerShinyHandlers()) {
    // If Shiny not ready, try multiple approaches
    console.log('Shiny not ready yet, waiting...');
    
    // Try on shiny:connected event
    $(document).on('shiny:connected', function() {
        console.log('shiny:connected event fired');
        registerShinyHandlers();
    });
    
    // Also try polling for a bit
    let attempts = 0;
    const checkInterval = setInterval(function() {
        attempts++;
        if (registerShinyHandlers() || attempts > 20) {
            clearInterval(checkInterval);
            if (attempts > 20) {
                console.error('✗ Failed to register Shiny handlers after 20 attempts');
            }
        }
    }, 500);
}
</script>
"""

app_ui = ui.page_fluid(
    ui.HTML(custom_css),
    ui.HTML(chessboard_js),
    
    # Info button in top right
    ui.div(
        ui.input_action_button(
            "show_info", 
            "ℹ️ How to Use", 
            class_="btn-info",
            style="position: fixed; top: 10px; right: 10px; z-index: 1000; border-radius: 20px; padding: 8px 16px;"
        ),
    ),
    
    # Two-column layout (Bootstrap grid; avoid bslib JS)
    ui.row(
        # Column 1: Current Position
        ui.column(
            4,
            ui.tags.div(
                {"class": "card"},
                ui.tags.div(
                    {"class": "card-header"},
                    ui.h4("Current Position", style="margin: 0; font-size: 1.1rem;"),
                ),
                ui.tags.div(
                    {"class": "card-body"},
                    # Chess board
                    ui.div(
                        {"class": "board-container"},
                        ui.HTML('<div id="mainBoard" style="width: 100%; max-width: 100%; height: auto;"></div>'),
                    ),
                    # Move input below board
                    ui.input_text(
                        "moves",
                        "Moves:",
                        placeholder="e.g., e4 e5 Nf3 Nc6",
                        width="100%",
                    ),
                    # Action buttons
                    ui.div(
                        ui.input_action_button(
                            "analyze_position",
                            "Analyze",
                            class_="btn-primary",
                            style="width: 48%; margin-right: 2%;",
                        ),
                        ui.input_action_button(
                            "reset_board",
                            "Reset",
                            class_="btn-secondary",
                            style="width: 48%;",
                        ),
                        style="margin-top: 10px; margin-bottom: 10px;",
                    ),
                    # Evaluation preference toggle
                    ui.div(
                        ui.input_radio_buttons(
                            "eval_mode",
                            "Evaluation:",
                            choices={
                                "local": "🖥️ Local (Stockfish.js)",
                                "cloud": "☁️ Cloud (Lichess API)",
                                "auto": "🔄 Auto (Local → Cloud)",
                            },
                            selected="auto",
                            inline=True,
                        ),
                        style="margin-bottom: 15px; font-size: 0.85em;",
                    ),
                    # Position summary
                    ui.output_ui("position_summary"),
                ),
            ),
        ),
        
        # Column 2: Candidate Move Comparison
        ui.column(
            8,
            ui.div(
                # Combined selection panel
                ui.output_ui("move_selector_panel"),
                
                # Two comparison columns
                ui.row(
                    ui.column(
                        6,
                        ui.tags.div(
                            {"class": "card"},
                            ui.tags.div(
                                {"class": "card-header"},
                                ui.h4(
                                    "Candidate Move A",
                                    style="margin: 0; font-size: 1.1rem; color: hsl(209, 79%, 56%);",
                                ),
                            ),
                            ui.tags.div(
                                {"class": "card-body"},
                                ui.output_ui("move_a_details"),
                            ),
                        ),
                    ),
                    ui.column(
                        6,
                        ui.tags.div(
                            {"class": "card"},
                            ui.tags.div(
                                {"class": "card-header"},
                                ui.h4(
                                    "Candidate Move B",
                                    style="margin: 0; font-size: 1.1rem; color: hsl(88, 62%, 37%);",
                                ),
                            ),
                            ui.tags.div(
                                {"class": "card-body"},
                                ui.output_ui("move_b_details"),
                            ),
                        ),
                    ),
                ),
                
                # Shared comparison panel
                ui.output_ui("comparison_panel"),
            ),
        ),
    ),
)


def server(input, output, session):
    # Reactive values for main board state
    main_board = reactive.Value(chess.Board())
    
    # Reactive values for current position data
    position_stats = reactive.Value({})
    position_eval = reactive.Value({})
    
    # Selected candidate moves (stored as SAN strings)
    selected_move_a = reactive.Value(None)
    selected_move_b = reactive.Value(None)
    
    # Data for selected moves (fetched lazily)
    move_a_stats = reactive.Value({})
    move_a_eval = reactive.Value({})
    move_b_stats = reactive.Value({})
    move_b_eval = reactive.Value({})
    
    # Track if board is initialized
    board_initialized = reactive.Value(False)
    
    @reactive.Effect
    async def _init_board():
        if not board_initialized():
            await session.send_custom_message(
                "update_board",
                {"fen": main_board().fen()}
            )
            board_initialized.set(True)
    
    # Show info modal when button is clicked
    @reactive.Effect
    @reactive.event(input.show_info)
    def _show_info():
        m = ui.modal(
            ui.h3("♟️ Chess Position Analyzer", style="color: #d85000; font-weight: 700;"),
            ui.p(
                "Analyze chess positions with interactive board. Set up a position using presets or by entering moves, "
                "then select two candidate moves to compare their evaluations and statistics."
            ),
            ui.hr(),
            ui.h5("How to use:"),
            ui.tags.ol(
                ui.tags.li("Build a position using the board or move input (or select a preset opening)"),
                ui.tags.li("Click 'Analyze Position' to fetch statistics and evaluations"),
                ui.tags.li("Select two candidate next moves from the dropdowns below"),
                ui.tags.li("Compare evaluations, win rates, and statistics for each move")
            ),
            ui.hr(),
            ui.p(
                ui.strong("Data Sources: "),
                "Statistics from Lichess database, evaluations from Lichess Cloud (Stockfish)"
            ),
            title="About Chess Position Analyzer",
            easy_close=True,
            footer=ui.modal_button("Close")
        )
        ui.modal_show(m)
    
    # Reset board handler
    @reactive.Effect
    @reactive.event(input.reset_board)
    async def _reset_board():
        main_board.set(chess.Board())
        await session.send_custom_message(
            "update_board",
            {"fen": chess.Board().fen()}
        )
        ui.update_text("moves", value="")
        position_stats.set({})
        position_eval.set({})
        selected_move_a.set(None)
        selected_move_b.set(None)
        move_a_stats.set({})
        move_a_eval.set({})
        move_b_stats.set({})
        move_b_eval.set({})
    
    # Reactive values for Stockfish results (responses come back via input.stockfish_response)
    stockfish_pending: Dict[int, asyncio.Event] = {}
    stockfish_results: Dict[int, dict] = {}
    stockfish_request_id = reactive.Value(0)

    # Generation counters to prevent stale async results overwriting newer ones
    eval_generation = {
        "position": 0,
        "move_a": 0,
        "move_b": 0,
    }
    
    # Watch for stockfish results from JavaScript using a single input
    @reactive.Effect
    @reactive.event(input.stockfish_response, ignore_none=False)
    def _on_stockfish_response():
        try:
            response = input.stockfish_response()
            if response is None or response == "":
                return
                
            import json
            if isinstance(response, str):
                data = json.loads(response)
            else:
                data = response

            if not isinstance(data, dict):
                return

            req_id = data.get('request_id')
            try:
                req_id = int(req_id) if req_id is not None else None
            except Exception:
                req_id = None
            
            if req_id and req_id in stockfish_pending:
                if 'error' in data:
                    stockfish_results[req_id] = {"error": data['error']}
                    print(f"✗ Received Stockfish error for request {req_id}: {data['error']}")
                else:
                    stockfish_results[req_id] = {
                        'cp': data.get('cp'),
                        'mate': data.get('mate')
                    }
                    print(f"✓ Received Stockfish result for request {req_id}: cp={data.get('cp')}, mate={data.get('mate')}")
                
                stockfish_pending[req_id].set()
        except Exception as e:
            print(f"Error processing stockfish response: {e}")
    
    # Listen for board drag moves and apply if legal
    @reactive.Effect
    @reactive.event(input.board_move)
    async def _on_board_move():
        move_str = input.board_move()
        if not move_str:
            return
        try:
            mv = chess.Move.from_uci(move_str)
            b = main_board().copy()
            if mv in b.legal_moves:
                b.push(mv)
                main_board.set(b)
                # Update the visual board
                await session.send_custom_message(
                    "update_board",
                    {"fen": b.fen()}
                )
                # Update text input with move history
                moves = []
                temp = chess.Board()
                for move in b.move_stack:
                    moves.append(temp.san(move))
                    temp.push(move)
                ui.update_text("moves", value=" ".join(moves))
        except Exception:
            pass
    
    def parse_moves(move_string: str) -> chess.Board:
        """Parse algebraic notation moves and return board state."""
        board = chess.Board()
        if not move_string.strip():
            return board
        
        try:
            moves = move_string.strip().split()
            for move_san in moves:
                move = board.parse_san(move_san)
                board.push(move)
            return board
        except (chess.InvalidMoveError, chess.IllegalMoveError, chess.AmbiguousMoveError) as e:
            raise ValueError(f"Invalid move sequence: {e}")
    
    # Analyze position
    @reactive.Effect
    @reactive.event(input.analyze_position)
    async def _analyze_position():
        try:
            new_board = parse_moves(input.moves())
            main_board.set(new_board)
            
            # Update board position
            await session.send_custom_message(
                "update_board",
                {"fen": new_board.fen()}
            )
            
            # Fetch stats for current position
            fen = new_board.fen()
            stats = await fetch_lichess_stats(fen)
            position_stats.set(stats)

            # Start evaluation in background to avoid deadlocks on input callbacks
            start_evaluation_for_target(fen, position_eval, target_key="position")
            
            # Clear previous move selections
            selected_move_a.set(None)
            selected_move_b.set(None)
            move_a_stats.set({})
            move_a_eval.set({})
            move_b_stats.set({})
            move_b_eval.set({})
            
        except ValueError as e:
            position_stats.set({"error": str(e)})
            position_eval.set({})
    
    async def fetch_lichess_stats(fen: str) -> Dict[str, Any]:
        """Fetch opening statistics from Lichess Explorer API."""
        try:
            base_url = "https://explorer.lichess.ovh/lichess"
            params = {
                "fen": fen,
                "speeds": "blitz,rapid,classical",
                "ratings": "1600,1800,2000,2200,2500",
            }
            
            if IN_BROWSER:
                # Use js.fetch in Shinylive/Pyodide
                query_parts = []
                for key, value in params.items():
                    encoded_value = js.encodeURIComponent(value)
                    query_parts.append(f"{key}={encoded_value}")
                query = "&".join(query_parts)
                
                url = f"{base_url}?{query}"
                response = await js.fetch(url)
                
                if not response.ok:
                    return {"error": f"HTTP {response.status}"}
                
                data = await response.json()
                return data.to_py()
            else:
                # Use httpx for local development
                async with httpx.AsyncClient() as client:
                    response = await client.get(base_url, params=params, timeout=10.0)
                    response.raise_for_status()
                    return response.json()
            
        except Exception as e:
            return {"error": str(e)}
    
    async def fetch_cloud_eval(fen: str) -> Dict[str, Any]:
        """Fetch position evaluation from Lichess Cloud Eval API."""
        try:
            base_url = "https://lichess.org/api/cloud-eval"
            
            if IN_BROWSER:
                # Use js.fetch in Shinylive/Pyodide
                encoded_fen = js.encodeURIComponent(fen)
                url = f"{base_url}?fen={encoded_fen}&multiPv=1"
                
                response = await js.fetch(url)
                
                if not response.ok:
                    return {"error": f"HTTP {response.status}"}
                
                data = await response.json()
                return data.to_py()
            else:
                # Use httpx for local development
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        base_url,
                        params={"fen": fen, "multiPv": "1"},
                        timeout=10.0
                    )
                    response.raise_for_status()
                    return response.json()
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _request_stockfish_eval(fen: str, depth: int = 9) -> int:
        """Send a Stockfish evaluation request to the browser and return the request id."""
        request_id = stockfish_request_id() + 1
        stockfish_request_id.set(request_id)

        print(f"📤 Sending Stockfish request {request_id} for position: {fen[:50]}...")

        event = asyncio.Event()
        stockfish_pending[request_id] = event

        await session.send_custom_message(
            "evaluate_stockfish",
            {"fen": fen, "depth": depth, "request_id": request_id},
        )
        return request_id

    async def _await_stockfish_eval(request_id: int, depth: int = 9, timeout_s: float = 30.0) -> Dict[str, Any]:
        """Wait for a Stockfish response and convert to Lichess cloud-eval-like format."""
        try:
            event = stockfish_pending.get(request_id)
            if not event:
                return {"error": "Stockfish request missing"}

            print("✓ Message sent, waiting for result...")

            await asyncio.wait_for(event.wait(), timeout=timeout_s)
            result = stockfish_results.pop(request_id, None)
            stockfish_pending.pop(request_id, None)

            if not result:
                return {"error": "Stockfish returned no result"}
            if "error" in result:
                return {"error": f"Stockfish: {result['error']}"}

            print(f"✓ Stockfish result: {result}")

            if result.get("cp") is not None:
                return {
                    "pvs": [{"cp": result["cp"]}],
                    "depth": depth,
                    "source": "stockfish.js",
                }
            if result.get("mate") is not None:
                mate_in = result["mate"]
                cp = 10000 if mate_in > 0 else -10000
                return {
                    "pvs": [{"cp": cp, "mate": mate_in}],
                    "depth": depth,
                    "source": "stockfish.js",
                }

            return {"error": "Stockfish result missing cp/mate"}

        except asyncio.TimeoutError:
            stockfish_pending.pop(request_id, None)
            stockfish_results.pop(request_id, None)
            return {"error": "Stockfish evaluation timeout"}
        except Exception as e:
            stockfish_pending.pop(request_id, None)
            stockfish_results.pop(request_id, None)
            return {"error": f"Stockfish wait error: {str(e)}"}

    async def _compute_evaluation(fen: str, depth: int = 9, mode: str = "auto") -> Dict[str, Any]:
        """Compute evaluation based on mode; safe to run in a background task."""
        if mode == "cloud":
            return await fetch_cloud_eval(fen)

        if mode == "local":
            req_id = await _request_stockfish_eval(fen, depth=depth)
            return await _await_stockfish_eval(req_id, depth=depth)

        # auto
        print("Attempting Stockfish evaluation for position...")
        req_id = await _request_stockfish_eval(fen, depth=depth)
        result = await _await_stockfish_eval(req_id, depth=depth)
        if "error" not in result:
            print("Stockfish evaluation successful")
            return result
        print(f"Stockfish failed ({result.get('error')}), falling back to cloud API")
        cloud = await fetch_cloud_eval(fen)
        if "error" not in cloud:
            cloud["source"] = "cloud"
        return cloud

    def start_evaluation_for_target(fen: str, target_value: reactive.Value, target_key: str, depth: int = 9) -> None:
        """Kick off evaluation in the background and update target_value when done."""
        eval_generation[target_key] += 1
        generation = eval_generation[target_key]
        mode = input.eval_mode() if hasattr(input, "eval_mode") else "auto"

        # Mark as pending immediately for the UI
        target_value.set({"pending": True, "mode": mode})

        async def _runner() -> None:
            result = await _compute_evaluation(fen, depth=depth, mode=mode)
            # Only apply if still the latest request for this target
            if eval_generation.get(target_key) == generation:
                target_value.set(result)

        asyncio.create_task(_runner())
    
    @output
    @render.ui
    def position_summary():
        board = main_board()
        stats = position_stats()
        evaluation = position_eval()
        
        # Build move history
        moves = []
        temp_board = chess.Board()
        for i, move in enumerate(board.move_stack):
            move_num = (i // 2) + 1
            if i % 2 == 0:
                moves.append(f"{move_num}. {temp_board.san(move)}")
            else:
                moves.append(temp_board.san(move))
            temp_board.push(move)
        
        move_history = " ".join(moves) if moves else "Starting position"
        
        # Determine position type based on move count and material
        move_count = len(board.move_stack)
        piece_count = len(board.piece_map())
        position_type = "opening"
        position_badge_class = "opening"
        
        if move_count > 40 or piece_count <= 10:
            position_type = "endgame"
            position_badge_class = "endgame"
        elif move_count > 15 or piece_count <= 20:
            position_type = "middlegame"
            position_badge_class = "middlegame"
        
        # Determine side to move
        side_to_move = "White to move" if board.turn == chess.WHITE else "Black to move"
        
        # Evaluation
        eval_text = "Not analyzed"
        eval_source = ""
        cp_value = None
        eval_bar_html = ""
        
        if evaluation and evaluation.get("pending"):
            eval_text = "⏳ Evaluating…"
            mode = evaluation.get("mode")
            if mode == "cloud":
                eval_source = " <span style='color: hsl(209, 79%, 56%); font-size: 0.8em;'>(Cloud)</span>"
            elif mode == "local":
                eval_source = " <span style='color: hsl(88, 62%, 50%); font-size: 0.8em;'>(Local)</span>"
            else:
                eval_source = " <span style='color: hsl(0, 0%, 58%); font-size: 0.8em;'>(Auto)</span>"
            eval_bar_html = '<div class="skeleton" style="height: 40px; margin: 15px 0;"></div>'
        elif evaluation and 'pvs' in evaluation and len(evaluation['pvs']) > 0:
            cp = evaluation['pvs'][0].get('cp')
            if cp is not None:
                cp_value = cp
                eval_text = f"+{cp/100:.2f}" if cp >= 0 else f"{cp/100:.2f}"
                if evaluation.get('source') == 'stockfish.js':
                    eval_source = " <span style='color: hsl(88, 62%, 50%); font-size: 0.8em;'>(Local)</span>"
                else:
                    eval_source = " <span style='color: hsl(209, 79%, 56%); font-size: 0.8em;'>(Cloud)</span>"
                
                # Create visual evaluation bar
                # Normalize cp to 0-100 scale (clamp at ±5.00)
                normalized = max(-500, min(500, cp)) / 10  # -50 to +50
                white_percentage = 50 + normalized  # 0 to 100
                
                eval_bar_html = f'''
                    <div class="eval-bar" role="progressbar" aria-valuenow="{white_percentage}" aria-valuemin="0" aria-valuemax="100" aria-label="Position evaluation bar">
                        <div class="eval-bar-label">{eval_text}</div>
                        <div class="eval-indicator" style="width: {white_percentage}%; left: 0;"></div>
                    </div>
                '''
        elif evaluation and 'error' in evaluation:
            eval_text = f"Error: {evaluation['error']}"
        
        # Stats
        total_games = 0
        white_pct = 0
        draw_pct = 0
        black_pct = 0
        stats_html = "<p>No statistics available</p>"
        
        if stats and 'error' not in stats:
            total_games = stats.get("white", 0) + stats.get("draws", 0) + stats.get("black", 0)
            if total_games > 0:
                white_pct = round(stats.get("white", 0) / total_games * 100, 1)
                draw_pct = round(stats.get("draws", 0) / total_games * 100, 1)
                black_pct = round(stats.get("black", 0) / total_games * 100, 1)
                stats_html = f"""
                    <p><strong>Total Lichess Games:</strong> <span style="color: hsl(0, 0%, 100%); font-weight: 700;">{total_games:,}</span></p>
                    <p><strong>Results:</strong></p>
                    <ul style="margin: 5px 0; padding-left: 20px; color: hsl(0, 0%, 100%);">
                        <li>White wins: <span style="font-weight: 700;">{white_pct}%</span></li>
                        <li>Draws: <span style="font-weight: 700;">{draw_pct}%</span></li>
                        <li>Black wins: <span style="font-weight: 700;">{black_pct}%</span></li>
                    </ul>
                """
        elif stats and 'error' in stats:
            stats_html = f"<p style='color: hsl(0, 60%, 60%);'>Stats error: {stats['error']}</p>"
        
        return ui.HTML(f"""
            <div class="metric-card" style="height: 100%;" role="region" aria-label="Position summary">
                <h4 style="color: hsl(0, 0%, 89%); font-weight: 700; margin-bottom: 10px;">
                    📊 Position Summary
                    <span class="position-badge {position_badge_class}">{position_type}</span>
                </h4>
                <div class="move-history" style="margin-bottom: 15px; color: hsl(0, 0%, 89%);">
                    <strong>Moves:</strong> <span style="color: hsl(0, 0%, 100%);">{move_history}</span>
                </div>
                <p><strong>{side_to_move}</strong></p>
                <p><strong>Evaluation:</strong> <span style="color: hsl(0, 0%, 100%); font-weight: 700;">{eval_text}</span>{eval_source}</p>
                {eval_bar_html}
                <hr>
                {stats_html}
            </div>
        """)
    
    @output
    @render.ui
    def move_selector_panel():
        board = main_board()
        position_st = position_stats()
        
        # Only show selector if position has been analyzed
        if not position_st:
            return ui.tags.div(
                {"class": "card"},
                ui.tags.div(
                    {"class": "card-header"},
                    ui.h4("📋 Select Candidate Moves", style="margin: 0;"),
                ),
                ui.tags.div(
                    {"class": "card-body"},
                    ui.div(
                        {"class": "loading"},
                        "Analyze position first to see available moves",
                    ),
                ),
            )
        
        if board.is_game_over():
            return ui.tags.div(
                {"class": "card"},
                ui.tags.div(
                    {"class": "card-header"},
                    ui.h4("📋 Select Candidate Moves", style="margin: 0;"),
                ),
                ui.tags.div(
                    {"class": "card-body"},
                    ui.div("Game over - no legal moves"),
                ),
            )
        
        # Get legal moves sorted by popularity from stats
        legal_moves_san = [board.san(move) for move in board.legal_moves]
        
        # Get top moves from position stats if available
        top_moves = []
        other_moves = []
        if position_st and 'moves' in position_st:
            # Sort moves by total games
            api_moves = position_st['moves']
            sorted_api_moves = sorted(
                api_moves,
                key=lambda m: m.get('white', 0) + m.get('draws', 0) + m.get('black', 0),
                reverse=True
            )[:5]  # Top 5 moves
            
            top_moves_san = [m['san'] for m in sorted_api_moves if m['san'] in legal_moves_san]
            top_moves = top_moves_san[:5]
            other_moves = [m for m in legal_moves_san if m not in top_moves]
        else:
            # If no stats, just show first few moves
            top_moves = legal_moves_san[:5]
            other_moves = legal_moves_san[5:]
        
        # Current selections
        move_a = selected_move_a()
        move_b = selected_move_b()
        
        # Create buttons for top moves with popularity indicators
        move_buttons = []
        max_games = 0
        move_game_counts = {}
        
        # Calculate max games for normalization
        if position_st and 'moves' in position_st:
            for m in position_st['moves']:
                if m['san'] in top_moves:
                    games = m.get('white', 0) + m.get('draws', 0) + m.get('black', 0)
                    move_game_counts[m['san']] = games
                    max_games = max(max_games, games)
        
        for move_san in top_moves:
            # Determine button class
            btn_class = "move-btn"
            if move_san == move_a:
                btn_class += " selected-a"
            elif move_san == move_b:
                btn_class += " selected-b"
            
            # Get statistics for this move
            games_count = move_game_counts.get(move_san, 0)
            popularity_pct = (games_count / max_games * 100) if max_games > 0 else 0
            
            # Format win rate if available
            win_rate_text = ""
            if position_st and 'moves' in position_st:
                for m in position_st['moves']:
                    if m['san'] == move_san:
                        total = m.get('white', 0) + m.get('draws', 0) + m.get('black', 0)
                        if total > 0:
                            white_pct = round(m.get('white', 0) / total * 100, 1)
                            win_rate_text = f"<span class='move-stats'>W: {white_pct}% · {games_count:,} games</span>"
                        break
            
            btn_label = f'<div class="move-btn-content"><span>{move_san}</span>{win_rate_text}</div><div class="move-btn-popularity" style="width: {popularity_pct}%;"></div>'
            
            move_buttons.append(
                ui.HTML(f'''
                    <button 
                        class="{btn_class}" 
                        onclick="Shiny.setInputValue('move_clicked', '{move_san}', {{priority: 'event'}})"
                        aria-label="Select move {move_san}, played in {games_count} games"
                        title="{move_san} - {games_count:,} games">
                        {btn_label}
                    </button>
                ''')
            )
        
        # Create dropdown for other moves
        dropdown_choices = {"---": "(Select other move)"}
        for move_san in other_moves:
            dropdown_choices[move_san] = move_san
        
        return ui.tags.div(
            {"class": "card"},
            ui.tags.div(
                {"class": "card-header"},
                ui.h4("📋 Select Candidate Moves", style="margin: 0; font-weight: 700;"),
            ),
            ui.tags.div(
                {"class": "card-body"},
                ui.div(
                    {"class": "move-selector-panel"},
                    # Legend
                    ui.div(
                        {"class": "selection-legend"},
                        ui.div(
                            {"class": "legend-item"},
                            ui.div({"class": "legend-color color-a"}),
                            ui.span(f"Move A: {move_a if move_a else '(not selected)'}"),
                        ),
                        ui.div(
                            {"class": "legend-item"},
                            ui.div({"class": "legend-color color-b"}),
                            ui.span(f"Move B: {move_b if move_b else '(not selected)'}"),
                        ),
                    ),
                    ui.hr(style="margin: 10px 0;"),
                    # Top move buttons
                    ui.div(
                        ui.p(ui.strong("Popular moves (click to select):"), style="margin-bottom: 10px;"),
                        ui.div(*move_buttons, style="display: flex; flex-wrap: wrap;"),
                    ),
                    # Dropdown for other moves
                    ui.div(
                        ui.input_select(
                            "move_dropdown",
                            "Other moves:",
                            choices=dropdown_choices,
                            width="300px",
                        )
                        if other_moves
                        else ui.div(),
                        style="margin-top: 15px;",
                    ),
                ),
            ),
        )
    
    # Handle move button clicks
    @reactive.Effect
    @reactive.event(input.move_clicked)
    def _on_move_clicked():
        move_san = input.move_clicked()
        if not move_san or move_san == "---":
            return
        
        move_a = selected_move_a()
        move_b = selected_move_b()
        
        # If clicking already selected move, deselect it
        if move_san == move_a:
            selected_move_a.set(None)
            return
        elif move_san == move_b:
            selected_move_b.set(None)
            return
        
        # If move A is empty, assign to A
        if move_a is None:
            selected_move_a.set(move_san)
        # If move B is empty, assign to B
        elif move_b is None:
            selected_move_b.set(move_san)
        # If both are filled, replace A
        else:
            selected_move_a.set(move_san)
    
    # Handle dropdown selection
    @reactive.Effect
    @reactive.event(input.move_dropdown)
    def _on_dropdown_selected():
        move_san = input.move_dropdown()
        if not move_san or move_san == "---":
            return
        
        move_a = selected_move_a()
        move_b = selected_move_b()
        
        # If clicking already selected move, deselect it
        if move_san == move_a:
            selected_move_a.set(None)
            return
        elif move_san == move_b:
            selected_move_b.set(None)
            return
        
        # If move A is empty, assign to A
        if move_a is None:
            selected_move_a.set(move_san)
        # If move B is empty, assign to B
        elif move_b is None:
            selected_move_b.set(move_san)
        # If both are filled, replace A
        else:
            selected_move_a.set(move_san)
        
        # Reset dropdown
        ui.update_select("move_dropdown", selected="---")
    
    # When move A is selected, fetch its data lazily
    @reactive.Effect
    @reactive.event(selected_move_a)
    async def _on_move_a_selected():
        move_san = selected_move_a()
        if not move_san:
            move_a_stats.set({})
            move_a_eval.set({})
            return
        
        board = main_board()
        
        # Find the move and get resulting position
        try:
            move = board.parse_san(move_san)
            test_board = board.copy()
            test_board.push(move)
            fen = test_board.fen()
            
            # Fetch stats, start evaluation in background
            move_a_stats.set({})
            start_evaluation_for_target(fen, move_a_eval, target_key="move_a")
            stats = await fetch_lichess_stats(fen)
            move_a_stats.set(stats)
        except Exception as e:
            move_a_eval.set({"error": str(e)})
            move_a_stats.set({"error": str(e)})
    
    # When move B is selected, fetch its data lazily
    @reactive.Effect
    @reactive.event(selected_move_b)
    async def _on_move_b_selected():
        move_san = selected_move_b()
        if not move_san:
            move_b_stats.set({})
            move_b_eval.set({})
            return
        
        board = main_board()
        
        # Find the move and get resulting position
        try:
            move = board.parse_san(move_san)
            test_board = board.copy()
            test_board.push(move)
            fen = test_board.fen()
            
            # Fetch stats, start evaluation in background
            move_b_stats.set({})
            start_evaluation_for_target(fen, move_b_eval, target_key="move_b")
            stats = await fetch_lichess_stats(fen)
            move_b_stats.set(stats)
        except Exception as e:
            move_b_eval.set({"error": str(e)})
            move_b_stats.set({"error": str(e)})
    
    @output
    @render.ui
    def move_a_details():
        stats = move_a_stats()
        evaluation = move_a_eval()
        move_san = selected_move_a()
        
        if not move_san:
            return ui.div(
                {"class": "loading"},
                ui.p("Click a move from the selection panel above", style="text-align: center; padding: 20px; color: #6c757d;")
            )
        
        # Check if data is still loading
        if not stats and not evaluation:
            return ui.div(
                {"class": "loading"},
                ui.p("⏳ Loading data...", style="text-align: center; padding: 20px;")
            )
        
        # Evaluation for move A
        eval_html = "<p style='color: hsl(0, 0%, 73%);'><em>No evaluation available</em></p>"
        if evaluation and evaluation.get('pending'):
            eval_html = "<p style='color: hsl(0, 0%, 73%);'><em>⏳ Evaluating…</em></p>"
        elif evaluation and 'error' in evaluation:
            eval_html = f"<p style='color: hsl(0, 60%, 60%);'><small>Eval error: {evaluation['error']}</small></p>"
        elif evaluation and 'pvs' in evaluation and len(evaluation['pvs']) > 0:
            cp_a = evaluation['pvs'][0].get('cp')
            if cp_a is not None:
                eval_text = f"+{cp_a/100:.2f}" if cp_a >= 0 else f"{cp_a/100:.2f}"
                eval_html = f"<p><strong>Evaluation:</strong> <span style='color: hsl(0, 0%, 100%); font-weight: 700; font-size: 1.1em;'>{eval_text}</span></p>"
        
        # Stats for move A
        stats_html = "<p style='color: hsl(0, 0%, 73%);'><em>No statistics available</em></p>"
        if stats and 'error' in stats:
            stats_html = f"<p style='color: hsl(0, 60%, 60%);'><small>Stats error: {stats['error']}</small></p>"
        elif stats and 'error' not in stats:
            total_a = stats.get("white", 0) + stats.get("draws", 0) + stats.get("black", 0)
            if total_a > 0:
                white_pct_a = round(stats.get("white", 0) / total_a * 100, 1)
                draw_pct = round(stats.get("draws", 0) / total_a * 100, 1)
                black_pct = round(stats.get("black", 0) / total_a * 100, 1)
                stats_html = f"""
                    <p><strong>Total Games:</strong> <span style="color: hsl(0, 0%, 100%); font-weight: 700;">{total_a:,}</span></p>
                    <p><strong>Results:</strong></p>
                    <ul style="margin: 5px 0; padding-left: 20px; color: hsl(0, 0%, 100%);">
                        <li>White: <span style="font-weight: 700;">{white_pct_a}%</span></li>
                        <li>Draw: <span style="font-weight: 700;">{draw_pct}%</span></li>
                        <li>Black: <span style="font-weight: 700;">{black_pct}%</span></li>
                    </ul>
                """
        
        return ui.HTML(f"""
            <div class="metric-card" style="height: 100%;">
                <h5 style="color: hsl(209, 79%, 56%); margin-top: 0;">{move_san}</h5>
                {eval_html}
                <hr style="margin: 10px 0;">
                {stats_html}
            </div>
        """)
    
    @output
    @render.ui
    def move_b_details():
        stats = move_b_stats()
        evaluation = move_b_eval()
        move_san = selected_move_b()
        
        if not move_san:
            return ui.div(
                {"class": "loading"},
                ui.p("Click a move from the selection panel above", style="text-align: center; padding: 20px; color: #6c757d;")
            )
        
        # Check if data is still loading
        if not stats and not evaluation:
            return ui.div(
                {"class": "loading"},
                ui.p("⏳ Loading data...", style="text-align: center; padding: 20px;")
            )
        
        # Evaluation for move B
        eval_html = "<p style='color: hsl(0, 0%, 73%);'><em>No evaluation available</em></p>"
        if evaluation and evaluation.get('pending'):
            eval_html = "<p style='color: hsl(0, 0%, 73%);'><em>⏳ Evaluating…</em></p>"
        elif evaluation and 'error' in evaluation:
            eval_html = f"<p style='color: hsl(0, 60%, 60%);'><small>Eval error: {evaluation['error']}</small></p>"
        elif evaluation and 'pvs' in evaluation and len(evaluation['pvs']) > 0:
            cp_b = evaluation['pvs'][0].get('cp')
            if cp_b is not None:
                eval_text = f"+{cp_b/100:.2f}" if cp_b >= 0 else f"{cp_b/100:.2f}"
                eval_html = f"<p><strong>Evaluation:</strong> <span style='color: hsl(0, 0%, 100%); font-weight: 700; font-size: 1.1em;'>{eval_text}</span></p>"
        
        # Stats for move B
        stats_html = "<p style='color: hsl(0, 0%, 73%);'><em>No statistics available</em></p>"
        if stats and 'error' in stats:
            stats_html = f"<p style='color: hsl(0, 60%, 60%);'><small>Stats error: {stats['error']}</small></p>"
        elif stats and 'error' not in stats:
            total_b = stats.get("white", 0) + stats.get("draws", 0) + stats.get("black", 0)
            if total_b > 0:
                white_pct_b = round(stats.get("white", 0) / total_b * 100, 1)
                draw_pct = round(stats.get("draws", 0) / total_b * 100, 1)
                black_pct = round(stats.get("black", 0) / total_b * 100, 1)
                stats_html = f"""
                    <p><strong>Total Games:</strong> <span style="color: hsl(0, 0%, 100%); font-weight: 700;">{total_b:,}</span></p>
                    <p><strong>Results:</strong></p>
                    <ul style="margin: 5px 0; padding-left: 20px; color: hsl(0, 0%, 100%);">
                        <li>White: <span style="font-weight: 700;">{white_pct_b}%</span></li>
                        <li>Draw: <span style="font-weight: 700;">{draw_pct}%</span></li>
                        <li>Black: <span style="font-weight: 700;">{black_pct}%</span></li>
                    </ul>
                """
        
        return ui.HTML(f"""
            <div class="metric-card" style="height: 100%;">
                <h5 style="color: hsl(88, 62%, 37%); margin-top: 0;">{move_san}</h5>
                {eval_html}
                <hr style="margin: 10px 0;">
                {stats_html}
            </div>
        """)
    

    @output
    @render.ui
    def comparison_panel():
        move_a_san = selected_move_a()
        move_b_san = selected_move_b()
        
        # Only show if both moves are selected
        if not move_a_san or not move_b_san:
            return ui.div()
        
        stats_a = move_a_stats()
        eval_a = move_a_eval()
        stats_b = move_b_stats()
        eval_b = move_b_eval()
        
        # Check if data is loaded (treat pending eval as loading)
        if (
            not stats_a
            or not stats_b
            or not eval_a
            or not eval_b
            or (isinstance(eval_a, dict) and eval_a.get("pending"))
            or (isinstance(eval_b, dict) and eval_b.get("pending"))
        ):
            return ui.tags.div(
                {"class": "card"},
                ui.tags.div(
                    {"class": "card-header"},
                    ui.h4("📊 Head-to-Head Comparison", style="margin: 0;"),
                ),
                ui.tags.div(
                    {"class": "card-body"},
                    ui.div(
                        {"class": "loading"},
                        ui.p("⏳ Loading comparison data...", style="text-align: center; padding: 20px;"),
                    ),
                ),
            )
        
        # Extract evaluation data
        cp_a = None
        cp_b = None
        eval_a_text = "N/A"
        eval_b_text = "N/A"
        eval_delta = ""
        
        if eval_a and 'pvs' in eval_a and len(eval_a['pvs']) > 0:
            cp_a = eval_a['pvs'][0].get('cp')
            if cp_a is not None:
                eval_a_text = f"+{cp_a/100:.2f}" if cp_a >= 0 else f"{cp_a/100:.2f}"
        
        if eval_b and 'pvs' in eval_b and len(eval_b['pvs']) > 0:
            cp_b = eval_b['pvs'][0].get('cp')
            if cp_b is not None:
                eval_b_text = f"+{cp_b/100:.2f}" if cp_b >= 0 else f"{cp_b/100:.2f}"
        
        # Calculate delta
        if cp_a is not None and cp_b is not None:
            delta_cp = abs(cp_a - cp_b)
            delta_text = f"Δ {delta_cp/100:.2f}"
            eval_delta = f"<span class='delta-indicator' style='color: hsl(0, 0%, 70%);'>{delta_text}</span>"
        
        # Determine eval winner
        eval_a_class = ""
        eval_b_class = ""
        if cp_a is not None and cp_b is not None:
            if cp_a > cp_b:
                eval_a_class = "winner metric-better"
                eval_b_class = "loser"
                eval_a_text += f" <span class='delta-indicator delta-positive'>↑ +{(cp_a-cp_b)/100:.2f}</span>"
                eval_b_text += f" <span class='delta-indicator delta-negative'>↓ {(cp_b-cp_a)/100:.2f}</span>"
            elif cp_b > cp_a:
                eval_b_class = "winner metric-better"
                eval_a_class = "loser"
                eval_b_text += f" <span class='delta-indicator delta-positive'>↑ +{(cp_b-cp_a)/100:.2f}</span>"
                eval_a_text += f" <span class='delta-indicator delta-negative'>↓ {(cp_a-cp_b)/100:.2f}</span>"
            else:
                eval_a_class = eval_b_class = "tie"
        
        # Extract stats data
        total_a = stats_a.get("white", 0) + stats_a.get("draws", 0) + stats_a.get("black", 0)
        total_b = stats_b.get("white", 0) + stats_b.get("draws", 0) + stats_b.get("black", 0)
        
        white_pct_a = 0
        draw_pct_a = 0
        black_pct_a = 0
        white_pct_b = 0
        draw_pct_b = 0
        black_pct_b = 0
        
        if total_a > 0:
            white_pct_a = round(stats_a.get("white", 0) / total_a * 100, 1)
            draw_pct_a = round(stats_a.get("draws", 0) / total_a * 100, 1)
            black_pct_a = round(stats_a.get("black", 0) / total_a * 100, 1)
        
        if total_b > 0:
            white_pct_b = round(stats_b.get("white", 0) / total_b * 100, 1)
            draw_pct_b = round(stats_b.get("draws", 0) / total_b * 100, 1)
            black_pct_b = round(stats_b.get("black", 0) / total_b * 100, 1)
        
        # Determine win rate winners with deltas
        white_a_class = ""
        white_b_class = ""
        white_a_display = f"{white_pct_a}%"
        white_b_display = f"{white_pct_b}%"
        
        if total_a > 0 and total_b > 0:
            white_delta = white_pct_a - white_pct_b
            if white_pct_a > white_pct_b:
                white_a_class = "winner metric-better"
                white_b_class = "loser"
                white_a_display += f" <span class='delta-indicator delta-positive'>↑ +{white_delta:.1f}</span>"
                white_b_display += f" <span class='delta-indicator delta-negative'>↓ {-white_delta:.1f}</span>"
            elif white_pct_b > white_pct_a:
                white_b_class = "winner metric-better"
                white_a_class = "loser"
                white_b_display += f" <span class='delta-indicator delta-positive'>↑ +{-white_delta:.1f}</span>"
                white_a_display += f" <span class='delta-indicator delta-negative'>↓ {white_delta:.1f}</span>"
            else:
                white_a_class = white_b_class = "tie"
        
        draw_a_class = ""
        draw_b_class = ""
        draw_a_display = f"{draw_pct_a}%"
        draw_b_display = f"{draw_pct_b}%"
        
        if total_a > 0 and total_b > 0:
            draw_delta = draw_pct_a - draw_pct_b
            if draw_pct_a > draw_pct_b:
                draw_a_class = "winner"
                draw_b_class = "loser"
                draw_a_display += f" <span class='delta-indicator delta-positive'>↑ +{draw_delta:.1f}</span>"
                draw_b_display += f" <span class='delta-indicator delta-negative'>↓ {-draw_delta:.1f}</span>"
            elif draw_pct_b > draw_pct_a:
                draw_b_class = "winner"
                draw_a_class = "loser"
                draw_b_display += f" <span class='delta-indicator delta-positive'>↑ +{-draw_delta:.1f}</span>"
                draw_a_display += f" <span class='delta-indicator delta-negative'>↓ {draw_delta:.1f}</span>"
            else:
                draw_a_class = draw_b_class = "tie"
        
        black_a_class = ""
        black_b_class = ""
        black_a_display = f"{black_pct_a}%"
        black_b_display = f"{black_pct_b}%"
        
        if total_a > 0 and total_b > 0:
            black_delta = black_pct_a - black_pct_b
            if black_pct_a > black_pct_b:
                black_a_class = "winner metric-better"
                black_b_class = "loser"
                black_a_display += f" <span class='delta-indicator delta-positive'>↑ +{black_delta:.1f}</span>"
                black_b_display += f" <span class='delta-indicator delta-negative'>↓ {-black_delta:.1f}</span>"
            elif black_pct_b > black_pct_a:
                black_b_class = "winner metric-better"
                black_a_class = "loser"
                black_b_display += f" <span class='delta-indicator delta-positive'>↑ +{-black_delta:.1f}</span>"
                black_a_display += f" <span class='delta-indicator delta-negative'>↓ {black_delta:.1f}</span>"
            else:
                black_a_class = black_b_class = "tie"
        
        # Determine total games winner (more data is better for reliability)
        games_a_class = ""
        games_b_class = ""
        if total_a > total_b:
            games_a_class = "winner"
            games_b_class = "loser"
        elif total_b > total_a:
            games_b_class = "winner"
            games_a_class = "loser"
        else:
            games_a_class = games_b_class = "tie"
        
        return ui.tags.div(
            {"class": "card"},
            ui.tags.div(
                {"class": "card-header"},
                ui.h4("📊 Head-to-Head Comparison", style="margin: 0;"),
            ),
            ui.tags.div(
                {"class": "card-body"},
                ui.HTML(
                    f"""
                    <div class="comparison-panel" role="region" aria-label="Move comparison table">
                        <table class="comparison-table">
                            <thead>
                                <tr>
                                    <th class="metric-name" scope="col">Metric</th>
                                    <th scope="col" style="color: hsl(209, 79%, 56%); font-weight: 700;">{move_a_san}</th>
                                    <th scope="col" style="color: hsl(88, 62%, 37%); font-weight: 700;">{move_b_san}</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td class="metric-name" scope="row">Engine Evaluation {eval_delta}</td>
                                    <td class="{eval_a_class}">{eval_a_text}</td>
                                    <td class="{eval_b_class}">{eval_b_text}</td>
                                </tr>
                                <tr>
                                    <td class="metric-name" scope="row">Total Games</td>
                                    <td class="{games_a_class}">{total_a:,}</td>
                                    <td class="{games_b_class}">{total_b:,}</td>
                                </tr>
                                <tr>
                                    <td class="metric-name" scope="row">White Win %</td>
                                    <td class="{white_a_class}">{white_a_display}</td>
                                    <td class="{white_b_class}">{white_b_display}</td>
                                </tr>
                                <tr>
                                    <td class="metric-name" scope="row">Draw %</td>
                                    <td class="{draw_a_class}">{draw_a_display}</td>
                                    <td class="{draw_b_class}">{draw_b_display}</td>
                                </tr>
                                <tr>
                                    <td class="metric-name" scope="row">Black Win %</td>
                                    <td class="{black_a_class}">{black_a_display}</td>
                                    <td class="{black_b_class}">{black_b_display}</td>
                                </tr>
                            </tbody>
                        </table>
                        <div style="margin-top: 15px; font-size: 0.85em; color: hsl(0, 0%, 58%); text-align: center;" role="note" aria-label="Color legend">
                            <span style="background-color: rgba(88, 153, 0, 0.3); padding: 4px 10px; border-radius: 3px; margin: 0 5px; font-weight: 600; color: hsl(88, 62%, 50%);">Green</span> = Better
                            <span style="background-color: rgba(220, 50, 47, 0.3); padding: 4px 10px; border-radius: 3px; margin: 0 5px; font-weight: 600; color: hsl(0, 60%, 60%);">Red</span> = Worse
                            <span style="background-color: rgba(181, 137, 0, 0.3); padding: 4px 10px; border-radius: 3px; margin: 0 5px; font-weight: 600; color: hsl(37, 74%, 53%);">Yellow</span> = Tied
                            <br><small style="margin-top: 8px; display: inline-block;">↑↓ arrows show difference between moves</small>
                        </div>
                    </div>
                    """
                ),
            ),
        )


app = App(app_ui, server)