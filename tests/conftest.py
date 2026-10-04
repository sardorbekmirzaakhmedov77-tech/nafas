import pytest

from nafas import create_app
from nafas.config import TestConfig
from nafas.demo import seed_demo_data
from nafas.extensions import db


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def seeded(app):
    seed_demo_data()
    return app


@pytest.fixture
def client(seeded):
    return seeded.test_client()
