import logging
import os

from dotenv import load_dotenv
from quart import Quart


def create_app(testing=False):
    # We do this here in addition to gunicorn.conf.py, since we don't always use gunicorn
    if not testing:
        load_dotenv(override=True)

    if os.getenv("RUNNING_IN_PRODUCTION"):
        logging.basicConfig(level=logging.WARNING)
    else:
        logging.basicConfig(level=logging.INFO)

    app = Quart(__name__)

    from . import chat  # noqa

    app.register_blueprint(chat.bp)

    return app
