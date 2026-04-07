from dotenv import load_dotenv
import os
from typing import List
import base64
from fastapi import FastAPI, Request, Depends, Response, Form, Cookie, HTTPException, status
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel
from fastapi.responses import JSONResponse, RedirectResponse
from app.services.email_service import send_emails
from app.models.database import SessionLocal, engine, Base, PhishingTarget
from app.websocket import router as websocket_router, push_tracking_event, broadcast_stats_snapshot
from app.track import router as track_router
from fastapi.staticfiles import StaticFiles
import uvicorn
import jwt 
from datetime import datetime, timedelta 
import hashlib

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="La Verdad Phishing Simulator")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "static/templates"))
app.include_router(websocket_router)
app.include_router(track_router)

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

EXTERNAL_AWARENESS_URL = "https://lv-cybersecurity-awareness.vercel.app/"
EXTERNAL_LMS_URL = "https://lms-lvcc-edu-ph.vercel.app/"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
async def trigger_email_drill(payload: EmailRequest, db: Session = Depends(get_db), _ = Depends(verify_session)):
    target_list = [{"name": t.name, "email": t.email} for t in payload.targets]
    
    if not target_list:
        return JSONResponse(status_code=400, content={"message": "No valid targets provided."})

    result = send_emails(target_list, payload.version)
    
    if result["status"] == "success":
        try:
            for token, email in result["tracking_data"].items():
                existing_target = db.query(PhishingTarget).filter(PhishingTarget.email == email).first()
                
                if existing_target:
                    existing_target.token = token
                    existing_target.is_sent = True
                    existing_target.is_opened = False
                    existing_target.is_clicked = False
                    existing_target.is_compromised = False 
                else:
                    new_target = PhishingTarget(email=email, token=token, is_sent=True)
                    db.add(new_target)
            
            db.commit()

            for email in result["tracking_data"].values():
                await push_tracking_event("sent", email)
            await broadcast_stats_snapshot()
            return {"message": result["message"]}
            
        except Exception as e:
            db.rollback()
            return JSONResponse(status_code=500, content={"message": "Email sent, but database failed to update."})
    else:
        return JSONResponse(status_code=400, content={"message": f"Failed to send: {result['message']}"})

@app.get("/pixel/{token}.png")
async def track_open(token: str, db: Session = Depends(get_db)):
    target = db.query(PhishingTarget).filter(PhishingTarget.token == token).first()
    if target and not target.is_opened:
        target.is_opened = True
        db.commit()
    
    transparent_pixel = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=")
    return Response(content=transparent_pixel, media_type="image/png")

@app.get("/track")
async def track_click(request: Request, token: str = None, v: str = "v1", db: Session = Depends(get_db)):
    if token:
        target = db.query(PhishingTarget).filter(PhishingTarget.token == token).first()
        if target and not target.is_clicked:
            target.is_clicked = True
            target.is_opened = True 
            db.commit()

    if v == "v2":
        redirect_url = f"{EXTERNAL_LMS_URL}?token={token}" if token else EXTERNAL_LMS_URL
        return RedirectResponse(url=redirect_url)
    else:
        return RedirectResponse(url=EXTERNAL_AWARENESS_URL)

@app.post("/track/login")
async def track_login_submission(
    request: Request, 
    token: str = Form(None), 
    username: str = Form(None), 
    password: str = Form(None), 
    db: Session = Depends(get_db)
):
    safe_username = username.strip() if username else ""
    
    if not safe_username or not password or not safe_username.endswith("laverdad.edu.ph"):
        error_url = f"{EXTERNAL_LMS_URL}?token={token}&error=invalid" if token else f"{EXTERNAL_LMS_URL}?error=invalid"
        return RedirectResponse(url=error_url, status_code=303) 
    
    if token:
        target = db.query(PhishingTarget).filter(PhishingTarget.token == token).first()
        if target and not target.is_compromised:
            target.is_compromised = True
            db.commit()
            await push_tracking_event("compromised", target.email)
            await broadcast_stats_snapshot()
            
    return RedirectResponse(url=EXTERNAL_AWARENESS_URL, status_code=303)

@app.get("/track/login/google")
async def track_google_login(request: Request, token: str = None, db: Session = Depends(get_db)):
    if token:
        target = db.query(PhishingTarget).filter(PhishingTarget.token == token).first()
        if target and not target.is_compromised:
            target.is_compromised = True
            db.commit()
            await push_tracking_event("compromised", target.email)
            await broadcast_stats_snapshot()
            
    return RedirectResponse(url=EXTERNAL_AWARENESS_URL)

@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db), _ = Depends(verify_session)):
    targets = db.query(PhishingTarget).all()
    
    total_sent = len(targets)
    total_opened = sum(1 for t in targets if t.is_opened)
    total_clicked = sum(1 for t in targets if t.is_clicked)
    total_compromised = sum(1 for t in targets if t.is_compromised)
    
    click_rate = round((total_clicked / total_sent * 100), 1) if total_sent > 0 else 0
    open_rate = round((total_opened / total_sent * 100), 1) if total_sent > 0 else 0
    compromised_rate = round((total_compromised / total_sent * 100), 1) if total_sent > 0 else 0

    table_data = [
        {
            "email": t.email, 
            "sent": t.is_sent, 
            "opened": t.is_opened, 
            "clicked": t.is_clicked,
            "compromised": t.is_compromised
        } for t in targets
    ]
    
    return {
        "analytics": {
            "total_sent": total_sent,
            "total_opened": total_opened,
            "total_clicked": total_clicked,
            "total_compromised": total_compromised,
            "open_rate": f"{open_rate}%",
            "click_rate": f"{click_rate}%",
            "compromised_rate": f"{compromised_rate}%"
        },
        "table": table_data
    }

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)