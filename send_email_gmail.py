#!/usr/bin/env python3
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

def send_email_gmail(events, date_str):
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASS = os.getenv("EMAIL_PASS")
    TO_EMAILS = [e.strip() for e in os.getenv("TO_EMAILS", "").split(",") if e.strip()]

    if not EMAIL_USER or not EMAIL_PASS:
        print("⚠️ Missing EMAIL_USER or EMAIL_PASS in .env")
        return

    # --- Build HTML Email (modern style) ---
    rows = "".join(
        f"""
        <tr style='background-color:#fff;'>
            <td style='padding:8px 12px;border-bottom:1px solid #eee;color:#555;'>{e['date']}</td>
            <td style='padding:8px 12px;border-bottom:1px solid #eee;color:#555;'>{e['venue']}</td>
            <td style='padding:8px 12px;border-bottom:1px solid #eee;'>
                <a href='{e['url']}' style='color:#1a73e8;text-decoration:none;font-weight:500;'>{e['name']}</a>
            </td>
        </tr>
        """
        for e in events
    )

    html = f"""
    <html>
    <body style="margin:0;padding:0;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;background:#f5f6fa;">
      <div style="max-width:700px;margin:30px auto;background:white;border-radius:10px;overflow:hidden;box-shadow:0 3px 12px rgba(0,0,0,0.08);">
        <div style="background:#1a73e8;color:white;padding:18px 24px;text-align:center;">
          <h1 style="margin:0;font-size:24px;">🎟️ PeteSheet NYC Events</h1>
          <p style="margin:4px 0 0;font-size:14px;">Your weekly live event drop — {date_str}</p>
        </div>

        <div style="padding:24px;">
          <p style="font-size:15px;color:#333;margin-bottom:20px;">
            <b>{len(events)}</b> concerts and shows happening in New York City:
          </p>

          <table style="width:100%;border-collapse:collapse;">
            <thead>
              <tr style="background-color:#f1f3f4;">
                <th style="text-align:left;padding:8px 12px;font-size:14px;color:#444;">Date</th>
                <th style="text-align:left;padding:8px 12px;font-size:14px;color:#444;">Venue</th>
                <th style="text-align:left;padding:8px 12px;font-size:14px;color:#444;">Event</th>
              </tr>
            </thead>
            <tbody>{rows}</tbody>
          </table>
        </div>

        <div style="background:#f1f3f4;padding:12px 20px;text-align:center;font-size:12px;color:#777;">
          Generated automatically by <b>PeteSheet</b> 🎫 | <a href="mailto:{EMAIL_USER}" style="color:#1a73e8;text-decoration:none;">Contact</a>
        </div>
      </div>
    </body>
    </html>
    """

    # --- Send email ---
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🎫 PeteSheet NYC Events – {date_str}"
    msg["From"] = EMAIL_USER
    msg["To"] = ", ".join(TO_EMAILS)
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, TO_EMAILS, msg.as_string())
        print(f"📤 Email sent successfully from {EMAIL_USER} → {TO_EMAILS}")
    except Exception as e:
        print("❌ Gmail send error:", e)