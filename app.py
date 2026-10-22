
"""
PondPulse MVP
Photo + water readings -> SAFE / WATCH / DANGER -> English alert.

Run locally:
    uvicorn app:app --reload

Open locally:
    http://127.0.0.1:8000
"""

import io
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError

app = FastAPI(
    title="PondPulse MVP",
    description="Pond water risk screening using readings and an optional photo.",
    version="1.1.0",
)

# Resolve the frontend relative to this Python file.
BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "static" / "index.html"

LEVELS = ["SAFE", "WATCH", "DANGER"]

REASON = {
    "oxygen": "Check the water's dissolved oxygen.",
    "ph": "Check the water's pH.",
    "temp": "Check the water temperature.",
    "image": "Check the pond water colour.",
}

EN = {
    "SAFE": "All looks normal. Keep monitoring.",
    "WATCH": "Early warning. Review water conditions and reduce feeding if appropriate.",
    "DANGER": (
        "High risk! Check the measurements immediately, increase aeration "
        "if appropriate, and contact a fisheries officer or water-testing lab."
    ),
}


def image_risk(data: bytes) -> float:
    """
    Placeholder image score between 0 and 1, based on colour and darkness.

    This is NOT a trained algae, fish-disease, or water-quality classifier.
    """
    with Image.open(io.BytesIO(data)) as original:
        img = original.convert("RGB").resize((64, 64))

    pixels = list(img.getdata())
    if not pixels:
        return 0.0

    count = len(pixels)
    red = sum(pixel[0] for pixel in pixels) / count
    green = sum(pixel[1] for pixel in pixels) / count
    blue = sum(pixel[2] for pixel in pixels) / count

    greenness = green - (red + blue) / 2
    darkness = 1 - (red + green + blue) / (3 * 255)

    score = greenness / 60 + darkness * 0.3
    return round(max(0.0, min(1.0, score)), 2)


def assess(
    do: Optional[float],
    ph: Optional[float],
    temp: Optional[float],
    img: Optional[float],
):
    """
    Illustrative screening thresholds only.
    Validate thresholds with fisheries experts before real-world use.
    """
    level = 0
    reasons = []

    def bump(new_level: int, reason: str):
        nonlocal level
        level = max(level, new_level)
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
    message_parts = [REASON[reason] for reason in reasons]
    message_parts.append(EN[name])
    message = " ".join(message_parts)

    return name, reasons, message


@app.get("/", response_class=FileResponse)
def home():
    """Serve the PondPulse frontend."""
    if not INDEX_FILE.is_file():
        raise HTTPException(
            status_code=500,
            detail=(
                "Frontend file not found. Expected static/index.html "
                "next to app.py."
            ),
        )

    return FileResponse(INDEX_FILE, media_type="text/html")


@app.get("/health")
def health():
    """Basic deployment health check."""
    return {
        "status": "ok",
        "frontend_found": INDEX_FILE.is_file(),
    }


@app.post("/api/assess")
async def api_assess(
    oxygen: Optional[float] = Form(None),
    ph: Optional[float] = Form(None),
    temperature: Optional[float] = Form(None),
    photo: Optional[UploadFile] = File(None),
):
    """Assess optional readings and an optional pond-water photo."""

    # Require at least one input.
    has_reading = any(
        value is not None for value in (oxygen, ph, temperature)
    )
    has_photo = photo is not None and bool(photo.filename)

    if not has_reading and not has_photo:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one water reading or a pond photo.",
        )

    # Validate numeric values.
    if oxygen is not None and oxygen < 0:
        raise HTTPException(
            status_code=422,
            detail="Dissolved oxygen cannot be negative.",
        )

    if ph is not None and not 0 <= ph <= 14:
        raise HTTPException(
            status_code=422,
            detail="pH must be between 0 and 14.",
        )

    if temperature is not None and not -10 <= temperature <= 100:
        raise HTTPException(
            status_code=422,
            detail="Temperature must be between -10 and 100 °C.",
        )

    img_score = None

    if has_photo:
        try:
            image_bytes = await photo.read()

            if not image_bytes:
                raise HTTPException(
                    status_code=400,
                    detail="The uploaded photo is empty.",
                )

            # Prevent unexpectedly large image uploads.
            max_bytes = 10 * 1024 * 1024
            if len(image_bytes) > max_bytes:
                raise HTTPException(
                    status_code=413,
                    detail="Photo must be 10 MB or smaller.",
                )

            img_score = image_risk(image_bytes)

        except UnidentifiedImageError:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is not a valid image.",
            )
        except OSError:
            raise HTTPException(
                status_code=400,
                detail="The uploaded image could not be read.",
            )
        finally:
            await photo.close()

    level, reasons, message = assess(
        oxygen,
        ph,
        temperature,
        img_score,
    )

    return {
        "risk": level,
        "reasons": reasons,
        "image_score": img_score,
        "alert": message,
        "note": (
            "Illustrative screening only; not a substitute for "
            "validated water testing or professional advice."
        ),
    }
