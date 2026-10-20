"""PondPulse MVP: photo + readings -> Safe / Watch / Danger -> English alert.

Run:  uvicorn app:app --reload
Open: http://127.0.0.1:8000
"""
import io
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse
from PIL import Image

app = FastAPI(title="PondPulse MVP")

LEVELS = ["SAFE", "WATCH", "DANGER"]

# English alert templates and per-cause hints.
REASON = {
    "oxygen": "Check the water's oxygen.",
    "ph": "Check the water's pH.",
    "temp": "Check the water temperature.",
    "image": "Check the pond water colour.",
}
EN = {
    "SAFE": "All looks normal. Keep monitoring.",
    "WATCH": "Early warning. Reduce feeding today.",
    "DANGER": "High risk! Aerate now and contact a fisheries officer or lab.",
}


def image_risk(data: bytes) -> float:
    """PLACEHOLDER image score (0 to 1) from water colour only.

    Very green or murky water scores higher. Replace this function with a
    trained classifier (e.g. transfer learning on public pond/disease images).
    """
    img = Image.open(io.BytesIO(data)).convert("RGB").resize((64, 64))
    px = list(img.getdata())
    r = sum(p[0] for p in px) / len(px)
    g = sum(p[1] for p in px) / len(px)
    b = sum(p[2] for p in px) / len(px)
    greenness = g - (r + b) / 2          # strong green tint -> algae bloom
    darkness = 1 - (r + g + b) / (3 * 255)
    return round(max(0.0, min(1.0, greenness / 60 + darkness * 0.3)), 2)


def assess(do: Optional[float], ph: Optional[float], temp: Optional[float],
           img: Optional[float]):
    """Illustrative thresholds. Tune with open datasets and expert advice."""
    level, reasons = 0, []

    def bump(lv, reason):
        nonlocal level
        level = max(level, lv)
        if reason not in reasons:
            reasons.append(reason)

    if do is not None:
        if do < 3:
            bump(2, "oxygen")
        elif do < 4:
            bump(1, "oxygen")
    if ph is not None:
        if ph < 6.5 or ph > 9:
            bump(2, "ph")
        elif ph < 7.5 or ph > 8.5:
            bump(1, "ph")
    if temp is not None:
        if temp > 34 or temp < 18:
            bump(2, "temp")
        elif temp > 32 or temp < 22:
            bump(1, "temp")
    if img is not None:
        if img > 0.7:
            bump(2, "image")
        elif img > 0.4:
            bump(1, "image")

    name = LEVELS[level]
    message = " ".join([REASON[r] for r in reasons] + [EN[name]])
    return name, reasons, message


@app.post("/api/assess")
async def api_assess(
    oxygen: Optional[float] = Form(None),   # dissolved oxygen, mg/L
    ph: Optional[float] = Form(None),
    temperature: Optional[float] = Form(None),  # deg C
    photo: Optional[UploadFile] = File(None),
):
    img_score = None
    if photo is not None and photo.filename:
        img_score = image_risk(await photo.read())
    level, reasons, message = assess(oxygen, ph, temperature, img_score)
    return {
        "risk": level,
        "reasons": reasons,
        "image_score": img_score,
        "alert": message,
    }


@app.get("/")
def home():
    return FileResponse("static/index.html")
