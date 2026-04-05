from dotenv import load_dotenv
import os

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.services.email_service import send_emails

app = FastAPI(title="School Phishing Simulator")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

active_campaign = {} 
clicked_users = set()

@app.get("/")
async def view_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html", 
        context={"project_name": "Cyber Awareness Tracker"}
    )

@app.post("/api/email")
async def trigger_email():
    result = send_emails()
    
    if result["status"] == "success":
        active_campaign.update(result["tracking_data"])
        return {"message": result["message"]}
    else:
        return {"message": f"Failed to send: {result['message']}"}

@app.get("/track")
async def track_click(request: Request, token: str = None): 
    
    if token and token in active_campaign:
        victim_email = active_campaign[token]
        clicked_users.add(victim_email)
        print(f"BOOM! Link clicked by: {victim_email}")
    else:
        print("Unknown or invalid token clicked.")

    return templates.TemplateResponse(
        request=request,
        name="awareness.html", 
        context={}
    )

@app.get("/api/stats")
async def get_stats():
    return {
        "emails_sent": len(active_campaign),
        "total_clicks": len(clicked_users), 
        "compromised_emails": list(clicked_users)
    }