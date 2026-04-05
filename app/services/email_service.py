import smtplib
from email.message import EmailMessage
import ssl
import json
import os
import secrets  

TARGETS_JSON = """
[
    {"name": "Rasheed Gavin Esponga", "email": "rasheedgavinesponga@student.laverdad.edu.ph"}
]
"""

def send_emails():
    SENDER_EMAIL = os.getenv("SENDER_EMAIL")
    APP_PASSWORD = os.getenv("APP_PASSWORD")
    SENDER_NAME = os.getenv("SENDER_NAME")

    if not SENDER_EMAIL or not APP_PASSWORD or not SENDER_NAME:
        return {"status": "error", "message": "Missing credentials in .env file."}

    targets = json.loads(TARGETS_JSON)
    context = ssl.create_default_context()
    
    tracking_data = {} 

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            
            for person in targets:
                unique_token = secrets.token_urlsafe(16)
                
                tracking_data[unique_token] = person["email"]

                msg = EmailMessage()
                msg['Subject'] = "ACTION REQUIRED: Update Your Staff Portal Password"
                msg['From'] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
                msg['To'] = person["email"]

                tracking_link = f"http://127.0.0.1:8000/track?token={unique_token}"

                html_content = f"""
                <html>
                    <body>
                        <p>Hello {person['name']},</p>
                        <p>Please click <a href="{tracking_link}">here</a> to verify your account.</p>
                        <br>
                        <p>Thank you,<br>IT Support</p>
                    </body>
                </html>
                """
                msg.set_content(html_content, subtype='html')
                server.send_message(msg)
                
        return {
            "status": "success", 
            "message": f"Successfully sent to {len(targets)} targets.",
            "tracking_data": tracking_data
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}