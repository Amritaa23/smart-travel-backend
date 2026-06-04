# Import all models here so SQLAlchemy Base.metadata knows about
# all tables before create_tables() is called at startup.
from models.user import User          # noqa: F401
from models.otp import OTP            # noqa: F401
from models.saved_place import SavedPlace  # noqa: F401
