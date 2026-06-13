# US Daily News Briefing Agent

Runs daily via cron or AWS Lambda. Calls Claude (with web search) to fetch
today's top US-relevant news, formats it as bullet points, and sends a
styled HTML email via Gmail.

---

## Quick start (local cron)

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Get your Anthropic API key

1. Go to https://console.anthropic.com
2. Create an API key
3. Copy `.env.example` → `.env` and paste your key

```bash
cp .env.example .env
```

### 3. Set up Gmail API credentials

1. Go to https://console.cloud.google.com
2. Create a new project (or use existing)
3. Enable the **Gmail API**
4. Go to APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID
5. Application type: **Desktop app**
6. Download the JSON → save as `credentials.json` in this folder
7. Run the script once locally — a browser window opens to authorize Gmail:

```bash
python briefing_agent.py
```

This creates `token.pickle` for future runs (no browser needed again).

### 4. Schedule with cron

Open crontab:

```bash
crontab -e
```

Add this line to run every day at 7:00 AM:

```
0 7 * * * cd /path/to/news-briefing-agent && /usr/bin/python3 briefing_agent.py >> /var/log/briefing.log 2>&1
```

Adjust the path and time to your preference.

---

## AWS Lambda deployment (recommended for reliability)

### 1. Package the project

```bash
pip install -r requirements.txt -t package/
cp briefing_agent.py lambda_handler.py package/
cd package && zip -r ../briefing_agent.zip . && cd ..
```

### 2. Create Lambda function

1. Go to AWS Lambda → Create function
2. Runtime: **Python 3.12**
3. Upload `briefing_agent.zip`
4. Handler: `lambda_handler.handler`

### 3. Set environment variables in Lambda

In the Lambda console → Configuration → Environment variables:

| Key | Value |
|-----|-------|
| `ANTHROPIC_API_KEY` | `sk-ant-...` |
| `RECIPIENT_EMAIL` | `you@example.com` |
| `BULLETS_PER_CAT` | `5` |
| `GMAIL_REFRESH_TOKEN` | *(see below)* |
| `GMAIL_CLIENT_ID` | *(from credentials.json)* |
| `GMAIL_CLIENT_SECRET` | *(from credentials.json)* |

### 4. Gmail auth for Lambda

Lambda can't open a browser, so use a refresh token instead:

```python
# Run this locally once to get your refresh token
from google_auth_oauthlib.flow import InstalledAppFlow
flow = InstalledAppFlow.from_client_secrets_file("credentials.json",
        ["https://www.googleapis.com/auth/gmail.send"])
creds = flow.run_local_server(port=0)
print("Refresh token:", creds.refresh_token)
```

Then in Lambda, rebuild credentials from env vars:

```python
# gmail_lambda.py
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os

def get_gmail_service_lambda():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GMAIL_REFRESH_TOKEN"],
        client_id=os.environ["GMAIL_CLIENT_ID"],
        client_secret=os.environ["GMAIL_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
    )
    return build("gmail", "v1", credentials=creds)
```

### 5. Schedule with EventBridge

1. AWS Console → EventBridge → Schedules → Create schedule
2. Schedule type: **Recurring schedule → Cron**
3. Cron expression for 7:00 AM daily: `0 12 * * ? *` (UTC = 7 AM EST)
4. Target: your Lambda function

---

## Customization

Edit `briefing_agent.py` to change:

- `CATEGORIES` list — add/remove news topics
- `BULLETS_PER_CAT` — via env var or hardcoded
- `build_prompt()` — adjust tone, depth, or focus areas

---

## File structure

```
news-briefing-agent/
├── briefing_agent.py    # main script
├── lambda_handler.py    # AWS Lambda wrapper
├── requirements.txt
├── .env.example
├── credentials.json     # Gmail OAuth (you add this)
├── token.pickle         # auto-generated after first auth
└── README.md
```
