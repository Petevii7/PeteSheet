#!/usr/bin/env python3
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

load_dotenv()

def send_email_dynamic(events, date_str):
    """
    Send an HTML email summary of events using SendGrid.
    """
    SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
    FROM_EMAIL = os.getenv("FROM_EMAIL")
    TO_EMAILS = [e.strip() for e in os.getenv("TO_EMAILS", "").split(",")]

    # --- Styled HTML ---
    rows = "".join(
        f"<tr><td>{e['date']}</td><td>{e['venue']}</td><td><a href='{e['url']}'>{e['name']}</a></td></tr>"
        for e in events
    )

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8" />
    <title>Pete Sheet – NYC Live Events</title>
    <style>
      body {{
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        background-color: #f5f7fa;
        color: #222;
        padding: 20px;
      }}
      h2 {{
        color: #0b5394;
        text-align: center;
      }}
      p.summary {{
        text-align: center;
        font-size: 15px;
        margin-bottom: 25px;
      }}
      table {{
        width: 100%;
        border-collapse: collapse;
        margin: 0 auto;
        background: #fff;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
      }}
      th {{
        background-color: #0b5394;
        color: #fff;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding: 10px;
      }}
      td {{
        padding: 10px;
        border-bottom: 1px solid #eee;
        font-size: 14px;
      }}
      tr:nth-child(even) td {{
        background-color: #f9f9f9;
      }}
      a {{
        color: #0b5394;
        text-decoration: none;
        font-weight: 600;
      }}
      a:hover {{
        text-decoration: underline;
      }}
      .footer {{
        text-align: center;
        font-size: 12px;
        color: #777;
        margin-top: 30px;
      }}
    </style>
    </head>
    <body>
      <h2>🎫 Pete Sheet – NYC Live Events ({date_str})</h2>
      <p class="summary"><b>{len(events)}</b> total shows across the city’s top venues.</p>
      <table>
        <thead><tr><th>Date</th><th>Venue</th><th>Event</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
      <div class="footer">
        <p>Generated automatically by Pete Sheet • {datetime.now().strftime("%B %d, %Y %I:%M %p")}</p>
      </div>
    </body>
    </html>
    """

    # --- SendGrid send ---
    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=TO_EMAILS,
        subject=f"🎟️ Pete Sheet – NYC Events ({len(events)} shows, {date_str})",
        html_content=html_content,
    )

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"📤 Email sent successfully from {FROM_EMAIL} → {TO_EMAILS} | Status: {response.status_code}")
    except Exception as e:
        print("❌ SendGrid Error:", e)


if __name__ == "__main__":
    from datetime import datetime
    today_str = datetime.now().strftime("%Y-%m-%d")

    file_path = f"outputs/events_{today_str}.json"
    if os.path.exists(file_path):
        with open(file_path) as f:
            events = json.load(f).get("events", [])
            send_email_dynamic(events, today_str)
    else:
        print(f"⚠️ No file found for today: {file_path}")
