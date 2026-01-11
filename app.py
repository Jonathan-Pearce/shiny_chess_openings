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
    max-width: 100%;
    margin: 10px auto;
    width: 100%;
}
.board-container > div {
    width: 100% !important;
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
                window.mainBoard = Chessboard('mainBoard', {
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
            } else {
                console.error('✗ mainBoard element not found');
            }
        } catch(e) {
            console.error('✗ Error initializing mainBoard:', e);
        }
    }, 1000);
});

// Handle custom messages from server to update board position
if (typeof Shiny !== 'undefined') {
    Shiny.addCustomMessageHandler('update_board', function(message) {
        console.log('Update board message received:', message);
        if (window.mainBoard) {
            try {
                window.mainBoard.position(message.fen);
                console.log('Board position updated');
            } catch(e) {
                console.error('Error updating board:', e);
            }
        }
    });
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
    
    # Three-column layout
    ui.layout_columns(
        # Column 1: Current Position
        ui.card(
            ui.card_header(ui.h4("Current Position", style="margin: 0; font-size: 1.1rem;")),
            
            # Chess board
            ui.div(
                {"class": "board-container"},
                ui.HTML('<div id="mainBoard" style="width: 100%; max-width: 100%; height: auto;"></div>'),
            ),
            
            # Move input below board
            ui.input_text("moves", "Moves:", 
                         placeholder="e.g., e4 e5 Nf3 Nc6",
                         width="100%"),
            
            # Action buttons
            ui.div(
                ui.input_action_button("analyze_position", "Analyze", class_="btn-primary", style="width: 48%; margin-right: 2%;"),
                ui.input_action_button("reset_board", "Reset", class_="btn-secondary", style="width: 48%;"),
                style="margin-top: 10px; margin-bottom: 15px;"
            ),
            
            # Position summary
            ui.output_ui("position_summary"),
        ),
        
        # Column 2: Candidate Move A
        ui.card(
            ui.card_header(ui.h4("Candidate Move A", style="margin: 0; font-size: 1.1rem;")),
            ui.output_ui("move_a_selector"),
            ui.output_ui("move_a_details"),
        ),
        
        # Column 3: Candidate Move B
        ui.card(
            ui.card_header(ui.h4("Candidate Move B", style="margin: 0; font-size: 1.1rem;")),
            ui.output_ui("move_b_selector"),
            ui.output_ui("move_b_details"),
        ),
        col_widths=[4, 4, 4],
    ),
)


