# PondPulse (MVP)

Early disease and water-quality alerts for small aquaculture farms (Sahyadri DevHack 2026, PS 1.1).

A farmer enters a pond photo and readings (oxygen, pH, temperature). PondPulse returns a
Safe / Watch / Danger risk and an English alert with the next action.

## Run
    pip install -r requirements.txt
    uvicorn app:app --reload
Open http://127.0.0.1:8000

## How it works
1. `image_risk()` scores the pond photo (placeholder colour heuristic, to be replaced by a trained model)
2. `assess()` checks readings against illustrative thresholds and combines everything into one risk class
3. An alert message with the next action is returned

## Next steps
- Train an image classifier on public pond / disease datasets
- Add WhatsApp / SMS delivery
- Add Open-Meteo rainfall data to the risk engine
- Tune thresholds with open water-quality data and expert advice

Team Kryptonix, Yenepoya Institute of Technology, Moodbidri
