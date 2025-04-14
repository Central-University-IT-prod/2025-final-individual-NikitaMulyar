from pydantic import BaseModel, Field, StrictStr, StrictInt, ConfigDict

from .gender_schemas import Gender

import uuid


class Client(BaseModel):
    client_id: uuid.UUID
    login: StrictStr = Field(min_length=3)
    age: StrictInt = Field(ge=0, le=100)
    location: StrictStr = Field(min_length=3)
    gender: Gender

    model_config = ConfigDict(from_attributes=True)


class ClientUpsert(Client):
    pass


class MLScore(BaseModel):
    client_id: uuid.UUID
    advertiser_id: uuid.UUID
    score: StrictInt = Field(ge=0)

    model_config = ConfigDict(from_attributes=True)


class ClientUUID(BaseModel):
    client_id: uuid.UUID
