"""WSGI entry point for production servers such as gunicorn on Render."""

try:
    from dotenv import load_dotenv
except ImportError:  # Serverless runtimes may not bundle python-dotenv
    def load_dotenv():
        return False

load_dotenv()

from app import create_app

app = create_app()