def server(input, output, session):
    # Reactive values for main board state
    main_board = reactive.Value(chess.Board())
    
    # Reactive values for current position data
    position_stats = reactive.Value({})
    position_eval = reactive.Value({})
    
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
            ui.h3("♟️ Chess Position Analyzer"),
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
        move_a_stats.set({})
        move_a_eval.set({})
        move_b_stats.set({})
        move_b_eval.set({})
    
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
            
            # Fetch stats and evaluation for current position only
            fen = new_board.fen()
            stats_task = fetch_lichess_stats(fen)
            eval_task = fetch_cloud_eval(fen)
            
            stats, evaluation = await asyncio.gather(stats_task, eval_task)
            position_stats.set(stats)
            position_eval.set(evaluation)
            
            # Clear previous move selections
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
        
        # Determine side to move
        side_to_move = "White to move" if board.turn == chess.WHITE else "Black to move"
        
        # Evaluation
        eval_text = "Not analyzed"
        if evaluation and 'pvs' in evaluation and len(evaluation['pvs']) > 0:
            cp = evaluation['pvs'][0].get('cp')
            if cp is not None:
                eval_text = f"+{cp/100:.2f}" if cp >= 0 else f"{cp/100:.2f}"
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
                    <p><strong>Total Lichess Games:</strong> {total_games:,}</p>
                    <p><strong>Results:</strong></p>
                    <ul style="margin: 5px 0; padding-left: 20px;">
                        <li>White wins: {white_pct}%</li>
                        <li>Draws: {draw_pct}%</li>
                        <li>Black wins: {black_pct}%</li>
                    </ul>
                """
        elif stats and 'error' in stats:
            stats_html = f"<p style='color: red;'>Stats error: {stats['error']}</p>"
        
        return ui.HTML(f"""
            <div class="metric-card" style="height: 100%;">
                <h4>📊 Position Summary</h4>
                <div class="move-history" style="margin-bottom: 15px;">
                    <strong>Moves:</strong> {move_history}
                </div>
                <p><strong>{side_to_move}</strong></p>
                <p><strong>Evaluation:</strong> {eval_text}</p>
                <hr>
                {stats_html}
            </div>
        """)
    
    @output
    @render.ui
    def move_a_selector():
        board = main_board()
        position_st = position_stats()
        
        # Only show selector if position has been analyzed
        if not position_st:
            return ui.div(
                {"class": "loading"},
                "Analyze position first to see available moves"
            )
        
        if board.is_game_over():
            return ui.div("Game over - no legal moves")
        
        # Get legal moves
        choices = {}
        for move in board.legal_moves:
            san = board.san(move)
            choices[san] = san
        
        return ui.input_select(
            "selected_move_a",
            "Select move:",
            choices=choices,
            selected=None
        )
    
    @output
    @render.ui
    def move_b_selector():
        board = main_board()
        position_st = position_stats()
        
        # Only show selector if position has been analyzed
        if not position_st:
            return ui.div(
                {"class": "loading"},
                "Analyze position first to see available moves"
            )
        
        if board.is_game_over():
            return ui.div("Game over - no legal moves")
        
        # Get legal moves
        choices = {}
        for move in board.legal_moves:
            san = board.san(move)
            choices[san] = san
        
        return ui.input_select(
            "selected_move_b",
            "Select move:",
            choices=choices,
            selected=None
        )
    
    # When move A is selected, fetch its data lazily
    @reactive.Effect
    @reactive.event(input.selected_move_a)
    async def _on_move_a_selected():
        move_san = input.selected_move_a()
        if not move_san:
            return
        
        board = main_board()
        
        # Find the move and get resulting position
        try:
            move = board.parse_san(move_san)
            test_board = board.copy()
            test_board.push(move)
            fen = test_board.fen()
            
            # Fetch evaluation and stats for this position
            eval_task = fetch_cloud_eval(fen)
            stats_task = fetch_lichess_stats(fen)
            
            evaluation, stats = await asyncio.gather(eval_task, stats_task)
            move_a_eval.set(evaluation)
            move_a_stats.set(stats)
        except Exception as e:
            move_a_eval.set({"error": str(e)})
            move_a_stats.set({"error": str(e)})
    
    # When move B is selected, fetch its data lazily
    @reactive.Effect
    @reactive.event(input.selected_move_b)
    async def _on_move_b_selected():
        move_san = input.selected_move_b()
        if not move_san:
            return
        
        board = main_board()
        
        # Find the move and get resulting position
        try:
            move = board.parse_san(move_san)
            test_board = board.copy()
            test_board.push(move)
            fen = test_board.fen()
            
            # Fetch evaluation and stats for this position
            eval_task = fetch_cloud_eval(fen)
            stats_task = fetch_lichess_stats(fen)
            
            evaluation, stats = await asyncio.gather(eval_task, stats_task)
            move_b_eval.set(evaluation)
            move_b_stats.set(stats)
        except Exception as e:
            move_b_eval.set({"error": str(e)})
            move_b_stats.set({"error": str(e)})
    
    @output
    @render.ui
    def move_a_details():
        stats = move_a_stats()
        evaluation = move_a_eval()
        move_san = input.selected_move_a() if hasattr(input, 'selected_move_a') else None
        
        if not move_san:
            return ui.div({"class": "loading"}, "Select a move to see details")
        
        # Get move B data for comparison
        move_b_san = input.selected_move_b() if hasattr(input, 'selected_move_b') else None
        stats_b = move_b_stats()
        eval_b = move_b_eval()
        
        # Evaluation for move A
        cp_a = None
        eval_html = "<p>No evaluation available</p>"
        if evaluation and 'pvs' in evaluation and len(evaluation['pvs']) > 0:
            cp_a = evaluation['pvs'][0].get('cp')
            if cp_a is not None:
                eval_text = f"+{cp_a/100:.2f}" if cp_a >= 0 else f"{cp_a/100:.2f}"
                eval_html = f"<p><strong>Evaluation:</strong> {eval_text}</p>"
        
        # Evaluation for move B (for comparison)
        cp_b = None
        if eval_b and 'pvs' in eval_b and len(eval_b['pvs']) > 0:
            cp_b = eval_b['pvs'][0].get('cp')
        
        # Stats for move A
        total_a = 0
        white_pct_a = 0
        stats_html = "<p>No statistics available</p>"
        if stats and 'error' not in stats:
            total_a = stats.get("white", 0) + stats.get("draws", 0) + stats.get("black", 0)
            if total_a > 0:
                white_pct_a = round(stats.get("white", 0) / total_a * 100, 1)
                draw_pct = round(stats.get("draws", 0) / total_a * 100, 1)
                black_pct = round(stats.get("black", 0) / total_a * 100, 1)
                stats_html = f"""
                    <p><strong>Total Games:</strong> {total_a:,}</p>
                    <ul style="margin: 5px 0; padding-left: 20px;">
                        <li>White: {white_pct_a}%</li>
                        <li>Draw: {draw_pct}%</li>
                        <li>Black: {black_pct}%</li>
                    </ul>
                """
        
        # Stats for move B (for comparison)
        total_b = 0
        white_pct_b = 0
        if stats_b and 'error' not in stats_b:
            total_b = stats_b.get("white", 0) + stats_b.get("draws", 0) + stats_b.get("black", 0)
            if total_b > 0:
                white_pct_b = stats_b.get("white", 0) / total_b * 100
        
        # Comparison section
        comparison_html = ""
        if move_b_san:
            comparison_html = "<hr><h6>Comparison vs Move B:</h6>"
            
            # Eval comparison
            eval_class = ""
            eval_comparison = ""
            if cp_a is not None and cp_b is not None:
                eval_class = "better" if cp_a > cp_b else ("worse" if cp_a < cp_b else "")
                diff = (cp_a - cp_b) / 100
                eval_comparison = f"<div class='metric-card {eval_class}'><strong>Eval:</strong> {diff:+.2f} pawns</div>"
            
            # Win rate comparison
            win_class = ""
            win_comparison = ""
            if total_a > 0 and total_b > 0:
                win_class = "better" if white_pct_a > white_pct_b else ("worse" if white_pct_a < white_pct_b else "")
                diff = white_pct_a - white_pct_b
                win_comparison = f"<div class='metric-card {win_class}'><strong>White Win Rate:</strong> {diff:+.1f}%</div>"
            
            comparison_html += eval_comparison + win_comparison
        
        return ui.HTML(f"""
            <div class="metric-card">
                <h5>{move_san}</h5>
                {eval_html}
                {stats_html}
                {comparison_html}
            </div>
        """)
    
    @output
    @render.ui
    def move_b_details():
        stats = move_b_stats()
        evaluation = move_b_eval()
        move_san = input.selected_move_b() if hasattr(input, 'selected_move_b') else None
        
        if not move_san:
            return ui.div({"class": "loading"}, "Select a move to see details")
        
        # Get move A data for comparison
        move_a_san = input.selected_move_a() if hasattr(input, 'selected_move_a') else None
        stats_a = move_a_stats()
        eval_a = move_a_eval()
        
        # Evaluation for move B
        cp_b = None
        eval_html = "<p>No evaluation available</p>"
        if evaluation and 'pvs' in evaluation and len(evaluation['pvs']) > 0:
            cp_b = evaluation['pvs'][0].get('cp')
            if cp_b is not None:
                eval_text = f"+{cp_b/100:.2f}" if cp_b >= 0 else f"{cp_b/100:.2f}"
                eval_html = f"<p><strong>Evaluation:</strong> {eval_text}</p>"
        
        # Evaluation for move A (for comparison)
        cp_a = None
        if eval_a and 'pvs' in eval_a and len(eval_a['pvs']) > 0:
            cp_a = eval_a['pvs'][0].get('cp')
        
        # Stats for move B
        total_b = 0
        white_pct_b = 0
        stats_html = "<p>No statistics available</p>"
        if stats and 'error' not in stats:
            total_b = stats.get("white", 0) + stats.get("draws", 0) + stats.get("black", 0)
            if total_b > 0:
                white_pct_b = round(stats.get("white", 0) / total_b * 100, 1)
                draw_pct = round(stats.get("draws", 0) / total_b * 100, 1)
                black_pct = round(stats.get("black", 0) / total_b * 100, 1)
                stats_html = f"""
                    <p><strong>Total Games:</strong> {total_b:,}</p>
                    <ul style="margin: 5px 0; padding-left: 20px;">
                        <li>White: {white_pct_b}%</li>
                        <li>Draw: {draw_pct}%</li>
                        <li>Black: {black_pct}%</li>
                    </ul>
                """
        
        # Stats for move A (for comparison)
        total_a = 0
        white_pct_a = 0
        if stats_a and 'error' not in stats_a:
            total_a = stats_a.get("white", 0) + stats_a.get("draws", 0) + stats_a.get("black", 0)
            if total_a > 0:
                white_pct_a = stats_a.get("white", 0) / total_a * 100
        
        # Comparison section
        comparison_html = ""
        if move_a_san:
            comparison_html = "<hr><h6>Comparison vs Move A:</h6>"
            
            # Eval comparison
            eval_class = ""
            eval_comparison = ""
            if cp_b is not None and cp_a is not None:
                eval_class = "better" if cp_b > cp_a else ("worse" if cp_b < cp_a else "")
                diff = (cp_b - cp_a) / 100
                eval_comparison = f"<div class='metric-card {eval_class}'><strong>Eval:</strong> {diff:+.2f} pawns</div>"
            
            # Win rate comparison
            win_class = ""
            win_comparison = ""
            if total_b > 0 and total_a > 0:
                win_class = "better" if white_pct_b > white_pct_a else ("worse" if white_pct_b < white_pct_a else "")
                diff = white_pct_b - white_pct_a
                win_comparison = f"<div class='metric-card {win_class}'><strong>White Win Rate:</strong> {diff:+.1f}%</div>"
            
            comparison_html += eval_comparison + win_comparison
        
        return ui.HTML(f"""
            <div class="metric-card">
                <h5>{move_san}</h5>
                {eval_html}
                {stats_html}
                {comparison_html}
            </div>
        """)
    


app = App(app_ui, server)