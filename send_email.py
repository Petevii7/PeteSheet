#!/usr/bin/env python3
import os
import json
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

load_dotenv()


def send_email_dynamic(events, date_str):
    """
    Send an email summary of collected events using SendGrid.
    """
    SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
    FROM_EMAIL = os.getenv("FROM_EMAIL")
    TO_EMAILS = [e.strip() for e in os.getenv("TO_EMAILS", "").split(",")]

    # Build a simple HTML summary table of events
    rows = "".join(
        f"<tr><td>{e['date']}</td><td>{e['venue']}</td><td><a href='{e['url']}'>{e['name']}</a></td></tr>"
        for e in events
    )
    html_content = f"""
    <h2>🎫 Pete Sheet - Live Events – {date_str}</h2>
    <p>Total events: <b>{len(events)}</b></p>
    <table border='1' cellpadding='6'>
        <tr><th>Date</th><th>Venue</th><th>Event</th></tr>
        {rows}
    </table>
    """

    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=TO_EMAILS,
        subject=f"🎟️ Pete Sheet - Live Events – {date_str} ({len(events)} shows)",
        html_content=html_content,
    )

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"📤 Email sent successfully from {FROM_EMAIL} → {TO_EMAILS} | Status: {response.status_code}")
    except Exception as e:
        print("❌ SendGrid Error:", e)


if __name__ == "__main__":
    # Optional: for manual testing
    with open("outputs/events_2025-10-25.json") as f:
        events = json.load(f).get("events", [])
        send_email_dynamic(events, "2025-10-25")
