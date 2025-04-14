import uuid

from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from .db_session import SqlAlchemyBase


class MLScore(SqlAlchemyBase):
    __tablename__ = 'ml_scores'
    ml_score_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.client_id"))
    advertiser_id = Column(UUID(as_uuid=True), ForeignKey("advertisers.advertiser_id"))
    score = Column(Integer, nullable=False)

    advertiser = relationship("Advertiser", back_populates="ml_scores", uselist=False)
    client = relationship("Client", back_populates="ml_scores", uselist=False)
