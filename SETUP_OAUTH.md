# Google OAuth Setup Guide

This guide will help you set up Google OAuth authentication for the PromptBuilder feature.

## Prerequisites

- A Google Cloud Platform account
- Access to the Google Cloud Console

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note your project ID

## Step 2: Enable Required APIs

1. In your Google Cloud project, go to **APIs & Services > Library**
2. Search for and enable the following APIs:
   - **Google Sheets API**
   - **Google Drive API**
   - **Google+ API** (for user info)

## Step 3: Create OAuth 2.0 Credentials

1. Go to **APIs & Services > Credentials**
2. Click **+ CREATE CREDENTIALS** > **OAuth client ID**
3. If prompted, configure the OAuth consent screen:
   - Choose **External** user type (unless you have a Google Workspace)
   - Fill in the required fields (app name, user support email, developer email)
   - Add these scopes:
     - `.../auth/spreadsheets`
     - `.../auth/userinfo.email`
     - `.../auth/userinfo.profile`
     - `openid`
   - Add test users (your email addresses that will use the app during testing)
   - Save and continue

4. Back at Create OAuth client ID:
   - Application type: **Web application**
   - Name: `MultiHub PromptBuilder`
   - Authorized redirect URIs:
     - `http://localhost:8501` (for local development)
     - Add your production URL if deploying (e.g., `https://yourdomain.com`)
   - Click **CREATE**

5. You'll see your **Client ID** and **Client Secret** - save these!

## Step 4: Configure Environment Variables

Create a `.env` file in your project root or set these environment variables:

```bash

```

For production deployment, update `OAUTH_REDIRECT_URI` to match your production URL.

## Step 5: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 6: Run the Application

```bash
streamlit run app.py
```

## How It Works

1. **User Login**: When users visit the PromptBuilder, they click "Login with Google"
2. **OAuth Flow**: They're redirected to Google to authorize the app
3. **Sheet Creation**: After authorization, a personal Google Sheet is created/accessed named "Prompts - {user_email}"
4. **Save Prompts**: All prompts are saved to the user's personal sheet
5. **Access**: Users can click the link to view their sheet anytime

## Troubleshooting

### "OAuth credentials not configured" error

- Ensure you've set the `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` environment variables
- Check that the values are correct (no extra quotes or spaces)

### Redirect URI mismatch

- Ensure the `OAUTH_REDIRECT_URI` in your environment matches exactly what you configured in Google Cloud Console
- Include the port number for local development (`:8501`)

### Permission denied when creating sheets

- Make sure the Google Sheets API is enabled in your Google Cloud project
- Verify that the OAuth consent screen has the correct scopes

### App not verified warning

- During testing, this is normal for apps not yet published
- Click "Advanced" > "Go to {app name} (unsafe)" to proceed
- To remove this warning, submit your app for verification in the OAuth consent screen settings

## Security Notes

- Never commit your `.env` file or expose your client secret
- Add `.env` to your `.gitignore` file
- For production, use secure secret management (e.g., environment variables in your hosting platform)
- Regularly rotate your OAuth credentials

## Production Deployment

When deploying to production (e.g., Streamlit Cloud, Heroku, etc.):

1. Set environment variables in your platform's settings
2. Update `OAUTH_REDIRECT_URI` to your production URL
3. Add the production URL to "Authorized redirect URIs" in Google Cloud Console
4. If using Streamlit Cloud, add variables to your app's secrets management
