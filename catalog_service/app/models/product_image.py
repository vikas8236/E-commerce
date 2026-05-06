from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    url = Column(String, nullable=False)
    alt_text = Column(String, nullable=True)
    position = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=func.now())

    product = relationship("Product", back_populates="images")
