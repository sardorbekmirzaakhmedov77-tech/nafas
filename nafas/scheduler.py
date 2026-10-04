"""Hourly background job: refresh data, then check alerts."""

import logging
import threading

from apscheduler.schedulers.background import BackgroundScheduler

log = logging.getLogger(__name__)
_scheduler = None


def refresh(app):
    from .alerts import check_alerts
    from .collector import collect_all

    with app.app_context():
        summary = collect_all()
        sent = check_alerts()
        log.info("Refresh done: %s cities ok, %s failed, %s alerts sent",
                 len(summary["ok"]), len(summary["failed"]), sent)


def start(app):
    """Start the hourly jobs once per process.

    Called from run.py (development) and wsgi.py (production). With gunicorn,
    use a single worker so jobs don't run in several processes at once.
    """
    global _scheduler
    if _scheduler is not None or not app.config["ENABLE_SCHEDULER"]:
        return

    _scheduler = BackgroundScheduler(timezone=app.config["TIMEZONE"])
    # Open-Meteo updates hourly; minute 7 gives it time to publish.
    _scheduler.add_job(refresh, "cron", minute=7, args=[app], id="refresh",
                       max_instances=1, coalesce=True)
    _scheduler.start()

    # Fill an empty database right away instead of waiting for the next hour.
    threading.Thread(target=refresh, args=[app], daemon=True).start()
    log.info("Scheduler started")
