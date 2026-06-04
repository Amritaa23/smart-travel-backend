from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from database.session import Base


class OTP(Base):
    __tablename__ = "otps"

    id         = Column(String, primary_key=True)
    user_id    = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    email      = Column(String, nullable=False, index=True)
    code       = Column(String(6), nullable=False)
    purpose    = Column(String, nullable=False)   # verify_email | login | reset_password
    expires_at = Column(DateTime, nullable=False)
    used       = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="otps")

    def __repr__(self) -> str:
        return f"<OTP {self.email} purpose={self.purpose} used={self.used}>"
