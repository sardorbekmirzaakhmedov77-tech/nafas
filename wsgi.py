"""Production entry point: gunicorn wsgi:app"""

from dotenv import load_dotenv

load_dotenv()

from nafas import create_app, scheduler  # noqa: E402

app = create_app()
scheduler.start(app)
