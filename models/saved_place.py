from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, Text
from sqlalchemy.orm import relationship

from database.session import Base


class SavedPlace(Base):
    __tablename__ = "saved_places"
    __table_args__ = (
        UniqueConstraint("user_id", "place", name="uq_user_place"),
    )

    id       = Column(String, primary_key=True)
    user_id  = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    place    = Column(String, nullable=False)   # canonical casing from dataset
    note     = Column(Text, default="", nullable=False)
    saved_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="saved_places")

    def __repr__(self) -> str:
        return f"<SavedPlace {self.place} user={self.user_id}>"
