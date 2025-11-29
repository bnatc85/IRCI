# IRCI Deployment Guide

## Streamlit Cloud Configuration

The IRCI app is deployed on Streamlit Cloud at: https://ircibeta.streamlit.app/

### Important: Branch Configuration

**Streamlit Cloud is configured to deploy from the `irci-bridge` branch, NOT `main`.**

This means:
- All development work happens on `main` branch
- Changes must be merged to `irci-bridge` to appear on the live app

### How to Deploy Changes

After making changes on `main`, run these commands to deploy:

```bash
# 1. Make sure you're on main and changes are committed
git checkout main
git status  # Should show "nothing to commit, working tree clean"

# 2. Switch to irci-bridge and merge changes from main
git checkout irci-bridge
git merge main -m "Merge main into irci-bridge - [describe changes]"

# 3. Push to deploy
git push origin irci-bridge

# 4. Switch back to main for continued development
git checkout main
```

### Quick One-Liner to Deploy

```bash
git checkout irci-bridge && git merge main -m "Deploy latest changes" && git push origin irci-bridge && git checkout main
```

### If Streamlit Cloud Doesn't Update

1. Go to https://share.streamlit.io/
2. Find the ircibeta app
3. Click the ⋮ menu → "Reboot app"

Or from the app itself:
1. Go to https://ircibeta.streamlit.app/
2. Click ☰ menu (bottom right)
3. Click "Reboot app"

### Streamlit Cloud Settings

To check or change deployment settings:
1. Go to https://share.streamlit.io/
2. Click on the ircibeta app
3. Click "Settings" (gear icon)

Current settings should be:
- **Repository**: bnatc85/IRCI
- **Branch**: irci-bridge
- **Main file path**: app.py

### Environment Variables

Streamlit Cloud uses secrets configured in the dashboard, NOT the local `.env` file.

To update secrets:
1. Go to Streamlit Cloud dashboard
2. Click on app → Settings → Secrets
3. Add secrets in TOML format

### Branches Overview

| Branch | Purpose |
|--------|---------|
| `main` | Active development, all new code goes here |
| `irci-bridge` | Production deployment branch for Streamlit Cloud |
| `feature/*` | Feature branches for larger changes |

