"""Single set of Flask extension instances shared by the whole application.

The instances live here (rather than in the application factory) so domain and
infrastructure modules can import them without importing ``create_app``.  They
are still initialised exactly once, by :func:`app.create_app`.
"""

from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
