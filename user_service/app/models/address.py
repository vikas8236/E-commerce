

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, func
from app.db.base import Base

class Address(Base):
    __tablename__ = "addresses"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    street = Column(String, nullable=True)
    city = Column(String, nullable=False)
    state = Column(String, nullable = False)
    zip_code = Column(String, nullable=False)
    country = Column(String, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=func.now())
