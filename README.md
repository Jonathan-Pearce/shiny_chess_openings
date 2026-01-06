# Chess Opening Explorer

An interactive web application for exploring chess openings with statistics from the Lichess database and position evaluation.

## Features

- 🎯 **Interactive Chess Board**: Visualize chess positions with a beautiful SVG chess board
- 📊 **Opening Statistics**: Get real-time statistics from the Lichess database (millions of games)
- 📈 **Position Evaluation**: Basic material evaluation and position assessment
- 🔍 **Popular Next Moves**: Discover the most played moves in any position
- 🚀 **Runs in Browser**: Powered by Shinylive - no server required!

## Live Demo

Visit the live application at: `https://jonathan-pearce.github.io/shiny_chess_openings/`

## How to Use

1. **Enter Moves**: Type chess moves in standard algebraic notation (e.g., `e4 e5 Nf3 Nc6`)
2. **Click Analyze**: Press the "Analyze Opening" button to update the board
3. **Quick Examples**: Use the quick start buttons for popular openings:
   - Italian Game
   - Sicilian Defense
   - French Defense
4. **Explore Tabs**:
   - **Board**: View the current position and move history
   - **Opening Statistics**: See win/draw/loss statistics from Lichess database
   - **Position Evaluation**: Get a basic material evaluation
   - **Popular Next Moves**: Discover what strong players typically play next

## Local Development

### Prerequisites

- Python 3.11 or higher
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/Jonathan-Pearce/shiny_chess_openings.git
cd shiny_chess_openings

# Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running Locally

```bash
# Run the Shiny app
shiny run app.py --reload
```

Then open your browser to `http://localhost:8000`

### Testing with Shinylive

To test the deployed version locally:

```bash
# Install shinylive
pip install shinylive

# Export to static site
shinylive export . _site

# Serve the site
python -m http.server --directory _site 8080
```

Then open `http://localhost:8080` in your browser.

## Deployment

This project is automatically deployed to GitHub Pages using GitHub Actions whenever changes are pushed to the `main` branch.

### Enable GitHub Pages

1. Go to your repository settings
2. Navigate to **Pages** section
3. Under **Source**, select "GitHub Actions"
4. The workflow will automatically build and deploy your site

### Manual Deployment

You can also manually trigger the deployment:

1. Go to the **Actions** tab in your repository
2. Select the "Deploy Shinylive to GitHub Pages" workflow
3. Click "Run workflow"

## Technical Details

### Technologies Used

- **Shiny for Python**: Web framework for interactive applications
- **Shinylive**: Converts Shiny apps to static sites that run in the browser
- **python-chess**: Chess library for move validation and board representation
- **Lichess API**: Source of opening statistics from millions of games

### How It Works

1. The Shiny app is written in Python ([app.py](app.py))
2. Shinylive converts it to WebAssembly that runs entirely in the browser
3. GitHub Actions automatically builds and deploys to GitHub Pages
4. No backend server needed - everything runs client-side!

### API Usage

The app uses the Lichess Opening Explorer API:
- Endpoint: `https://explorer.lichess.ovh/lichess`
- Documentation: https://lichess.org/api#tag/opening-explorer
- No authentication required for public data

### Limitations

- **Stockfish Evaluation**: Full Stockfish engine evaluation requires server-side processing. The current implementation provides basic material evaluation instead.
- **Browser Performance**: Running in the browser via WebAssembly may be slower than native Python for complex operations.
- **API Rate Limits**: The Lichess API may rate limit excessive requests.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Acknowledgments

- [Lichess.org](https://lichess.org) for providing the opening database API
- [Shiny for Python](https://shiny.posit.co/py/) for the web framework
- [python-chess](https://python-chess.readthedocs.io/) for chess logic
- [Shinylive](https://shiny.posit.co/py/docs/shinylive.html) for enabling browser-based deployment