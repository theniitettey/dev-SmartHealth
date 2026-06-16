"""
Smart Health Sync — Production Entry Point
Authors: Enock Queenson Eduafo & Christabel Araba Edumadze | University of Ghana 2026

Run locally:
    python main.py

With Gunicorn (production):
    gunicorn main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120

With Waitress (Windows):
    waitress-serve --port=5000 main:app
"""

import os
from backend.factory import create_app

app = create_app()

if __name__ == "__main__":
    port  = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "development") != "production"
    app.run(host="0.0.0.0", port=port, debug=debug)
