from shiny import App, render, ui, reactive
import chess
import chess.svg
import requests
from pathlib import Path

# JavaScript code to load and interact with chess-wasm
chess_wasm_js = """
<script type="module">
// Import chess-wasm from CDN
import init, { Chess } from 'https://unpkg.com/chess-wasm@0.3.0/chess.js';

let chessEngine = null;
let currentEvaluation = "Initializing...";
let bestMove = "";
let engineReady = false;

async function initChessWasm() {
    try {
        await init();
        chessEngine = new Chess();
        engineReady = true;
        currentEvaluation = "Ready";
        console.log("Chess-wasm engine initialized successfully");
    } catch (error) {
        console.error("Failed to initialize chess-wasm:", error);
        currentEvaluation = "Failed to initialize";
    }
}

window.analyzePositionWasm = function(fen) {
    if (!engineReady || !chessEngine) {
        currentEvaluation = "Engine not ready";
        return;
    }
    
    try {
        currentEvaluation = "Analyzing...";
        bestMove = "";
        
        // Set position
        chessEngine.load_fen(fen);
        
        // Analyze position (depth 10-12 for good balance)
        const result = chessEngine.go({ depth: 12 });
        
        if (result) {
            // Extract evaluation
            if (result.score !== undefined) {
                // Score is in centipawns
                const scorePawns = result.score / 100;
                currentEvaluation = scorePawns.toFixed(2);
            }
            
            // Extract best move
            if (result.best_move) {
                bestMove = result.best_move;
            }
        } else {
            currentEvaluation = "Analysis complete";
        }
        
    } catch (error) {
        console.error("Analysis error:", error);
        currentEvaluation = "Error: " + error.message;
    }
}

window.getWasmEvaluation = function() {
    return currentEvaluation;
}

window.getWasmBestMove = function() {
    return bestMove;
}

window.isWasmReady = function() {
    return engineReady;
}

// Initialize on load
initChessWasm();
</script>
"""

app_ui = ui.page_fluid(
    ui.head_content(
        ui.HTML(chess_wasm_js)
    ),
    ui.panel_title("Chess Opening Explorer with Chess-WASM"),
    ui.markdown(
        """
        Enter chess moves in standard algebraic notation (e.g., e4 e5 Nf3 Nc6) 
        to explore opening statistics and get **lightweight chess-wasm engine analysis**.
        """
    ),
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_text_area(
                "moves",
                "Enter moves (space-separated):",
                value="e4 e5 Nf3",
                rows=3,
                width="100%"
            ),
            ui.input_action_button("analyze", "Analyze Opening", class_="btn-primary"),
            ui.input_action_button("wasm_analyze", "Run Chess-WASM", class_="btn-success"),
            ui.input_action_button("reset", "Reset Board", class_="btn-secondary"),
            ui.hr(),
            ui.markdown("**Quick Start Examples:**"),
            ui.input_action_button("italian", "Italian Game", class_="btn-sm"),
            ui.input_action_button("sicilian", "Sicilian Defense", class_="btn-sm"),
            ui.input_action_button("french", "French Defense", class_="btn-sm"),
            width=300
        ),
        ui.navset_tab(
            ui.nav_panel(
                "Board",
                ui.output_ui("board_display"),
                ui.output_text_verbatim("move_history")
            ),
            ui.nav_panel(
                "Opening Statistics",
                ui.output_ui("opening_stats")
            ),
            ui.nav_panel(
                "Chess-WASM Evaluation",
                ui.output_ui("wasm_eval")
            ),
            ui.nav_panel(
                "Popular Next Moves",
                ui.output_ui("next_moves")
            )
        )
    )
)


