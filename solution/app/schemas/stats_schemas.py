from pydantic import BaseModel, Field, StrictInt, StrictFloat


class Stats(BaseModel):
    impressions_count: StrictInt = Field(ge=0)
    clicks_count: StrictInt = Field(ge=0)
    conversion: StrictFloat = Field(ge=0)
    spent_impressions: StrictFloat = Field(ge=0)
    spent_clicks: StrictFloat = Field(ge=0)
    spent_total: StrictFloat = Field(ge=0)


class DailyStats(Stats):
    date: StrictInt = Field(ge=0)


class DateSetting(BaseModel):
    current_date: StrictInt = Field(ge=0)
