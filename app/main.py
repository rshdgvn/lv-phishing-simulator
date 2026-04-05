from dotenv import load_dotenv
import os
from fastapi import FastAPI, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.services.email_service import send_emails
from app.models.database import SessionLocal, engine, Base, PhishingTarget

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="La Verdad Phishing Simulator")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
async def view_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html", 
        context={"project_name": "Cyber Awareness Tracker"}
    )

@app.post("/api/send-email")
async def trigger_email_drill(db: Session = Depends(get_db)): 
    result = send_emails()
    
    if result["status"] == "success":
        for token, email in result["tracking_data"].items():
            new_target = PhishingTarget(email=email, token=token, clicked=False)
            db.add(new_target)
        db.commit() 
        
        return {"message": result["message"]}
    else:
        return {"message": f"Failed to send: {result['message']}"}

@app.get("/track")
async def track_click(request: Request, token: str = None, db: Session = Depends(get_db)):
    if token:
        target = db.query(PhishingTarget).filter(PhishingTarget.token == token).first()
        
        if target and not target.clicked:
            target.clicked = True
            db.commit()
            print(f"BOOM! Link clicked by: {target.email}")
        elif target and target.clicked:
            print(f"{target.email} clicked the link AGAIN.")
        else:
            print("Unknown or invalid token clicked.")

    return templates.TemplateResponse(
        request=request,
        name="awareness.html", 
        context={}
    )

@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    total_sent = db.query(PhishingTarget).count()
    clicked_targets = db.query(PhishingTarget).filter(PhishingTarget.clicked == True).all()
    
    return {
        "emails_sent": total_sent,
        "total_clicks": len(clicked_targets), 
        "compromised_emails": [target.email for target in clicked_targets]
    }