"""PondPulse backend. Run: python -m uvicorn app:app --reload"""
import io
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, ImageStat, UnidentifiedImageError

app = FastAPI(title="PondPulse MVP", version="1.1.0")
FRONTEND = Path(__file__).parent / "static" / "index.html"

LEVELS = ["SAFE", "WATCH", "DANGER"]
REASONS = {
    "oxygen": "Check the water's dissolved oxygen.",
    "ph": "Check the water's pH.",
    "temperature": "Check the water temperature.",
    "photo": "Check the pond water colour.",
}
ALERTS = {
    "SAFE": "All looks normal. Keep monitoring.",
    "WATCH": "Early warning. Review water conditions and reduce feeding if appropriate.",
    "DANGER": "High risk! Check measurements immediately, increase aeration if appropriate, "
              "and contact a fisheries officer or water-testing lab.",
}


def photo_score(photo_bytes):
    """Basic colour score only; this is not a trained disease classifier."""
    image = Image.open(io.BytesIO(photo_bytes)).convert("RGB").resize((64, 64))
    red, green, blue = ImageStat.Stat(image).mean
    green_score = green - (red + blue) / 2
    dark_score = 1 - (red + green + blue) / (3 * 255)
    score = green_score / 60 + dark_score * 0.3
    return round(max(0, min(1, score)), 2)


def assess_pond(oxygen, ph, temperature, image_score):
    risk, reasons = 0, []

    def warn(level, reason):
        nonlocal risk
        risk = max(risk, level)
        if reason not in reasons:
            reasons.append(reason)

    if oxygen is not None:
        if oxygen < 3:
            warn(2, "oxygen")
        elif oxygen < 4:
            warn(1, "oxygen")

    if ph is not None:
        if ph < 6.5 or ph > 9:
            warn(2, "ph")
        elif ph < 7.5 or ph > 8.5:
            warn(1, "ph")

    if temperature is not None:
        if temperature < 18 or temperature > 34:
            warn(2, "temperature")
        elif temperature < 22 or temperature > 32:
            warn(1, "temperature")

    if image_score is not None:
        if image_score > 0.7:
            warn(2, "photo")
        elif image_score > 0.4:
            warn(1, "photo")

    level = LEVELS[risk]
    alert = " ".join([REASONS[item] for item in reasons] + [ALERTS[level]])
    return level, reasons, alert


@app.get("/")
def home():
    if not FRONTEND.is_file():
        raise HTTPException(500, "Frontend not found: create static/index.html.")
    return FileResponse(FRONTEND)


@app.get("/health")
def health():
    return {"status": "ok", "frontend_found": FRONTEND.is_file()}


@app.post("/api/assess")
async def api_assess(
    oxygen: float | None = Form(None),
    ph: float | None = Form(None),
    temperature: float | None = Form(None),
    photo: UploadFile | None = File(None),
):
    if all(value is None for value in (oxygen, ph, temperature)) and not (
        photo and photo.filename
    ):
        raise HTTPException(400, "Provide at least one water reading or a pond photo.")

    if oxygen is not None and oxygen < 0:
        raise HTTPException(422, "Dissolved oxygen cannot be negative.")
    if ph is not None and not 0 <= ph <= 14:
        raise HTTPException(422, "pH must be between 0 and 14.")
    if temperature is not None and not -10 <= temperature <= 100:
        raise HTTPException(422, "Temperature must be between -10 and 100 °C.")

    image_score = None
    if photo and photo.filename:
        try:
            photo_bytes = await photo.read()
            if not photo_bytes:
                raise HTTPException(400, "The uploaded photo is empty.")
            if len(photo_bytes) > 10 * 1024 * 1024:
                raise HTTPException(413, "Photo must be 10 MB or smaller.")
            image_score = photo_score(photo_bytes)
        except UnidentifiedImageError:
            raise HTTPException(400, "The uploaded file is not a valid image.")
        except OSError:
            raise HTTPException(400, "The uploaded image could not be read.")
        finally:
            await photo.close()

    level, reasons, alert = assess_pond(oxygen, ph, temperature, image_score)
    return {
        "risk": level,
        "reasons": reasons,
        "image_score": image_score,
        "alert": alert,
        "note": "Illustrative screening only; not a substitute for validated water testing "
                "or professional advice.",
    }
