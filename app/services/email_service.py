import smtplib
from email.message import EmailMessage
import ssl
import os
import secrets
from urllib.parse import quote
import time

def send_emails(targets: list, version: str = "v1"):
    BASE_URL = os.getenv("BASE_URL")
    SENDER_EMAIL = os.getenv("SENDER_EMAIL")
    APP_PASSWORD = os.getenv("APP_PASSWORD")
    SENDER_NAME = "Admin user (via LEARNING MANAGEMENT SYSTEM)"

    if not SENDER_EMAIL or not APP_PASSWORD or not SENDER_NAME or not BASE_URL:
        return {"status": "error", "message": "Missing credentials in .env file."}

    context = ssl.create_default_context()
    tracking_data = {} 

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            
            for person in targets:
                unique_token = secrets.token_urlsafe(16)
                tracking_data[unique_token] = person["email"]

                msg = EmailMessage()
                msg['Subject'] = "ACTION REQUIRED: Verify Your LMS Account Access"
                msg['From'] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
                msg['To'] = person["email"]

                tracking_link = f"{BASE_URL}/track?token={quote(unique_token)}&v={version}"
                
                pixel_link = f"{BASE_URL}/pixel/{quote(unique_token)}.png"

                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <style>
                        body {{ font-family: Arial, sans-serif; color: #000000; line-height: 1.5; }}
                        .container {{ max-width: 650px; margin: 0 auto; border: 1px solid #e5e7eb; padding: 30px; background-color: #ffffff; }}
                        .blue-bar {{ background-color: #1460A5; height: 16px; width: 100%; margin: 20px 0; }}
                        .header-text {{ text-align: center; font-size: 24px; color: #333; margin-top: 10px; font-weight: normal; }}
                        .logo-container {{ text-align: center; margin: 20px 0; }}
                        .logo {{ max-width: 120px; }}
                        .content {{ padding: 0 10px; font-size: 14px; }}
                        .important-note {{ font-weight: bold; margin-top: 25px; margin-bottom: 5px; color: #b91c1c; }}
                        .footer {{ font-size: 11px; font-style: italic; color: #555; margin-top: 40px; }}
                        .highlight {{ background-color: #fef08a; padding: 2px 4px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="blue-bar"></div>

                        <div class="logo-container">
                            <img class="logo" src="https://lms.laverdad.edu.ph/pluginfile.php/1/core_admin/logo/0x200/1760791385/lvcc_logo.png" alt="LVCC Logo" />
                        </div>
                        
                        <div class="header-text">LMS Account Verification</div>
                        
                        <div class="blue-bar"></div>

                        <div class="content">
                            <p>Dear {person['name']},</p>

                            <p>We are currently implementing critical security upgrades to our Learning Management System (LMS) to ensure a safe online environment for the current semester.</p>

                            <p>Our records indicate that your account access has not yet been verified under the new security protocol. To maintain uninterrupted access to your courses, modules, and upcoming assignments, you are required to log in and confirm your credentials.</p>

                            <p>Please complete this quick verification process immediately.</p>

                            <p>Securely log in and verify your account here:<br>
                            <a href="{tracking_link}" style="color: #1a0dab; text-decoration: underline; font-weight: bold;">LMS Login Portal</a></p>

                            <p class="important-note">IMPORTANT NOTE:</p>
                            <p style="margin-top: 0;">Failure to verify your account within 24 hours will result in an automatic, temporary suspension of your LMS access. This may affect your ability to submit pending coursework or access class materials.</p>

                            <p>If you experience any issues logging in, please contact the IT Support Desk immediately.</p>

                            <p>Best regards,<br>
                            IT Support & Systems Administration<br>
                            Email: <span class="highlight">info@laverdad.edu.ph</span></p>

                            <p class="footer">***This is an automated system security notification. Please do not reply.</p>
                        </div>
                        
                        <img src="{pixel_link}" width="1" height="1" style="display:none;" />
                    </div>
                </body>
                </html>
                """
                
                msg.set_content(html_content, subtype='html')
                server.send_message(msg)
                
        return {"status": "success", "message": f"Sent to {len(targets)} targets.", "tracking_data": tracking_data}

    except Exception as e:
        return {"status": "error", "message": str(e)}