import uuid

from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from .db_session import SqlAlchemyBase


class Campaign(SqlAlchemyBase):
    __tablename__ = 'campaigns'
    campaign_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    advertiser_id = Column(UUID(as_uuid=True), ForeignKey("advertisers.advertiser_id"))
    impressions_limit = Column(Integer, nullable=False)
    clicks_limit = Column(Integer, nullable=False)
    cost_per_impression = Column(Float, nullable=False)
    cost_per_click = Column(Float, nullable=False)
    ad_title = Column(String, nullable=False)
    ad_text = Column(String, nullable=False)
    start_date = Column(Integer, nullable=False)
    end_date = Column(Integer, nullable=False)
    targeting = Column(JSON, nullable=False)

    current_impressions = Column(Integer, default=0)
    current_clicks = Column(Integer, default=0)

    advertiser = relationship("Advertiser", back_populates="campaigns", uselist=False)
    actions = relationship("Action", back_populates="campaign",
                           cascade="all, delete", uselist=True)
