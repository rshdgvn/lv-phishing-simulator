from urllib.parse import unquote
from fastapi import APIRouter, Depends
from fastapi.responses import Response, RedirectResponse
from sqlalchemy.orm import Session
from app.models.database import SessionLocal, PhishingTarget
from app.websocket import push_tracking_event, broadcast_stats_snapshot

router = APIRouter()

# 1x1 transparent GIF used by /track/open
TRANSPARENT_GIF = (
    b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00"
    b"\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x00\x00\x00\x00"
    b"\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02"
    b"\x44\x01\x00\x3b"
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/track/open")
async def track_open(e: str, db: Session = Depends(get_db)):
    """
    Track open by encoded email (`e`) or token value.
    Returns a 1x1 GIF for email clients.
    """
    key = unquote(e)
    target = (
        db.query(PhishingTarget).filter(PhishingTarget.token == key).first()
        or db.query(PhishingTarget).filter(PhishingTarget.email == key).first()
    )

    if target and not target.is_opened:
        target.is_opened = True
        db.commit()
        await push_tracking_event("opened", target.email)
        await broadcast_stats_snapshot()

    return Response(content=TRANSPARENT_GIF, media_type="image/gif")


@router.get("/track/click")
async def track_click(e: str, r: str = "/", db: Session = Depends(get_db)):
    """
    Track click by encoded email/token (`e`), then redirect.
    """
    key = unquote(e)
    redirect = unquote(r)
    target = (
        db.query(PhishingTarget).filter(PhishingTarget.token == key).first()
        or db.query(PhishingTarget).filter(PhishingTarget.email == key).first()
    )

    if target and not target.is_clicked:
        target.is_clicked = True
        if not target.is_opened:
            target.is_opened = True
        db.commit()
        await push_tracking_event("clicked", target.email)
        await broadcast_stats_snapshot()

    return RedirectResponse(url=redirect)


async def notify_sent(email: str):
    await push_tracking_event("sent", email)
    await broadcast_stats_snapshot()