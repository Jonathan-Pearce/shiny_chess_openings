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
    "Italian Game": "e4 e5 Nf3 Nc6 Bc4",
    "Sicilian Defense": "e4 c5",
    "French Defense": "e4 e6",
    "Queen's Gambit": "d4 d5 c4",
    "King's Indian": "d4 Nf6 c4 g6",
    "Ruy Lopez": "e4 e5 Nf3 Nc6 Bb5",
}

# Custom CSS for styling
custom_css = """
<style>
.eval-bar {
    height: 30px;
    background: linear-gradient(to right, #000 0%, #000 50%, #fff 50%, #fff 100%);
    border: 2px solid #333;
    border-radius: 5px;
    position: relative;
    margin: 10px 0;
}
.eval-indicator {
    position: absolute;
    height: 100%;
    background-color: #4CAF50;
    transition: left 0.3s ease;
    border-radius: 3px;
}
.metric-card {
    padding: 10px;
    margin: 5px 0;
    border-radius: 5px;
    background-color: #f8f9fa;
}
.better {
    background-color: #d4edda !important;
    border-left: 4px solid #28a745;
}
.worse {
    background-color: #f8d7da !important;
    border-left: 4px solid #dc3545;
}
.board-container {
    max-width: 400px;
    margin: 10px auto;
}
.move-history {
    font-family: monospace;
    padding: 10px;
    background-color: #f8f9fa;
    border-radius: 5px;
    max-height: 100px;
    overflow-y: auto;
    margin-top: 10px;
}
.loading {
    text-align: center;
    padding: 20px;
    color: #6c757d;
}
.welcome-section {
    background-color: #e7f3ff;
    padding: 20px;
    border-radius: 10px;
    margin-bottom: 20px;
    border-left: 5px solid #007bff;
}
</style>
"""

# Chess board JavaScript integration
chessboard_js = """
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<link rel="stylesheet" href="https://unpkg.com/@chrisoakman/chessboardjs@1.0.0/dist/chessboard-1.0.0.min.css">
<script src="https://unpkg.com/@chrisoakman/chessboardjs@1.0.0/dist/chessboard-1.0.0.min.js"></script>
<script>
console.log('Chessboard scripts loaded');

// Initialize boards after page load
window.addEventListener('load', function() {
    console.log('Window loaded, checking for Chessboard...');
    console.log('Chessboard available:', typeof Chessboard !== 'undefined');
    console.log('jQuery available:', typeof $ !== 'undefined');
    console.log('boardA element:', document.getElementById('boardA'));
    console.log('boardB element:', document.getElementById('boardB'));
    
    // Wait a bit for Shiny to be ready
    setTimeout(function() {
        console.log('Attempting to initialize boards...');
        
        try {
            if (document.getElementById('boardA')) {
                window.boardA = Chessboard('boardA', {
                    position: 'start',
                    draggable: true,
                    pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png',
                    onDrop: function(source, target) {
                        console.log('Move attempted:', source, target);
                        if (typeof Shiny !== 'undefined') {
                            Shiny.setInputValue('boardA_move', source + target, {priority: 'event'});
                        }
                        return 'snapback';
                    }
                });
                console.log('✓ Board A initialized successfully');
            } else {
                console.error('✗ boardA element not found');
            }
        } catch(e) {
            console.error('✗ Error initializing boardA:', e);
        }
        
        try {
            if (document.getElementById('boardB')) {
                window.boardB = Chessboard('boardB', {
                    position: 'start',
                    draggable: true,
                    pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png',
                    onDrop: function(source, target) {
                        console.log('Move attempted:', source, target);
                        if (typeof Shiny !== 'undefined') {
                            Shiny.setInputValue('boardB_move', source + target, {priority: 'event'});
                        }
                        return 'snapback';
                    }
                });
                console.log('✓ Board B initialized successfully');
            } else {
                console.error('✗ boardB element not found');
            }
        } catch(e) {
            console.error('✗ Error initializing boardB:', e);
        }
    }, 1000);
});

// Handle custom messages from server to update board positions
if (typeof Shiny !== 'undefined') {
    Shiny.addCustomMessageHandler('update_board', function(message) {
        console.log('Update board message received:', message);
        if (message.board === 'boardA' && window.boardA) {
            try {
                window.boardA.position(message.fen);
                console.log('Board A position updated');
            } catch(e) {
                console.error('Error updating boardA:', e);
            }
        } else if (message.board === 'boardB' && window.boardB) {
            try {
                window.boardB.position(message.fen);
                console.log('Board B position updated');
            } catch(e) {
                console.error('Error updating boardB:', e);
            }
        }
    });
}
</script>
"""

