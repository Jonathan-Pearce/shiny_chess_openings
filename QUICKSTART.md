# Quick Start Guide

## Getting Your Chess Opening Explorer Live in 5 Minutes

### Step 1: Enable GitHub Pages

1. Go to your repository on GitHub: https://github.com/Jonathan-Pearce/shiny_chess_openings
2. Click on **Settings** (top menu)
3. Scroll down to **Pages** in the left sidebar
4. Under **Build and deployment**:
   - Source: Select **GitHub Actions**
5. Click **Save**

### Step 2: Push Your Code (if not already done)

```bash
git add .
git commit -m "Add Chess Opening Explorer with Shinylive"
git push origin main
```

### Step 3: Wait for Deployment

1. Go to the **Actions** tab in your repository
2. You should see a workflow running: "Deploy Shinylive to GitHub Pages"
3. Wait for it to complete (usually 2-3 minutes)
4. Once complete, a green checkmark will appear

### Step 4: Access Your Site

Your site will be live at:
```
https://jonathan-pearce.github.io/shiny_chess_openings/
```

## Troubleshooting

### Workflow Not Running?

- Make sure you've enabled GitHub Actions in repository settings
- Check that the `.github/workflows/deploy.yml` file exists
- Try manually triggering: Actions → Deploy Shinylive → Run workflow

### 404 Error on Site?

- Wait a few more minutes (can take up to 10 minutes for first deployment)
- Check that GitHub Pages is enabled with "GitHub Actions" as source
- Verify the workflow completed successfully in the Actions tab

### Local Testing

Want to test before deploying?

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
shiny run app.py

# Open browser to http://localhost:8000
```

## Using the App

1. **Enter moves** in standard notation: `e4 e5 Nf3 Nc6 Bc4`
2. **Click "Analyze Opening"** to update the board
3. Explore different tabs:
   - **Board**: See the current position
   - **Opening Statistics**: View data from millions of games
   - **Position Evaluation**: Get material assessment
   - **Popular Next Moves**: See what strong players play

## Next Steps

- Customize the app in `app.py`
- Add more features
- Share your site with chess friends!

## Support

For issues or questions:
- Check the main [README.md](README.md)
- Open an issue on GitHub
- Review Shiny documentation: https://shiny.posit.co/py/
