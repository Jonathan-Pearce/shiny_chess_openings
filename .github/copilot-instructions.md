# Chess Opening Explorer - GitHub Copilot Instructions

## Project Overview

This is a **Chess Opening A/B Testing Tool** built as a static GitHub Pages website using **Shiny Live** (Python). The application allows users to compare two chess openings side-by-side, displaying comprehensive statistics and evaluations for each.

**Live Site**: https://jonathan-pearce.github.io/shiny_chess_openings/

## Core Technology Stack

- **Framework**: Shiny for Python with Shinylive (browser-based, no server)
- **Language**: Python only
- **Deployment**: GitHub Pages (static site)
- **Chess Library**: python-chess
- **APIs**: 
  - Lichess Opening Explorer API: https://lichess.org/api#tag/opening-explorer/GET/lichess
  - Lichess Cloud Evaluation API: https://lichess.org/api#tag/Analysis/get-cloud-eval

## Application Architecture

### Single-Page Layout (No Tabs)
The application should be a **single scrollable page** with:

1. **Welcome Section** (top of page or modal popup):
   - Brief introduction explaining the tool's purpose
   - How to use the comparison feature
   - What metrics are being compared

2. **Two-Column Comparison Layout**:
   - **Left Column**: Opening A
   - **Right Column**: Opening B
   - Each column should have identical structure for easy comparison

### Each Column Should Include:

1. **Opening Input Section**:
   - Text input for moves in algebraic notation (e.g., "e4 e5 Nf3 Nc6")
   - Interactive chess board for visual move entry (using chessboard.js or similar)
   - Quick preset buttons for popular openings

2. **Chess Board Display**:
   - Visual representation of the current position
   - Move history displayed below board

3. **Opening Statistics** (from Lichess API):
   - Total games analyzed
   - Win/Draw/Loss percentages (White perspective)
   - Win/Draw/Loss percentages (Black perspective)
   - Average rating of games
   - Most popular next moves with statistics

4. **Position Evaluation** (from Lichess Cloud Eval API):
   - Stockfish cloud evaluation (centipawn score)
   - Best move suggestion
   - Evaluation depth
   - Visual evaluation bar

5. **Comparison Metrics**:
   - Highlight which opening performs better in key metrics
   - Win rate differential
   - Evaluation score differential

## Key Design Principles

### Code Standards
- **Python-only**: All logic in Python, no backend required
- **Shinylive compatible**: Code must run entirely in browser
- **Async API calls**: Use asyncio for non-blocking Lichess API requests
- **Error handling**: Gracefully handle invalid moves, API failures, network issues
- **Responsive design**: CSS should adapt to different screen sizes

### UI/UX Guidelines
- **Side-by-side comparison**: Keep both openings visible simultaneously
- **Visual hierarchy**: Important metrics (win rates, evaluations) should be prominent
- **Color coding**: Use green/red for better/worse metrics
- **Mobile-friendly**: Layout should stack vertically on mobile devices
- **Loading indicators**: Show progress when fetching API data

### API Integration

#### Lichess Opening Explorer API
```python
# Endpoint: https://explorer.lichess.ovh/lichess
# Parameters:
# - fen: Position in FEN notation
# - play: Move sequence (e.g., "e4,e5,Nf3")
# - ratings: [1600,1800,2000,2200,2500] (rating categories)
# - speeds: [bullet,blitz,rapid,classical] (time controls)
# - topGames: 10 (number of top games to return)
```

#### Lichess Cloud Evaluation API
```python
# Endpoint: https://lichess.org/api/cloud-eval
# Parameters:
# - fen: Position in FEN notation
# - multiPv: Number of variations (default 1)
# Response includes: cp (centipawns), depth, pvs (principal variations)
```

### File Structure
```
/
├── app.py                          # Main Shiny application
├── requirements.txt                # Python dependencies
├── README.md                       # Project documentation
├── shinylive/                      # Generated static site (gitignored)
└── .github/
    └── copilot-instructions.md     # This file
```

## Implementation Guidelines

### When writing Python code:
1. Use `shiny` reactive patterns correctly:
   - `@reactive.Calc` for computed values
   - `@reactive.Effect` for side effects
   - `@reactive.event` for button clicks
   - `@render.ui` for dynamic UI elements

2. Structure layout using `ui.layout_columns()` for side-by-side comparison

3. Implement proper error handling for:
   - Invalid chess moves
   - API request failures
   - Malformed FEN strings
   - Network timeouts

4. Cache API responses where appropriate to reduce API calls

### Chess Board Integration:
- Use `chess` library for move validation and FEN generation
- Integrate chessboard.js via CDN for interactive board
- Sync Python chess state with JavaScript board state
- Support drag-and-drop move entry

### Styling:
- Use inline CSS or `<style>` tags in Shiny UI
- Bootstrap classes (available in Shiny by default)
- Responsive grid system: `col-md-6` for two columns on desktop
- Custom CSS for evaluation bars, metric highlights

### Example Code Patterns:

#### Two-Column Layout
```python
ui.layout_columns(
    # Left column - Opening A
    ui.card(
        ui.card_header("Opening A"),
        # ... opening A content
    ),
    # Right column - Opening B
    ui.card(
        ui.card_header("Opening B"),
        # ... opening B content
    ),
    col_widths=[6, 6]
)
```

#### API Call with Error Handling
```python
@reactive.Calc
async def fetch_opening_stats():
    try:
        response = requests.get(
            "https://explorer.lichess.ovh/lichess",
            params={"fen": fen(), "speeds": "blitz,rapid"},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}
```

## Testing Checklist

Before committing code, verify:
- [ ] Moves can be entered via text input
- [ ] Interactive board allows piece movement
- [ ] Both columns update independently
- [ ] Lichess API returns valid data
- [ ] Cloud evaluation displays correctly
- [ ] Welcome message displays on first load
- [ ] Responsive layout works on mobile
- [ ] Error messages display for invalid input
- [ ] Loading states show during API calls
- [ ] Comparison highlights work correctly

## Deployment

1. **Build Shinylive site**: 
   ```bash
   shinylive export . shinylive
   ```

2. **Deploy to GitHub Pages**:
   - Push to `main` branch
   - GitHub Actions deploys `shinylive/` directory

3. **Test live site**: Visit https://jonathan-pearce.github.io/shiny_chess_openings/

## Common Tasks

### Adding a new preset opening:
Add to preset buttons dictionary with move sequence in algebraic notation

### Modifying API parameters:
Update rating ranges, time controls, or depth in API request functions

### Changing evaluation display:
Modify the centipawn-to-visual conversion in evaluation rendering

### Adding new metrics:
Fetch additional data from Lichess API and add to comparison cards

## Resources

- Shiny for Python: https://shiny.posit.co/py/
- Shinylive Documentation: https://shiny.posit.co/py/docs/shinylive.html
- python-chess: https://python-chess.readthedocs.io/
- Lichess API: https://lichess.org/api
- chessboard.js: https://chessboardjs.com/

## Important Notes

- **No server-side code**: Everything runs in the browser via Pyodide
- **No file I/O**: Cannot read/write local files in Shinylive
- **Limited packages**: Only packages available in Pyodide can be used
- **CORS-friendly APIs**: Must use APIs that allow cross-origin requests (Lichess does)
- **Performance**: Keep computations lightweight for browser execution

## Code Style

- Follow PEP 8 conventions
- Use type hints where applicable
- Add docstrings to complex functions
- Comment API integrations clearly
- Keep functions focused and modular
- Prefer readability over cleverness