app_ui = ui.page_fluid(
    ui.HTML(custom_css),
    ui.HTML(chessboard_js),
    
    # Welcome Section
    ui.div(
        {"class": "welcome-section"},
        ui.h2("♟️ Chess Opening A/B Testing Tool"),
        ui.p(
            "Compare two chess openings side-by-side with comprehensive statistics and evaluations. "
            "Enter moves in algebraic notation (e.g., 'e4 e5 Nf3'), use preset buttons, or drag pieces on the board."
        ),
        ui.p(
            ui.strong("Metrics: "),
            "Win/Draw/Loss rates from Lichess database, Stockfish cloud evaluation, "
            "popular continuations, and direct comparison highlights."
        ),
    ),
    
    # Two-column comparison layout
    ui.layout_columns(
        # Left Column - Opening A
        ui.card(
            ui.card_header(
                ui.h3("Opening A", style="margin: 0;")
            ),
            
            # Preset buttons
            ui.div(
                ui.strong("Quick Presets:"),
                style="margin-bottom: 10px;"
            ),
            ui.div(
                *[ui.input_action_button(f"preset_a_{i}", name, style="margin: 2px;") 
                  for i, name in enumerate(PRESETS.keys())],
                style="margin-bottom: 15px;"
            ),
            
            # Move input
            ui.input_text("moves_a", "Enter moves (algebraic notation):", 
                         placeholder="e.g., e4 e5 Nf3 Nc6"),
            ui.input_action_button("analyze_a", "Analyze Opening A", class_="btn-primary"),
            
            # Chess board
            ui.div(
                {"class": "board-container"},
                ui.HTML('<div id="boardA" style="width: 400px; height: 400px;"></div>'),
            ),
            
            # Move history
            ui.output_ui("move_history_a"),
            
            # Stats and evaluation
            ui.output_ui("stats_a"),
            ui.output_ui("eval_a"),
        ),
        
        # Right Column - Opening B
        ui.card(
            ui.card_header(
                ui.h3("Opening B", style="margin: 0;")
            ),
            
            # Preset buttons
            ui.div(
                ui.strong("Quick Presets:"),
                style="margin-bottom: 10px;"
            ),
            ui.div(
                *[ui.input_action_button(f"preset_b_{i}", name, style="margin: 2px;") 
                  for i, name in enumerate(PRESETS.keys())],
                style="margin-bottom: 15px;"
            ),
            
            # Move input
            ui.input_text("moves_b", "Enter moves (algebraic notation):", 
                         placeholder="e.g., d4 d5 c4"),
            ui.input_action_button("analyze_b", "Analyze Opening B", class_="btn-primary"),
            
            # Chess board
            ui.div(
                {"class": "board-container"},
                ui.HTML('<div id="boardB" style="width: 400px; height: 400px;"></div>'),
            ),
            
            # Move history
            ui.output_ui("move_history_b"),
            
            # Stats and evaluation
            ui.output_ui("stats_b"),
            ui.output_ui("eval_b"),
        ),
        col_widths=[6, 6],
    ),
    
    # Comparison section
    ui.card(
        ui.card_header(ui.h3("Direct Comparison")),
        ui.output_ui("comparison"),
    ),
)


