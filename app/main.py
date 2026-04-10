from dotenv import load_dotenv
import os
from typing import List
from fastapi import FastAPI, Request, Depends, Response, Cookie, HTTPException
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import jwt 
from datetime import datetime, timedelta 
import hashlib
from app.services.email_service import send_emails
from app.models.database import supabase
from app.websocket import router as websocket_router, push_tracking_event, broadcast_stats_snapshot
from app.track import router as track_router

load_dotenv()

app = FastAPI(title="La Verdad Phishing Simulator")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "static/templates"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
app.include_router(websocket_router)
app.include_router(track_router)

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

class TargetItem(BaseModel):
    name: str
    email: str

class EmailRequest(BaseModel):
    targets: List[TargetItem]
    version: str = "v1" 

class LoginRequest(BaseModel):
    passcode: str

def get_client_fingerprint(request: Request):
    ip = request.client.host
    user_agent = request.headers.get("user-agent", "unknown")
    raw_fingerprint = f"{ip}::{user_agent}"
    return hashlib.sha256(raw_fingerprint.encode()).hexdigest()

def verify_session(request: Request, session_token: str = Cookie(None)):
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(session_token, SECRET_KEY, algorithms=[ALGORITHM])
        current_fingerprint = get_client_fingerprint(request)
        if payload.get("fgpt") != current_fingerprint:
            raise HTTPException(status_code=403, detail="Session hijacked or environment changed")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid session")
    return True

@app.post("/api/admin/login")
async def admin_login(payload: LoginRequest, response: Response, request: Request):
    correct_passcode = os.getenv("ADMIN_PASSCODE", "admin123")
    if payload.passcode != correct_passcode:
        raise HTTPException(status_code=401, detail="Invalid passcode")
    
    fingerprint = get_client_fingerprint(request)
    expire = datetime.utcnow() + timedelta(hours=12)
    token = jwt.encode(
        {"sub": "admin", "exp": expire, "fgpt": fingerprint}, 
        SECRET_KEY, 
        algorithm=ALGORITHM
    )
    
    response.set_cookie(
        key="session_token", 
        value=token, 
        httponly=True, 
        samesite="Lax", 
        max_age=43200 
    )
    return {"message": "Authenticated"}

@app.post("/api/admin/logout")
async def admin_logout(response: Response):
    response.delete_cookie("session_token")
    return {"message": "Logged out"}

@app.get("/api/admin/check-session")
async def check_session(is_valid: bool = Depends(verify_session)):
    return {"status": "authenticated"}

@app.get("/")
async def view_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html", 
        context={"project_name": "La Verdad Phishing Simulator"}
    )

@app.post("/api/send-email")
async def trigger_email_drill(payload: EmailRequest, _ = Depends(verify_session)):
    target_list = [{"name": t.name, "email": t.email} for t in payload.targets]
    
    if not target_list:
        return JSONResponse(status_code=400, content={"message": "No valid targets provided."})

    result = send_emails(target_list, payload.version)
    
    if result["status"] == "success":
        try:
            for token, email in result["tracking_data"].items():
                supabase.table("phishing_targets").upsert({
                    "email": email,
                    "token": token,
                    "is_sent": True,
                    "is_opened": False,
                    "is_clicked": False,
                    "is_compromised": False,
                    "is_aware": False
                }, on_conflict="email").execute()

            for email in result["tracking_data"].values():
                await push_tracking_event("sent", email)
            await broadcast_stats_snapshot()
            
            return {"message": result["message"]}
            
        except Exception as e:
            return JSONResponse(status_code=500, content={"message": f"Email sent, but database failed to update: {str(e)}"})
    else:
        return JSONResponse(status_code=400, content={"message": f"Failed to send: {result['message']}"})

@app.get("/api/stats")
async def get_stats(_ = Depends(verify_session)):
    res = supabase.table("phishing_targets").select("*").execute()
    targets = res.data if res.data else []
    
    total_sent = len(targets)
    total_opened = sum(1 for t in targets if t.get("is_opened"))
    total_clicked = sum(1 for t in targets if t.get("is_clicked"))
    total_compromised = sum(1 for t in targets if t.get("is_compromised"))
    total_aware = sum(1 for t in targets if t.get("is_aware"))
    
    click_rate = round((total_clicked / total_sent * 100), 1) if total_sent > 0 else 0
    open_rate = round((total_opened / total_sent * 100), 1) if total_sent > 0 else 0
    compromised_rate = round((total_compromised / total_sent * 100), 1) if total_sent > 0 else 0
    aware_rate = round((total_aware / total_sent * 100), 1) if total_sent > 0 else 0

    table_data = [
        {
            "email": t.get("email"), 
            "sent": t.get("is_sent"), 
            "opened": t.get("is_opened"), 
            "clicked": t.get("is_clicked"),
            "compromised": t.get("is_compromised"),
            "aware": t.get("is_aware")
        } for t in targets
    ]
    
    return {
        "analytics": {
            "total_sent": total_sent,
            "total_opened": total_opened,
            "total_clicked": total_clicked,
            "total_compromised": total_compromised,
            "total_aware": total_aware,
            "open_rate": f"{open_rate}%",
            "click_rate": f"{click_rate}%",
            "compromised_rate": f"{compromised_rate}%"
        },
        "table": table_data
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)