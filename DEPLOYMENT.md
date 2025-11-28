# 🚀 IRCI Deployment Guide - Streamlit Community Cloud

This guide will help you deploy the IRCI Analysis Platform to Streamlit Community Cloud.

## Prerequisites

- GitHub account
- Streamlit Community Cloud account (sign up at https://share.streamlit.io)
- API keys for:
  - Financial Modeling Prep (FMP)
  - OpenAI (for AI Assistant feature)
  - Alpha Vantage (optional)

## Step 1: Push Code to GitHub

Your code is already in the `irci-bridge` branch. Push it to GitHub:

```bash
git push origin irci-bridge
```

Or if you want to deploy from main:
```bash
git checkout main
git merge irci-bridge
git push origin main
```

## Step 2: Sign Up for Streamlit Community Cloud

1. Go to https://share.streamlit.io
2. Sign in with your GitHub account
3. Authorize Streamlit to access your repositories

## Step 3: Deploy Your App

1. Click **"New app"** button
2. Fill in the deployment settings:
   - **Repository**: Select your IRCI repository
   - **Branch**: `irci-bridge` (or `main` if you merged)
   - **Main file path**: `app.py`
   - **App URL** (optional): Choose a custom subdomain

3. Click **"Deploy"**

## Step 4: Configure Secrets

After deployment (or before), add your API keys and access code:

1. In the Streamlit Cloud dashboard, go to your app
2. Click the **"⚙️ Settings"** button
3. Go to **"Secrets"** section
4. Copy the contents of `.streamlit/secrets.toml.example`
5. Paste into the secrets editor
6. Replace the placeholder values with your actual keys:

```toml
# Financial Modeling Prep API Key
FMP_API_KEY = "your_actual_fmp_key"

# OpenAI API Key (for AI Assistant)
OPENAI_API_KEY = "your_actual_openai_key"

# Alpha Vantage API Key (optional)
ALPHA_VANTAGE_API_KEY = "your_actual_alpha_vantage_key"

# Access Code (change to your custom code)
ACCESS_CODE = "Melissa2019"
```

7. Click **"Save"**

## Step 5: Your App is Live! 🎉

Your app will be available at:
```
https://your-app-name.streamlit.app
```

## Configuration Files

- **`.streamlit/config.toml`**: Production settings (already configured)
- **`.streamlit/secrets.toml.example`**: Template for secrets (DO NOT commit actual secrets.toml)
- **`requirements.txt`**: Python dependencies (already configured)

## Updating Your Deployed App

Streamlit Cloud automatically redeploys when you push to your connected branch:

```bash
git add .
git commit -m "Update app"
git push origin irci-bridge
```

Your app will rebuild and redeploy automatically!

## Troubleshooting

### App Won't Start
- Check the logs in Streamlit Cloud dashboard
- Verify all secrets are set correctly
- Ensure requirements.txt includes all dependencies

### "Module not found" Errors
- Add missing packages to requirements.txt
- Push changes to trigger rebuild

### API Errors
- Verify API keys in secrets are correct
- Check API key quotas/limits

### Access Code Not Working
- Verify ACCESS_CODE is set in secrets
- Check for typos (case-sensitive)

## Managing Resources

**Free Tier Limits:**
- 1 GB RAM per app
- Apps sleep after inactivity
- Wake up automatically when accessed

**Tips to optimize:**
- Use `@st.cache_data` for expensive operations
- Limit data fetching where possible
- Consider pagination for large datasets

## Security Notes

- ✅ Access code provides basic protection
- ✅ API keys stored securely in Streamlit secrets
- ✅ HTTPS enabled by default
- ⚠️ For production use, consider proper authentication

## Support

- Streamlit Cloud Docs: https://docs.streamlit.io/streamlit-community-cloud
- IRCI Repository: [Your GitHub URL]
- Questions? Check the Streamlit Community Forum

---

**Happy Deploying! 🚀**