def server(input, output, session):
    # Reactive values for board states
    board_a = reactive.Value(chess.Board())
    board_b = reactive.Value(chess.Board())
    
    # Reactive values for API data
    stats_a_data = reactive.Value({})
    stats_b_data = reactive.Value({})
    eval_a_data = reactive.Value({})
    eval_b_data = reactive.Value({})
    
    # Track if boards are initialized
    boards_initialized = reactive.Value(False)
    
    @reactive.Effect
    async def _init_boards():
        if not boards_initialized():
            await session.send_custom_message(
                "init_boards",
                {
                    "boardA_fen": board_a().fen(),
                    "boardB_fen": board_b().fen()
                }
            )
            boards_initialized.set(True)
    
    # Preset button handlers for Opening A
    for i, (name, moves) in enumerate(PRESETS.items()):
        @reactive.Effect
        @reactive.event(input[f"preset_a_{i}"])
        def _preset_a(moves=moves):
            ui.update_text("moves_a", value=moves)
    
    # Preset button handlers for Opening B
    for i, (name, moves) in enumerate(PRESETS.items()):
        @reactive.Effect
        @reactive.event(input[f"preset_b_{i}"])
        def _preset_b(moves=moves):
            ui.update_text("moves_b", value=moves)
    
    # Listen for board drag moves and apply if legal
    @reactive.Effect
    @reactive.event(input.boardA_move)
    async def _on_board_a_move():
        move_str = input.boardA_move()
        if not move_str:
            return
        try:
            mv = chess.Move.from_uci(move_str)
            b = board_a().copy()
            if mv in b.legal_moves:
                b.push(mv)
                board_a.set(b)
                # Update the visual board
                await session.send_custom_message(
                    "update_board",
                    {"board": "boardA", "fen": b.fen()}
                )
                # Update text input with move history
                moves = []
                temp = chess.Board()
                for move in b.move_stack:
                    moves.append(temp.san(move))
                    temp.push(move)
                ui.update_text("moves_a", value=" ".join(moves))
        except Exception:
            pass
    
    @reactive.Effect
    @reactive.event(input.boardB_move)
    async def _on_board_b_move():
        move_str = input.boardB_move()
        if not move_str:
            return
        try:
            mv = chess.Move.from_uci(move_str)
            b = board_b().copy()
            if mv in b.legal_moves:
                b.push(mv)
                board_b.set(b)
                # Update the visual board
                await session.send_custom_message(
                    "update_board",
                    {"board": "boardB", "fen": b.fen()}
                )
                # Update text input with move history
                moves = []
                temp = chess.Board()
                for move in b.move_stack:
                    moves.append(temp.san(move))
                    temp.push(move)
                ui.update_text("moves_b", value=" ".join(moves))
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
    
    # Analyze Opening A
    @reactive.Effect
    @reactive.event(input.analyze_a)
    async def _analyze_a():
        try:
            new_board = parse_moves(input.moves_a())
            board_a.set(new_board)
            
            # Update board position
            await session.send_custom_message(
                "update_board",
                {"board": "boardA", "fen": new_board.fen()}
            )
            
            # Fetch stats and evaluation
            fen = new_board.fen()
            stats_task = fetch_lichess_stats(fen)
            eval_task = fetch_cloud_eval(fen)
            
            stats, evaluation = await asyncio.gather(stats_task, eval_task)
            stats_a_data.set(stats)
            eval_a_data.set(evaluation)
            
        except ValueError as e:
            stats_a_data.set({"error": str(e)})
            eval_a_data.set({})
    
    # Analyze Opening B
    @reactive.Effect
    @reactive.event(input.analyze_b)
    async def _analyze_b():
        try:
            new_board = parse_moves(input.moves_b())
            board_b.set(new_board)
            
            # Update board position
            await session.send_custom_message(
                "update_board",
                {"board": "boardB", "fen": new_board.fen()}
            )
            
            # Fetch stats and evaluation
            fen = new_board.fen()
            stats_task = fetch_lichess_stats(fen)
            eval_task = fetch_cloud_eval(fen)
            
            stats, evaluation = await asyncio.gather(stats_task, eval_task)
            stats_b_data.set(stats)
            eval_b_data.set(evaluation)
            
        except ValueError as e:
            stats_b_data.set({"error": str(e)})
            eval_b_data.set({})
    
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
                    encoded_value = await js.encodeURIComponent(value)
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
                encoded_fen = await js.encodeURIComponent(fen)
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
    
    @output
    @render.ui
    def move_history_a():
        board = board_a()
        moves = []
        temp_board = chess.Board()
        
        for i, move in enumerate(board.move_stack):
            move_num = (i // 2) + 1
            if i % 2 == 0:
                moves.append(f"{move_num}. {temp_board.san(move)}")
            else:
                moves.append(temp_board.san(move))
            temp_board.push(move)
        
        history = " ".join(moves) if moves else "Starting position"
        return ui.div(
            {"class": "move-history"},
            ui.strong("Moves: "),
            history
        )
    
    @output
    @render.ui
    def move_history_b():
        board = board_b()
        moves = []
        temp_board = chess.Board()
        
        for i, move in enumerate(board.move_stack):
            move_num = (i // 2) + 1
            if i % 2 == 0:
                moves.append(f"{move_num}. {temp_board.san(move)}")
            else:
                moves.append(temp_board.san(move))
            temp_board.push(move)
        
        history = " ".join(moves) if moves else "Starting position"
        return ui.div(
            {"class": "move-history"},
            ui.strong("Moves: "),
            history
        )
    
    @output
    @render.ui
    def stats_a():
        data = stats_a_data()
        if not data:
            return ui.div({"class": "loading"}, "Click 'Analyze Opening A' to load statistics")
        
        if "error" in data:
            return ui.div(f"❌ Error: {data['error']}", style="color: red; padding: 10px;")
        
        total_games = data.get("white", 0) + data.get("draws", 0) + data.get("black", 0)
        if total_games == 0:
            return ui.div("No games found for this position", style="padding: 10px;")
        
        white_pct = round(data.get("white", 0) / total_games * 100, 1)
        draw_pct = round(data.get("draws", 0) / total_games * 100, 1)
        black_pct = round(data.get("black", 0) / total_games * 100, 1)
        
        # Top moves
        moves = data.get("moves", [])[:5]
        top_moves_html = ""
        if moves:
            top_moves_html = "<div style='margin-top: 10px;'><strong>Popular Moves:</strong><ul style='margin: 5px 0;'>"
            for m in moves:
                move_total = m.get("white", 0) + m.get("draws", 0) + m.get("black", 0)
                top_moves_html += f"<li>{m.get('san', '?')}: {move_total} games</li>"
            top_moves_html += "</ul></div>"
        
        return ui.HTML(f"""
            <div class="metric-card">
                <h5>📊 Opening Statistics</h5>
                <p><strong>Total Games:</strong> {total_games:,}</p>
                <p><strong>Results:</strong></p>
                <ul>
                    <li>White wins: {white_pct}%</li>
                    <li>Draws: {draw_pct}%</li>
                    <li>Black wins: {black_pct}%</li>
                </ul>
                {top_moves_html}
            </div>
        """)
    
    @output
    @render.ui
    def stats_b():
        data = stats_b_data()
        if not data:
            return ui.div({"class": "loading"}, "Click 'Analyze Opening B' to load statistics")
        
        if "error" in data:
            return ui.div(f"❌ Error: {data['error']}", style="color: red; padding: 10px;")
        
        total_games = data.get("white", 0) + data.get("draws", 0) + data.get("black", 0)
        if total_games == 0:
            return ui.div("No games found for this position", style="padding: 10px;")
        
        white_pct = round(data.get("white", 0) / total_games * 100, 1)
        draw_pct = round(data.get("draws", 0) / total_games * 100, 1)
        black_pct = round(data.get("black", 0) / total_games * 100, 1)
        
        # Top moves
        moves = data.get("moves", [])[:5]
        top_moves_html = ""
        if moves:
            top_moves_html = "<div style='margin-top: 10px;'><strong>Popular Moves:</strong><ul style='margin: 5px 0;'>"
            for m in moves:
                move_total = m.get("white", 0) + m.get("draws", 0) + m.get("black", 0)
                top_moves_html += f"<li>{m.get('san', '?')}: {move_total} games</li>"
            top_moves_html += "</ul></div>"
        
        return ui.HTML(f"""
            <div class="metric-card">
                <h5>📊 Opening Statistics</h5>
                <p><strong>Total Games:</strong> {total_games:,}</p>
                <p><strong>Results:</strong></p>
                <ul>
                    <li>White wins: {white_pct}%</li>
                    <li>Draws: {draw_pct}%</li>
                    <li>Black wins: {black_pct}%</li>
                </ul>
                {top_moves_html}
            </div>
        """)
    
    @output
    @render.ui
    def eval_a():
        data = eval_a_data()
        if not data:
            return ui.div({"class": "loading"}, "Evaluation will appear after analysis")
        
        if "error" in data:
            return ui.div(f"❌ Eval Error: {data['error']}", style="color: red; padding: 10px;")
        
        cp = data.get("pvs", [{}])[0].get("cp")
        if cp is None:
            return ui.div("Evaluation not available", style="padding: 10px;")
        
        # Clamp centipawns and convert to percentage
        clamped_cp = max(-1000, min(1000, cp))
        eval_pct = 50 + (clamped_cp / 20)
        
        eval_text = f"+{cp/100:.2f}" if cp >= 0 else f"{cp/100:.2f}"
        depth = data.get("depth", "?")
        
        # Best move
        best_move = "N/A"
        if data.get("pvs") and data["pvs"][0].get("moves"):
            uci_move = data["pvs"][0]["moves"].split()[0]
            try:
                move = chess.Move.from_uci(uci_move)
                best_move = board_a().san(move)
            except:
                best_move = uci_move
        
        return ui.HTML(f"""
            <div class="metric-card">
                <h5>🤖 Stockfish Cloud Evaluation</h5>
                <div class="eval-bar">
                    <div class="eval-indicator" style="left: {eval_pct}%; width: 2px; background-color: red;"></div>
                </div>
                <p><strong>Evaluation:</strong> {eval_text} (depth: {depth})</p>
                <p><strong>Best Move:</strong> {best_move}</p>
            </div>
        """)
    
    @output
    @render.ui
    def eval_b():
        data = eval_b_data()
        if not data:
            return ui.div({"class": "loading"}, "Evaluation will appear after analysis")
        
        if "error" in data:
            return ui.div(f"❌ Eval Error: {data['error']}", style="color: red; padding: 10px;")
        
        cp = data.get("pvs", [{}])[0].get("cp")
        if cp is None:
            return ui.div("Evaluation not available", style="padding: 10px;")
        
        # Clamp centipawns and convert to percentage
        clamped_cp = max(-1000, min(1000, cp))
        eval_pct = 50 + (clamped_cp / 20)
        
        eval_text = f"+{cp/100:.2f}" if cp >= 0 else f"{cp/100:.2f}"
        depth = data.get("depth", "?")
        
        # Best move
        best_move = "N/A"
        if data.get("pvs") and data["pvs"][0].get("moves"):
            uci_move = data["pvs"][0]["moves"].split()[0]
            try:
                move = chess.Move.from_uci(uci_move)
                best_move = board_b().san(move)
            except:
                best_move = uci_move
        
        return ui.HTML(f"""
            <div class="metric-card">
                <h5>🤖 Stockfish Cloud Evaluation</h5>
                <div class="eval-bar">
                    <div class="eval-indicator" style="left: {eval_pct}%; width: 2px; background-color: red;"></div>
                </div>
                <p><strong>Evaluation:</strong> {eval_text} (depth: {depth})</p>
                <p><strong>Best Move:</strong> {best_move}</p>
            </div>
        """)
    
    @output
    @render.ui
    def comparison():
        stats_a = stats_a_data()
        stats_b = stats_b_data()
        eval_a = eval_a_data()
        eval_b = eval_b_data()
        
        if not stats_a or not stats_b:
            return ui.div(
                {"class": "loading"},
                "Analyze both openings to see comparison"
            )
        
        if "error" in stats_a or "error" in stats_b:
            return ui.div("Complete both analyses to compare", style="padding: 10px;")
        
        # Calculate win rates
        total_a = stats_a.get("white", 0) + stats_a.get("draws", 0) + stats_a.get("black", 0)
        total_b = stats_b.get("white", 0) + stats_b.get("draws", 0) + stats_b.get("black", 0)
        
        if total_a == 0 or total_b == 0:
            return ui.div("Insufficient data for comparison", style="padding: 10px;")
        
        white_win_a = stats_a.get("white", 0) / total_a * 100
        white_win_b = stats_b.get("white", 0) / total_b * 100
        
        # Evaluations
        cp_a = eval_a.get("pvs", [{}])[0].get("cp", 0) if eval_a else 0
        cp_b = eval_b.get("pvs", [{}])[0].get("cp", 0) if eval_b else 0
        
        win_rate_class_a = "better" if white_win_a > white_win_b else "worse"
        win_rate_class_b = "better" if white_win_b > white_win_a else "worse"
        eval_class_a = "better" if cp_a > cp_b else "worse"
        eval_class_b = "better" if cp_b > cp_a else "worse"
        
        return ui.HTML(f"""
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div class="metric-card {win_rate_class_a}">
                    <h5>Opening A: White Win Rate</h5>
                    <h3>{white_win_a:.1f}%</h3>
                    <small>{total_a:,} games</small>
                </div>
                <div class="metric-card {win_rate_class_b}">
                    <h5>Opening B: White Win Rate</h5>
                    <h3>{white_win_b:.1f}%</h3>
                    <small>{total_b:,} games</small>
                </div>
                <div class="metric-card {eval_class_a}">
                    <h5>Opening A: Evaluation</h5>
                    <h3>{cp_a/100:+.2f}</h3>
                </div>
                <div class="metric-card {eval_class_b}">
                    <h5>Opening B: Evaluation</h5>
                    <h3>{cp_b/100:+.2f}</h3>
                </div>
            </div>
        """)


app = App(app_ui, server)