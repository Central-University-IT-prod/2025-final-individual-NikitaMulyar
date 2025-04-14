import uuid

from sqlalchemy.orm import relationship
from sqlalchemy import Column, Float, String, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from .db_session import SqlAlchemyBase


class Action(SqlAlchemyBase):
    __tablename__ = 'actions'
    action_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.client_id"))
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.campaign_id"))
    cost = Column(Float, nullable=False)
    action = Column(String, nullable=False)
    day = Column(Integer, nullable=False)

    campaign = relationship("Campaign", back_populates="actions", uselist=False)
    client = relationship("Client", back_populates="actions", uselist=False)
