import uuid

from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, Integer
from sqlalchemy.dialects.postgresql import UUID

from .db_session import SqlAlchemyBase


class Client(SqlAlchemyBase):
    __tablename__ = 'clients'
    client_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    login = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    location = Column(String, nullable=False)
    gender = Column(String, nullable=True)

    ml_scores = relationship("MLScore", back_populates="client",
                             cascade="all, delete", uselist=True)
    actions = relationship("Action", back_populates="client",
                           cascade="all, delete", uselist=True)
