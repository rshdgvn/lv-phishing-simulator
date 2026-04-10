import base64
from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse
from app.models.database import supabase
from app.websocket import push_tracking_event, broadcast_stats_snapshot

router = APIRouter()

EXTERNAL_AWARENESS_URL = "https://lv-cybersecurity-awareness.vercel.app/"
EXTERNAL_LMS_URL = "https://lms-lvcc-edu-ph.vercel.app/"

@router.get("/pixel/{token}.png")
async def track_open(token: str):
    res = supabase.table("phishing_targets").select("*").eq("token", token).execute()
    if res.data:
        target = res.data[0]
        if not target["is_opened"]:
            supabase.table("phishing_targets").update({"is_opened": True}).eq("token", token).execute()
            await push_tracking_event("opened", target["email"])
            await broadcast_stats_snapshot()
            
    transparent_pixel = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=")
    return Response(content=transparent_pixel, media_type="image/png")

@router.get("/track")
async def track_click(request: Request, token: str = None, v: str = "v1"):
    if token:
        res = supabase.table("phishing_targets").select("*").eq("token", token).execute()
        if res.data:
            target = res.data[0]
            if not target["is_clicked"]:
                supabase.table("phishing_targets").update({
                    "is_clicked": True, 
                    "is_opened": True
                }).eq("token", token).execute()
                await push_tracking_event("clicked", target["email"])
                await broadcast_stats_snapshot()

    if v == "v2":
        redirect_url = f"{EXTERNAL_LMS_URL}?token={token}" if token else EXTERNAL_LMS_URL
        return RedirectResponse(url=redirect_url)
    else:
        return RedirectResponse(url=f"{EXTERNAL_AWARENESS_URL}?token={token}", status_code=303)

@router.post("/track/login")
async def track_login_submission(request: Request):
    token, username, password = None, None, None

    if request.headers.get("content-type", "").startswith("application/json"):
        data = await request.json()
        token = data.get("token")
        username = data.get("username")
        password = data.get("password")
    else:
        form = await request.form()
        token = form.get("token")
        username = form.get("username")
        password = form.get("password")

    safe_username = username.strip() if username else ""
    
    is_valid_user = safe_username and password and (
        "@" not in safe_username or safe_username.endswith("laverdad.edu.ph")
    )
    
    if not is_valid_user:
        error_url = f"{EXTERNAL_LMS_URL}?token={token}&error=invalid" if token else f"{EXTERNAL_LMS_URL}?error=invalid"
        return RedirectResponse(url=error_url, status_code=303) 
    
    if token:
        res = supabase.table("phishing_targets").select("*").eq("token", token).execute()
        if res.data:
            target = res.data[0]
            if not target["is_compromised"]:
                supabase.table("phishing_targets").update({"is_compromised": True}).eq("token", token).execute()
                await push_tracking_event("compromised", target["email"])
                await broadcast_stats_snapshot()
            
    return RedirectResponse(url=f"{EXTERNAL_AWARENESS_URL}?token={token}", status_code=303)

@router.get("/track/login/google")
async def track_google_login(request: Request, token: str = None):
    if token:
        res = supabase.table("phishing_targets").select("*").eq("token", token).execute()
        if res.data:
            target = res.data[0]
            if not target["is_compromised"]:
                supabase.table("phishing_targets").update({"is_compromised": True}).eq("token", token).execute()
                await push_tracking_event("compromised", target["email"])
                await broadcast_stats_snapshot()
            
    return RedirectResponse(url=f"{EXTERNAL_AWARENESS_URL}?token={token}", status_code=303)

@router.post("/track/awareness")
async def track_awareness_acknowledgement(request: Request):
    # Same JSON/Form fix for awareness tracking
    token = None
    if request.headers.get("content-type", "").startswith("application/json"):
        data = await request.json()
        token = data.get("token")
    else:
        form = await request.form()
        token = form.get("token")

    if token:
        res = supabase.table("phishing_targets").select("*").eq("token", token).execute()
        if res.data:
            target = res.data[0]
            if not target["is_aware"]:
                supabase.table("phishing_targets").update({"is_aware": True}).eq("token", token).execute()
                await push_tracking_event("aware", target["email"])
                await broadcast_stats_snapshot()
                
            return {"status": "success", "message": "Awareness logged"}
            
    return {"status": "ignored", "message": "No valid token found"}