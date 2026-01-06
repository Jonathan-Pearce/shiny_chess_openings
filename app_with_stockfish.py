from shiny import App, render, ui, reactive
import chess
import chess.svg
import requests
from pathlib import Path

# JavaScript code to load and interact with Stockfish
stockfish_js = """
<script src="https://cdn.jsdelivr.net/npm/stockfish.js@10.0.2/stockfish.js"></script>
<script>
var stockfish = null;
var currentEvaluation = "Initializing...";
var bestMove = "";
var principalVariation = [];

function initStockfish() {
    if (typeof STOCKFISH === "function") {
        stockfish = STOCKFISH();
        stockfish.onmessage = function(event) {
            const line = event.data ? event.data : event;
            
            // Parse evaluation
            if (line.includes("score cp")) {
                const match = line.match(/score cp (-?\\d+)/);
                if (match) {
                    const centipawns = parseInt(match[1]);
                    currentEvaluation = (centipawns / 100).toFixed(2);
                }
            } else if (line.includes("score mate")) {
                const match = line.match(/score mate (-?\\d+)/);
                if (match) {
                    const moves = match[1];
                    currentEvaluation = "M" + moves;
                }
            }
            
            // Parse best move
            if (line.includes("bestmove")) {
                const match = line.match(/bestmove (\\S+)/);
                if (match) {
                    bestMove = match[1];
                }
            }
            
            // Parse principal variation
            if (line.includes(" pv ")) {
                const match = line.match(/pv (.+)/);
                if (match) {
                    principalVariation = match[1].split(" ").slice(0, 5);
                }
            }
        };
        
        stockfish.postMessage("uci");
        stockfish.postMessage("setoption name Skill Level value 20");
        stockfish.postMessage("isready");
    }
}

function analyzePosition(fen) {
    if (stockfish) {
        currentEvaluation = "Analyzing...";
        bestMove = "";
        principalVariation = [];
        
        stockfish.postMessage("position fen " + fen);
        stockfish.postMessage("go depth 15");
    }
}

function getEvaluation() {
    return currentEvaluation;
}

function getBestMove() {
    return bestMove;
}

function getPV() {
    return principalVariation.join(" ");
}

// Initialize on load
setTimeout(initStockfish, 1000);
</script>
"""

app_ui = ui.page_fluid(
    ui.head_content(
        ui.HTML(stockfish_js)
    ),
    ui.panel_title("Chess Opening Explorer with Stockfish"),
    ui.markdown(
        """
        Enter chess moves in standard algebraic notation (e.g., e4 e5 Nf3 Nc6) 
        to explore opening statistics from the Lichess database and get **real Stockfish analysis**.
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
            ui.input_action_button("sf_analyze", "Run Stockfish", class_="btn-success"),
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
                "Stockfish Evaluation",
                ui.output_ui("stockfish_eval"),
                ui.tags.div(id="sf-results")
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
    @reactive.event(input.sf_analyze)
    def _():
        board = board_state.get()
        fen = board.fen()
        
        # Trigger Stockfish analysis via JavaScript
        ui.insert_ui(
            ui.HTML(f'<script>analyzePosition("{fen}");</script>'),
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
    def stockfish_eval():
        board = board_state.get()
        fen = board.fen()
        
        return ui.div(
            ui.h4("Stockfish Engine Analysis"),
            ui.p(ui.strong("Current Position: "), fen),
            ui.hr(),
            ui.markdown(
                """
                **Instructions:**
                1. Click the "Run Stockfish" button to analyze the current position
                2. Wait a few seconds for the analysis to complete
                3. Results will show evaluation, best move, and principal variation
                """
            ),
            ui.hr(),
            ui.HTML("""
                <div id="stockfish-results">
                    <h5>Analysis Results:</h5>
                    <p><strong>Evaluation:</strong> <span id="eval-score">Click 'Run Stockfish' to analyze</span></p>
                    <p><strong>Best Move:</strong> <span id="best-move">-</span></p>
                    <p><strong>Principal Variation:</strong> <span id="pv">-</span></p>
                </div>
                <script>
                    function updateResults() {
                        document.getElementById('eval-score').textContent = getEvaluation();
                        document.getElementById('best-move').textContent = getBestMove() || '-';
                        document.getElementById('pv').textContent = getPV() || '-';
                    }
                    setInterval(updateResults, 500);
                </script>
            """),
            ui.hr(),
            ui.p(
                ui.em("Note: Stockfish.js runs directly in your browser. "),
                ui.em("Analysis depth is set to 15 for reasonable performance.")
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
