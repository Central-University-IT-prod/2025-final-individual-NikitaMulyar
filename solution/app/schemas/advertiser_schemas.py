from pydantic import BaseModel, Field, StrictStr, ConfigDict

import uuid


class Advertiser(BaseModel):
    advertiser_id: uuid.UUID
    name: StrictStr = Field(min_length=3)

    model_config = ConfigDict(from_attributes=True)


class AdvertiserUpsert(Advertiser):
    pass


class Ad(BaseModel):
    ad_id: uuid.UUID
    ad_title: StrictStr = Field(min_length=3)
    ad_text: StrictStr = Field(min_length=3)
    advertiser_id: uuid.UUID
