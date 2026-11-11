# PondPulse (MVP)

Early pond health and water-quality alerts for small aquaculture farms.

Enter a pond photo and readings (dissolved oxygen, pH, temperature). PondPulse
returns a SAFE / WATCH / DANGER screening result and an English alert.

## Project structure

```text
PondPulse/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
└── static/
    └── index.html
```

## Run locally

Open this folder in VS Code, then run:

```bash
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload
```

Open http://127.0.0.1:8000

Health check: http://127.0.0.1:8000/health
API documentation: http://127.0.0.1:8000/docs

## Important limitations

The photo score is a simple colour heuristic, not a trained ML model or disease
classifier. The water-quality thresholds are illustrative and must be validated
with fisheries experts and local water-testing guidance. This prototype is not
a substitute for professional testing or advice.
