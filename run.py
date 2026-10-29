"""Development entry point: python run.py"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    # Debug flag comes from config (FLASK_ENV=development => DEBUG=True).
    # Never enable debug mode in production.
    app.run(host="0.0.0.0", port=5000)
