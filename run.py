"""Development server: python run.py"""

import os

from dotenv import load_dotenv

load_dotenv()  # read settings from .env before the app reads its config

from nafas import create_app, scheduler  # noqa: E402

app = create_app()

if __name__ == "__main__":
    # Flask's auto-reloader runs this file in two processes: a file watcher and
    # the actual server. Only the server (WERKZEUG_RUN_MAIN=true) runs the jobs.
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        scheduler.start(app)
    app.run(debug=True)
