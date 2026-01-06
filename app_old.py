from shiny import App, render, ui, reactive
import chess
import chess.svg
import requests
from pathlib import Path

app_ui = ui.page_fluid(
    ui.panel_title("Chess Opening Explorer"),
    ui.markdown(
        """
        Enter chess moves in standard algebraic notation (e.g., e4 e5 Nf3 Nc6) 
        to explore opening statistics and get **real Stockfish evaluation** via Lichess Cloud Analysis.
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
                "Position Evaluation",
                ui.output_ui("evaluation")
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
                # Invalid move, keep previous board state
                pass
    
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
        
        # Get FEN for API request
        fen = board.fen()
        
        try:
            # Call Lichess API
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
    def evaluation():
        board = board_state.get()
        fen = board.fen()
        
        # Check game state first
        if board.is_checkmate():
            result = "Checkmate! " + ("Black" if board.turn else "White") + " wins."
            game_status = "Game Over"
        elif board.is_stalemate():
            result = "Stalemate - Draw"
            game_status = "Game Over"
        elif board.is_insufficient_material():
            result = "Insufficient material - Draw"
            game_status = "Game Over"
        else:
            result = "Game in progress"
            game_status = "Active"
        
        # Try to get Lichess Cloud Evaluation
        cloud_eval = None
        best_moves = []
        
        try:
            response = requests.get(
                "https://lichess.org/api/cloud-eval",
                params={
                    "fen": fen,
                    "multiPv": 3  # Get top 3 moves
                },
                timeout=5
            )
            
            if response.status_code == 200:
                cloud_eval = response.json()
        except:
            pass
        
        # Calculate material as fallback
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
        
        # Build the UI
        elements = [
            ui.h4("Position Evaluation"),
            ui.p(ui.strong("Status: "), result),
            ui.p(ui.strong("Game State: "), game_status),
            ui.hr()
        ]
        
        # Display Lichess Cloud Evaluation if available
        if cloud_eval and "pvs" in cloud_eval:
            elements.append(ui.h5("🔥 Lichess Cloud Analysis"))
            
            pv_data = cloud_eval["pvs"][0]  # Best line
            
            # Parse evaluation
            if "cp" in pv_data:
                cp = pv_data["cp"]
                eval_score = f"{cp / 100:+.2f}"
                eval_pawns = cp / 100
                
                if eval_pawns > 2:
                    assessment = "White has a significant advantage"
                elif eval_pawns > 0.5:
                    assessment = "White is slightly better"
                elif eval_pawns < -2:
                    assessment = "Black has a significant advantage"
                elif eval_pawns < -0.5:
                    assessment = "Black is slightly better"
                else:
                    assessment = "Position is approximately equal"
            elif "mate" in pv_data:
                mate_in = pv_data["mate"]
                if mate_in > 0:
                    eval_score = f"M{mate_in}"
                    assessment = f"White has mate in {mate_in}"
                else:
                    eval_score = f"-M{abs(mate_in)}"
                    assessment = f"Black has mate in {abs(mate_in)}"
            else:
                eval_score = "?"
                assessment = "Evaluation unavailable"
            
            elements.extend([
                ui.p(ui.strong("Evaluation: "), eval_score),
                ui.p(ui.strong("Assessment: "), assessment),
                ui.p(ui.strong("Analysis Depth: "), str(cloud_eval.get("depth", "?"))),
            ])
            
            # Show top moves
            if len(cloud_eval["pvs"]) > 0:
                elements.append(ui.h5("Best Moves:"))
                
                for i, pv in enumerate(cloud_eval["pvs"][:3], 1):
                    moves = pv.get("moves", "").split()[:3]  # First 3 moves
                    
                    # Convert UCI to SAN
                    temp_board = board.copy()
                    san_moves = []
                    for uci_move in moves:
                        try:
                            move = chess.Move.from_uci(uci_move)
                            san_moves.append(temp_board.san(move))
                            temp_board.push(move)
                        except:
                            break
                    
                    move_line = " ".join(san_moves)
                    
                    if "cp" in pv:
                        move_eval = f"{pv['cp'] / 100:+.2f}"
                    elif "mate" in pv:
                        mate_in = pv["mate"]
                        move_eval = f"M{mate_in}" if mate_in > 0 else f"-M{abs(mate_in)}"
                    else:
                        move_eval = "?"
                    
                    elements.append(
                        ui.p(f"{i}. {move_line} ({move_eval})")
                    )
            
            elements.append(
                ui.p(
                    ui.em("Source: Lichess Cloud Analysis powered by Stockfish"),
                    style="font-size: 0.9em; color: #666;"
                )
            )
        else:
            # Fallback to material evaluation
            elements.append(ui.h5("📊 Material Evaluation"))
            
            if game_status == "Game Over":
                eval_score = "Game Over"
            else:
                eval_score = f"{material_diff:+.1f}"
            
            if material_diff > 3:
                assessment = "White has a significant material advantage"
            elif material_diff < -3:
                assessment = "Black has a significant material advantage"
            elif material_diff > 0:
                assessment = "White has a slight material advantage"
            elif material_diff < 0:
                assessment = "Black has a slight material advantage"
            else:
                assessment = "Material is equal"
            
            elements.extend([
                ui.p(ui.strong("Material Balance: "), eval_score + " pawns"),
                ui.p(ui.strong("Assessment: "), assessment),
                ui.hr(),
                ui.h5("Piece Count:"),
                ui.p(f"White: {white_material} points"),
                ui.p(f"Black: {black_material} points"),
                ui.hr(),
                ui.p(
                    ui.em("⚠️ Lichess Cloud Analysis not available for this position. "),
                    ui.em("Showing material count instead."),
                    style="font-size: 0.9em; color: #666;"
                )
            ])
        
        return ui.div(*elements)
    
    @output
    @render.ui
    def next_moves():
        board = board_state.get()
        
        if board.is_game_over():
            return ui.div(
                ui.h4("Game Over"),
                ui.p("No more moves available.")
            )
        
        # Get FEN for API request
        fen = board.fen()
        
        try:
            # Call Lichess API for popular moves
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
            
            # Sort by number of games played
            moves_data.sort(key=lambda x: x.get("white", 0) + x.get("draws", 0) + x.get("black", 0), reverse=True)
            
            move_elements = [ui.h4("Popular Next Moves (from Lichess Database)")]
            
            for i, move_info in enumerate(moves_data[:10], 1):  # Top 10 moves
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
