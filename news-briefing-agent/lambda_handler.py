"""
AWS Lambda handler — wraps briefing_agent.py for serverless deployment.
Triggered by EventBridge Scheduler (cron).
"""

import os
from briefing_agent import fetch_briefing, briefing_to_html, send_email
from gmail_lambda import get_gmail_service_lambda  # see README for Lambda Gmail setup


def handler(event, context):
    print("Lambda triggered — starting daily briefing...")
    try:
        briefing_text = fetch_briefing()
        html = briefing_to_html(briefing_text)
        gmail = get_gmail_service_lambda()
        send_email(gmail, html)
        return {"statusCode": 200, "body": "Briefing sent successfully."}
    except Exception as e:
        print(f"Error: {e}")
        raise