def server(input, output, session):
    board_state = reactive.Value(chess.Board())
    
    @reactive.Effect
    @reactive.event(input.italian)
    def _():
        ui.update_text("moves", value="e4 e5 Nf3 Nc6 Bc4")
    
    @reactive.Effect
    @reactive.event(input.sicilian)
    def _():
        ui.update_text("moves", value="e4 c5 Nf3 d6 d4")
    
    @reactive.Effect
    @reactive.event(input.french)
    def _():
        ui.update_text("moves", value="e4 e6 d4 d5")
    
    @reactive.Effect
    @reactive.event(input.reset)
    def _():
        board_state.set(chess.Board())
        ui.update_text("moves", value="")
    
    @reactive.Effect
    @reactive.event(input.analyze)
    def _():
        board = chess.Board()
        moves_text = input.moves().strip()
        
        if moves_text:
            moves = moves_text.split()
            try:
                for move_san in moves:
                    move = board.parse_san(move_san)
                    board.push(move)
                board_state.set(board)
            except ValueError as e:
                pass
    
    @reactive.Effect
    @reactive.event(input.wasm_analyze)
    def _():
        board = board_state.get()
        fen = board.fen()
        
        # Trigger chess-wasm analysis via JavaScript
        ui.insert_ui(
            ui.HTML(f'<script>if (window.analyzePositionWasm) analyzePositionWasm("{fen}");</script>'),
            selector="body",
            where="beforeEnd"
        )
    
    @output
    @render.ui
    def board_display():
        board = board_state.get()
        svg = chess.svg.board(
            board=board,
            size=500,
            coordinates=True
        )
        return ui.HTML(svg)
    
    @output
    @render.text
    def move_history():
        board = board_state.get()
        if len(board.move_stack) == 0:
            return "No moves played yet. Starting position."
        
        moves_text = []
        temp_board = chess.Board()
        for i, move in enumerate(board.move_stack):
            if i % 2 == 0:
                moves_text.append(f"{i//2 + 1}. {temp_board.san(move)}")
            else:
                moves_text[-1] += f" {temp_board.san(move)}"
            temp_board.push(move)
        
        return "Move History:\n" + " ".join(moves_text)
    
    @output
    @render.ui
    def opening_stats():
        board = board_state.get()
        fen = board.fen()
        
        try:
            response = requests.get(
                "https://explorer.lichess.ovh/lichess",
                params={
                    "fen": fen,
                    "variant": "standard",
                    "speeds": "blitz,rapid,classical",
                    "ratings": "2000,2200,2500"
                },
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            
            white_wins = data.get("white", 0)
            draws = data.get("draws", 0)
            black_wins = data.get("black", 0)
            total_games = white_wins + draws + black_wins
            
            if total_games == 0:
                return ui.div(
                    ui.h4("No Statistics Available"),
                    ui.p("This position has not been reached in the Lichess database.")
                )
            
            white_pct = (white_wins / total_games * 100) if total_games > 0 else 0
            draw_pct = (draws / total_games * 100) if total_games > 0 else 0
            black_pct = (black_wins / total_games * 100) if total_games > 0 else 0
            
            opening_name = data.get("opening", {}).get("name", "Unknown Opening")
            
            return ui.div(
                ui.h4("Lichess Database Statistics"),
                ui.p(ui.strong("Opening: "), opening_name),
                ui.p(ui.strong("Total Games: "), f"{total_games:,}"),
                ui.hr(),
                ui.h5("Results:"),
                ui.div(
                    ui.p(f"White wins: {white_wins:,} ({white_pct:.1f}%)"),
                    ui.p(f"Draws: {draws:,} ({draw_pct:.1f}%)"),
                    ui.p(f"Black wins: {black_wins:,} ({black_pct:.1f}%)"),
                ),
                ui.hr(),
                ui.div(
                    ui.div(
                        f"White {white_pct:.0f}%",
                        style=f"width: {white_pct}%; background-color: #fff; border: 1px solid #000; display: inline-block; padding: 5px; text-align: center;"
                    ),
                    ui.div(
                        f"Draw {draw_pct:.0f}%",
                        style=f"width: {draw_pct}%; background-color: #888; border: 1px solid #000; display: inline-block; padding: 5px; text-align: center;"
                    ),
                    ui.div(
                        f"Black {black_pct:.0f}%",
                        style=f"width: {black_pct}%; background-color: #000; color: #fff; border: 1px solid #000; display: inline-block; padding: 5px; text-align: center;"
                    )
                )
            )
            
        except requests.RequestException as e:
            return ui.div(
                ui.h4("Error Loading Statistics"),
                ui.p(f"Could not fetch data from Lichess API: {str(e)}")
            )
    
    @output
    @render.ui
    def wasm_eval():
        board = board_state.get()
        fen = board.fen()
        
        # Calculate basic material as supplementary info
        piece_values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
            chess.KING: 0
        }
        
        white_material = 0
        black_material = 0
        
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                value = piece_values[piece.piece_type]
                if piece.color == chess.WHITE:
                    white_material += value
                else:
                    black_material += value
        
        material_diff = white_material - black_material
        
        # Check game state
        if board.is_checkmate():
            game_status = "Checkmate! " + ("Black" if board.turn else "White") + " wins."
        elif board.is_stalemate():
            game_status = "Stalemate - Draw"
        elif board.is_insufficient_material():
            game_status = "Insufficient material - Draw"
        else:
            game_status = "Game in progress"
        
        return ui.div(
            ui.h4("⚡ Chess-WASM Engine Analysis"),
            ui.p(ui.strong("Game Status: "), game_status),
            ui.p(ui.strong("Current Position: "), fen),
            ui.hr(),
            ui.markdown(
                """
                **Instructions:**
                1. Click the "Run Chess-WASM" button to analyze the current position
                2. The lightweight WebAssembly engine will evaluate the position
                3. Results appear in 1-3 seconds
                
                **About Chess-WASM:**
                - Lightweight (~100KB) WebAssembly chess engine
                - Runs entirely in your browser
                - Good strength, optimized for speed
                - Analysis depth: 12 (balanced performance)
                """
            ),
            ui.hr(),
            ui.HTML("""
                <div id="wasm-results">
                    <h5>Analysis Results:</h5>
                    <div style="background-color: #f0f0f0; padding: 15px; border-radius: 5px; margin: 10px 0;">
                        <p><strong>Engine Status:</strong> <span id="wasm-status">Initializing...</span></p>
                        <p><strong>Evaluation:</strong> <span id="wasm-eval-score">Click 'Run Chess-WASM' to analyze</span></p>
                        <p><strong>Best Move (UCI):</strong> <span id="wasm-best-move">-</span></p>
                    </div>
                </div>
                <script>
                    function updateWasmResults() {
                        if (typeof isWasmReady === 'function') {
                            const ready = isWasmReady();
                            document.getElementById('wasm-status').textContent = ready ? '✓ Ready' : 'Loading...';
                            
                            if (ready && typeof getWasmEvaluation === 'function') {
                                const eval_score = getWasmEvaluation();
                                document.getElementById('wasm-eval-score').textContent = eval_score;
                                
                                // Interpret evaluation
                                if (eval_score !== 'Ready' && eval_score !== 'Initializing...' && eval_score !== 'Analyzing...') {
                                    try {
                                        const score = parseFloat(eval_score);
                                        let interpretation = '';
                                        if (score > 2) interpretation = ' (White is winning)';
                                        else if (score > 0.5) interpretation = ' (White is better)';
                                        else if (score < -2) interpretation = ' (Black is winning)';
                                        else if (score < -0.5) interpretation = ' (Black is better)';
                                        else interpretation = ' (Equal position)';
                                        
                                        document.getElementById('wasm-eval-score').textContent = eval_score + interpretation;
                                    } catch (e) {}
                                }
                            }
                            
                            if (typeof getWasmBestMove === 'function') {
                                const best_move = getWasmBestMove();
                                document.getElementById('wasm-best-move').textContent = best_move || '-';
                            }
                        }
                    }
                    setInterval(updateWasmResults, 500);
                </script>
            """),
            ui.hr(),
            ui.h5("Material Balance (Reference):"),
            ui.p(f"White: {white_material} points | Black: {black_material} points | Difference: {material_diff:+.1f}"),
            ui.hr(),
            ui.p(
                ui.em("Note: Chess-WASM is a lightweight engine (~100KB) optimized for browser use. "),
                ui.em("For stronger analysis, consider using Lichess Cloud API or Stockfish.js."),
                style="font-size: 0.9em; color: #666;"
            )
        )
    
    @output
    @render.ui
    def next_moves():
        board = board_state.get()
        
        if board.is_game_over():
            return ui.div(
                ui.h4("Game Over"),
                ui.p("No more moves available.")
            )
        
        fen = board.fen()
        
        try:
            response = requests.get(
                "https://explorer.lichess.ovh/lichess",
                params={
                    "fen": fen,
                    "variant": "standard",
                    "speeds": "blitz,rapid,classical",
                    "ratings": "2000,2200,2500"
                },
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            
            moves_data = data.get("moves", [])
            
            if not moves_data:
                return ui.div(
                    ui.h4("Popular Next Moves"),
                    ui.p("No data available for next moves in this position.")
                )
            
            moves_data.sort(key=lambda x: x.get("white", 0) + x.get("draws", 0) + x.get("black", 0), reverse=True)
            
            move_elements = [ui.h4("Popular Next Moves (from Lichess Database)")]
            
            for i, move_info in enumerate(moves_data[:10], 1):
                san = move_info.get("san", "?")
                white = move_info.get("white", 0)
                draws = move_info.get("draws", 0)
                black = move_info.get("black", 0)
                total = white + draws + black
                
                if total > 0:
                    white_pct = (white / total * 100)
                    draw_pct = (draws / total * 100)
                    black_pct = (black / total * 100)
                    
                    move_elements.append(
                        ui.div(
                            ui.h5(f"{i}. {san}"),
                            ui.p(f"Played {total:,} times"),
                            ui.p(f"White: {white_pct:.1f}% | Draw: {draw_pct:.1f}% | Black: {black_pct:.1f}%"),
                            ui.hr()
                        )
                    )
            
            return ui.div(*move_elements)
            
        except requests.RequestException as e:
            return ui.div(
                ui.h4("Error Loading Next Moves"),
                ui.p(f"Could not fetch data from Lichess API: {str(e)}")
            )


app = App(app_ui, server)
