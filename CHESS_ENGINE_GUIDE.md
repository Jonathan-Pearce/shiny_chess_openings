# Adding Chess Engine Support to Your Shinylive App

## Overview

Yes! You can absolutely use chess engines in your browser-based Shinylive app. Here are your options:

## Option 1: Stockfish.js (Browser-Based Engine) ⭐ Recommended

**Stockfish.js** is a JavaScript/WebAssembly port of the Stockfish engine that runs entirely in the browser.

### Advantages:
- ✅ Runs completely client-side (no server needed)
- ✅ Works perfectly with Shinylive/GitHub Pages
- ✅ Real Stockfish engine (same as desktop version)
- ✅ No API calls or rate limits
- ✅ Fast and accurate

### Implementation:

I've created an enhanced version with Stockfish.js: **[app_with_stockfish.py](app_with_stockfish.py)**

#### Key Features Added:
1. **Stockfish.js Integration**: Loads the engine via CDN
2. **JavaScript Bridge**: Python ↔ JavaScript communication
3. **Real Engine Analysis**:
   - Evaluation scores (in pawns/centipawns)
   - Best move suggestions
   - Principal variation (sequence of best moves)
   - Configurable search depth

#### To Use This Version:

```bash
# Replace your current app.py
cp app_with_stockfish.py app.py

# Or run directly
shiny run app_with_stockfish.py
```

Then deploy as usual - Stockfish will load from CDN and run in the browser!

---

## Option 2: Lichess Cloud Evaluation API

Use Lichess's free cloud evaluation service.

### Advantages:
- ✅ No client-side processing (faster on slow devices)
- ✅ Simple API calls
- ✅ Already uses Lichess API for openings

### Implementation:

```python
def get_lichess_evaluation(fen):
    """Get position evaluation from Lichess cloud"""
    try:
        response = requests.get(
            "https://lichess.org/api/cloud-eval",
            params={"fen": fen, "multiPv": 3},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            # data contains: eval score, best moves, depth, etc.
            return data
    except:
        return None
```

### Limitations:
- ⚠️ Only evaluates positions that have been analyzed before
- ⚠️ May not have analysis for rare positions

---

## Option 3: chess-wasm (Lightweight Alternative)

A smaller WebAssembly chess engine optimized for browser use.

### Installation:
```html
<script src="https://unpkg.com/chess-wasm@1.0.0/dist/chess.js"></script>
```

---

## Comparison Table

| Feature | Stockfish.js | Lichess Cloud | chess-wasm |
|---------|-------------|---------------|------------|
| Runs in Browser | ✅ Yes | ❌ No (API) | ✅ Yes |
| Strength | 🔥 Very Strong | 🔥 Very Strong | ⚡ Good |
| Speed | ⚡ Fast | 🚀 Instant* | 🚀 Very Fast |
| Offline Support | ✅ Yes | ❌ No | ✅ Yes |
| Setup Complexity | Easy | Very Easy | Easy |
| File Size | ~500KB | None | ~100KB |

*Only if position is cached

---

## Recommendation for Your Project

**Use Stockfish.js** (already implemented in `app_with_stockfish.py`) because:

1. ✅ Perfect fit for Shinylive/GitHub Pages
2. ✅ No server or API dependencies
3. ✅ Professional-grade engine (same as chess.com)
4. ✅ Works offline once loaded
5. ✅ Easy to integrate with Shiny

---

## How to Switch to Stockfish Version

### Quick Switch:
```bash
# Backup current version
mv app.py app_simple.py

# Use Stockfish version
mv app_with_stockfish.py app.py

# Commit and deploy
git add app.py
git commit -m "Add Stockfish.js engine support"
git push origin main
```

### Test Locally First:
```bash
shiny run app_with_stockfish.py
```

Visit http://localhost:8000, enter some moves, and click "Run Stockfish"!

---

## Advanced Customization

### Adjust Engine Strength:

In the JavaScript code, change the skill level (0-20):
```javascript
stockfish.postMessage("setoption name Skill Level value 20"); // Max strength
stockfish.postMessage("setoption name Skill Level value 10"); // Intermediate
```

### Adjust Search Depth:

```javascript
stockfish.postMessage("go depth 15");  // Deeper = slower but stronger
stockfish.postMessage("go depth 10");  // Faster but less accurate
```

### Add Time-Based Search:

```javascript
stockfish.postMessage("go movetime 3000"); // Analyze for 3 seconds
```

---

## Performance Notes

- **First Load**: Takes 1-2 seconds to initialize Stockfish
- **Analysis Time**: 1-5 seconds depending on depth and position complexity
- **Mobile Performance**: Works but slower on mobile devices
- **Memory Usage**: ~50-100MB while analyzing

---

## Troubleshooting

### "Stockfish not initialized"
- Wait 2-3 seconds after page loads before clicking "Run Stockfish"
- Check browser console for JavaScript errors

### "Evaluation stuck on 'Analyzing...'"
- Try a shallower depth (change `depth 15` to `depth 10`)
- Check if position is a checkmate (analysis completes instantly)

### Slow Performance
- Reduce search depth
- Use Lichess Cloud API instead for slower devices

---

## Want Both Options?

You could offer users a choice:
- "Quick Analysis" → Lichess Cloud API (instant but limited)
- "Deep Analysis" → Stockfish.js (slower but always available)

Let me know if you want me to implement this dual approach!
