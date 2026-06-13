"""
US Daily News Briefing Agent
Calls Anthropic API with web search, then sends formatted email via Gmail API.
"""

import os
import base64
import datetime
import anthropic
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle

# ── Config ────────────────────────────────────────────────────────────────────

RECIPIENT_EMAIL   = os.environ.get("RECIPIENT_EMAIL", "you@example.com")
BULLETS_PER_CAT   = int(os.environ.get("BULLETS_PER_CAT", "5"))
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

CATEGORIES = [
    "geopolitics & foreign policy",
    "US economy & markets",
    "domestic politics",
    "trade & tariffs",
    "national security & defense",
]

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# ── Briefing prompt ────────────────────────────────────────────────────────────

def build_prompt() -> str:
    today = datetime.date.today().strftime("%B %d, %Y")
    cat_list = "\n".join(f"- {c}" for c in CATEGORIES)
    return f"""You are a world-class news analyst. Today is {today}.

Search the web for the latest breaking news and produce a concise US daily briefing.

For each of the following categories, write exactly {BULLETS_PER_CAT} bullet points.
Each bullet must be ONE sentence: state the key fact and its relevance to the United States.

Categories:
{cat_list}

Format your response exactly like this (use plain text, no markdown bold):

GEOPOLITICS & FOREIGN POLICY
• bullet one
• bullet two
...

US ECONOMY & MARKETS
• bullet one
...

(and so on for every category)

Be factual, neutral, and specific. Include country names, figures, and context where possible.
Do not add any intro or closing text — just the categorized bullets."""

# ── Claude API call with web search ───────────────────────────────────────────

def fetch_briefing() -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": build_prompt()}],
    )

    # Extract the final text response (after tool use rounds)
    text_blocks = [b.text for b in response.content if hasattr(b, "text")]
    return "\n".join(text_blocks).strip()

# ── Gmail auth ─────────────────────────────────────────────────────────────────

def get_gmail_service():
    creds = None
    token_path = "token.pickle"
    creds_path = "credentials.json"  # Downloaded from Google Cloud Console

    if os.path.exists(token_path):
        with open(token_path, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "wb") as f:
            pickle.dump(creds, f)

    return build("gmail", "v1", credentials=creds)

# ── Build HTML email ───────────────────────────────────────────────────────────

def briefing_to_html(briefing_text: str) -> str:
    today = datetime.date.today().strftime("%A, %B %d, %Y")

    category_colors = {
        "GEOPOLITICS": ("#E6F1FB", "#0C447C"),
        "ECONOMY":     ("#EAF3DE", "#27500A"),
        "POLITICS":    ("#EEEDFE", "#3C3489"),
        "TRADE":       ("#FAECE7", "#712B13"),
        "SECURITY":    ("#FAEEDA", "#633806"),
        "CLIMATE":     ("#E1F5EE", "#085041"),
    }

    def get_color(heading: str):
        for key, colors in category_colors.items():
            if key in heading.upper():
                return colors
        return ("#F1EFE8", "#444441")

    sections_html = ""
    current_heading = None
    bullets = []

    for line in briefing_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("•"):
            bullets.append(line[1:].strip())
        else:
            if current_heading and bullets:
                bg, fg = get_color(current_heading)
                bullet_items = "".join(
                    f'<li style="margin-bottom:8px;line-height:1.6;">{b}</li>'
                    for b in bullets
                )
                sections_html += f"""
                <div style="margin-bottom:24px;">
                  <div style="display:inline-block;background:{bg};color:{fg};
                              font-size:12px;font-weight:600;padding:4px 12px;
                              border-radius:6px;margin-bottom:10px;letter-spacing:0.05em;">
                    {current_heading}
                  </div>
                  <ul style="margin:0;padding-left:20px;font-size:15px;color:#1a1a1a;">
                    {bullet_items}
                  </ul>
                </div>"""
            current_heading = line.title()
            bullets = []

    # flush last section
    if current_heading and bullets:
        bg, fg = get_color(current_heading)
        bullet_items = "".join(
            f'<li style="margin-bottom:8px;line-height:1.6;">{b}</li>'
            for b in bullets
        )
        sections_html += f"""
        <div style="margin-bottom:24px;">
          <div style="display:inline-block;background:{bg};color:{fg};
                      font-size:12px;font-weight:600;padding:4px 12px;
                      border-radius:6px;margin-bottom:10px;letter-spacing:0.05em;">
            {current_heading}
          </div>
          <ul style="margin:0;padding-left:20px;font-size:15px;color:#1a1a1a;">
            {bullet_items}
          </ul>
        </div>"""

    return f"""
    <html><body style="margin:0;padding:0;background:#f5f5f0;font-family:Arial,sans-serif;">
      <div style="max-width:640px;margin:32px auto;background:#ffffff;
                  border-radius:12px;border:1px solid #e0e0d8;overflow:hidden;">
        <div style="background:#1a1a1a;padding:24px 32px;">
          <p style="margin:0;font-size:13px;color:#888;letter-spacing:0.08em;">DAILY BRIEFING</p>
          <h1 style="margin:6px 0 0;font-size:22px;color:#ffffff;font-weight:500;">
            US News Summary
          </h1>
          <p style="margin:6px 0 0;font-size:13px;color:#aaa;">{today}</p>
        </div>
        <div style="padding:28px 32px;">
          {sections_html}
        </div>
        <div style="padding:16px 32px;border-top:1px solid #e0e0d8;
                    font-size:12px;color:#aaa;text-align:center;">
          Powered by Claude + web search &nbsp;·&nbsp; Unsubscribe
        </div>
      </div>
    </body></html>"""

# ── Send email ─────────────────────────────────────────────────────────────────

def send_email(service, html_body: str):
    today = datetime.date.today().strftime("%B %d, %Y")
    subject = f"Your US News Briefing — {today}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["To"]      = RECIPIENT_EMAIL
    msg.attach(MIMEText(html_body, "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
    print(f"✓ Briefing sent to {RECIPIENT_EMAIL}")

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("Fetching today's news briefing...")
    briefing_text = fetch_briefing()
    print("Briefing fetched. Building email...")
    html = briefing_to_html(briefing_text)
    print("Connecting to Gmail...")
    gmail = get_gmail_service()
    send_email(gmail, html)

if __name__ == "__main__":
    main()
