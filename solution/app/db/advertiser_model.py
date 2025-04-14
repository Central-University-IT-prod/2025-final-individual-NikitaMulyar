import uuid

from sqlalchemy.orm import relationship
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from .db_session import SqlAlchemyBase


class Advertiser(SqlAlchemyBase):
    __tablename__ = 'advertisers'
    advertiser_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)

    ml_scores = relationship("MLScore", back_populates="advertiser",
                             cascade="all, delete", uselist=True)
    campaigns = relationship("Campaign", back_populates="advertiser",
                             cascade="all, delete", uselist=True)
