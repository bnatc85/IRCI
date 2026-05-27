# IRCI Deployment Guide

## Railway

The IRCI app is deployed on Railway at: https://irci.up.railway.app/

Railway auto-deploys from the `main` branch of `bnatc85/IRCI` on every push.

### Configuration

| File | Purpose |
|------|---------|
| `Procfile` | `web: streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true` |
| `.python-version` | Pins Python to 3.12 |
| `requirements.txt` | Installed by Railway's Python builder |

### Deploying Changes

```bash
git push origin main
```

Railway rebuilds within ~1–2 minutes. Confirm by checking the `last-modified` response header at https://irci.up.railway.app/ or the deploy log in the Railway dashboard.

### Health Check

```bash
curl -I https://irci.up.railway.app/                  # expect HTTP 200
curl https://irci.up.railway.app/_stcore/health       # Streamlit healthz
```

### Environment Variables / Secrets

Set in the Railway dashboard under **Variables**, not via local `.env`. The app reads them through standard `os.environ` lookups in `irci/config.py`.

### Reboot

Railway dashboard → service → **Deployments** → ⋮ on latest → **Redeploy**.

### Branches Overview

| Branch | Purpose |
|--------|---------|
| `main` | Active development; Railway deploys from here |
| `feature/*` | Feature branches for larger changes |

The `irci-bridge` branch is a legacy Streamlit Cloud deploy branch and is no longer used.
