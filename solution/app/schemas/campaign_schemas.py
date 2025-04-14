from typing import Optional

from pydantic import BaseModel, Field, field_validator, StrictStr, StrictInt, StrictFloat, ConfigDict

from .gender_schemas import GenderALL

import uuid


class Targeting(BaseModel):
    gender: Optional[GenderALL] = Field(default=None)
    age_from: Optional[StrictInt] = Field(default=None, ge=0)
    age_to: Optional[StrictInt] = Field(default=None, le=100)
    location: Optional[StrictStr] = Field(default=None, min_length=3)

    @classmethod
    @field_validator("age_to", mode="after")
    def check_age_range(cls, age_to, values):
        age_from = values.get("age_from")
        if age_from is not None and age_to is not None and age_from > age_to:
            raise ValueError("Age from must be age to or less")
        return age_to


class CampaignCreate(BaseModel):
    impressions_limit: StrictInt = Field(ge=0)
    clicks_limit: StrictInt = Field(ge=0)
    cost_per_impression: StrictFloat = Field(ge=0)
    cost_per_click: StrictFloat = Field(ge=0)
    ad_title: StrictStr = Field(min_length=3)
    ad_text: StrictStr = Field(min_length=3)
    start_date: StrictInt = Field(ge=0)
    end_date: StrictInt = Field(ge=0)
    targeting: Targeting

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    @field_validator("end_date", mode="after")
    def check_date_range(cls, end_date, values):
        start_date = values.get("start_date")
        if start_date is not None and end_date is not None and start_date > end_date:
            raise ValueError("Start date must be end date or earlier")
        return end_date


class Campaign(CampaignCreate):
    campaign_id: uuid.UUID
    advertiser_id: uuid.UUID


class CampaignUpdate(CampaignCreate):
    impressions_limit: Optional[StrictInt] = Field(default=None, ge=0)
    clicks_limit: Optional[StrictInt] = Field(default=None, ge=0)
    cost_per_impression: Optional[StrictFloat] = Field(default=None, ge=0)
    cost_per_click: Optional[StrictFloat] = Field(default=None, ge=0)
    ad_title: Optional[StrictStr] = Field(default=None, min_length=3)
    ad_text: Optional[StrictStr] = Field(default=None, min_length=3)
    start_date: Optional[StrictInt] = Field(default=None, ge=0)
    end_date: Optional[StrictInt] = Field(default=None, ge=0)
