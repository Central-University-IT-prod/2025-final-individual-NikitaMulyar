from typing import Annotated, Optional

from fastapi import APIRouter, Body, Path, Query, Depends, HTTPException, Request
from starlette import status

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.db_session import create_session
from ..db import advertiser_model
from ..db import campaign_model

from ..schemas.campaign_schemas import Campaign, CampaignCreate, CampaignUpdate

from ..redis import redis_client

import uuid

from g4f.client import Client


router = APIRouter(tags=["Campaigns"])


def create_llm_text(title: str):
    client = Client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user",
             "content": f"Привет! Напиши, пожалуйста, небольшой (до 5 предложений) рекламный текст "
                        f"для \"{title}\". Я хочу получить ТОЛЬКО текст рекламы. Спасибо заранее."
             }
        ],
        web_search=False, ignore_stream=True, ignore_working=True
    )
    return response.choices[0].message.content


@router.post("/advertisers/{advertiser_id}/campaigns", status_code=status.HTTP_201_CREATED, response_model=Campaign)
async def create_campaign(request: Request,
                          advertiser_id: Annotated[uuid.UUID, Path()],
                          data: Annotated[CampaignCreate, Body()],
                          llm: Annotated[Optional[int], Query()] = None,
                          session: AsyncSession = Depends(create_session)):
    advertiser_exists = await session.execute(select(advertiser_model.Advertiser)
                                              .where(advertiser_model.Advertiser.advertiser_id == advertiser_id))
    advertiser_exists = advertiser_exists.scalar_one_or_none()
    if advertiser_exists is None:
        raise HTTPException(status_code=404, detail="Advertiser not found")

    current_day = await redis_client.get_day(request.app.state.redis)

    if not (current_day <= data.start_date <= data.end_date):
        raise HTTPException(status_code=400,
                            detail="Start date must be current day or later. End date must be start date or later")

    d = {
        'gender': data.targeting.gender,
        'age_from': data.targeting.age_from,
        'age_to': data.targeting.age_to,
        'location': data.targeting.location
    }

    new_campaign = campaign_model.Campaign(
        campaign_id=uuid.uuid4(),
        advertiser_id=advertiser_id,
        impressions_limit=data.impressions_limit,
        clicks_limit=data.clicks_limit,
        cost_per_impression=data.cost_per_impression,
        cost_per_click=data.cost_per_click,
        ad_title=data.ad_title,
        ad_text=data.ad_text,
        start_date=data.start_date,
        end_date=data.end_date,
        targeting=d
    )
    if llm is not None:
        attempts = 3
        while True:
            try:
                new_campaign.ad_text = create_llm_text(data.ad_title)
                break
            except Exception:
                attempts -= 1
                if attempts == 0:
                    raise HTTPException(status_code=500, detail="Error due creating llm text")

    session.add(new_campaign)
    await session.commit()
    return new_campaign


@router.get("/advertisers/{advertiser_id}/campaigns", response_model=list[Campaign])
async def get_campaigns_by_author(advertiser_id: Annotated[uuid.UUID, Path()],
                                  size: Annotated[Optional[int], Query(gt=1)] = None,
                                  page: Annotated[Optional[int], Query(gt=1)] = None,
                                  session: AsyncSession = Depends(create_session)):
    advertiser_exists = await session.execute(select(advertiser_model.Advertiser)
                                              .where(advertiser_model.Advertiser.advertiser_id == advertiser_id))
    advertiser_exists = advertiser_exists.scalar_one_or_none()
    if advertiser_exists is None:
        raise HTTPException(status_code=404, detail="Advertiser not found")

    query = ((select(campaign_model.Campaign)
             .where(campaign_model.Campaign.advertiser_id == advertiser_id))
             .order_by(campaign_model.Campaign.start_date))

    if size is None and page is None or size is None and page is not None:
        result = await session.execute(query)
        result = result.scalars().all()
    elif size is not None and page is None:
        result = await session.execute(query.limit(size))
        result = result.scalars().all()
    else:
        result = await session.execute(query.offset((page - 1) * size).limit(size))
        result = result.scalars().all()
    return result


@router.get("/advertisers/{advertiser_id}/campaigns/{campaign_id}", response_model=Campaign)
async def get_campaign(advertiser_id: Annotated[uuid.UUID, Path()],
                       campaign_id: Annotated[uuid.UUID, Path()],
                       session: AsyncSession = Depends(create_session)):
    campaign_exists = await session.execute(select(campaign_model.Campaign)
                                            .filter(campaign_model.Campaign.campaign_id == campaign_id,
                                                    campaign_model.Campaign.advertiser_id == advertiser_id))
    campaign_exists = campaign_exists.scalar_one_or_none()
    if campaign_exists is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return campaign_exists


@router.put("/advertisers/{advertiser_id}/campaigns/{campaign_id}", response_model=Campaign)
async def update_campaign(request: Request,
                          advertiser_id: Annotated[uuid.UUID, Path()],
                          campaign_id: Annotated[uuid.UUID, Path()],
                          data: Annotated[CampaignUpdate, Body()],
                          llm: Annotated[Optional[int], Query()] = None,
                          session: AsyncSession = Depends(create_session)):
    campaign_exists = await session.execute(select(campaign_model.Campaign)
                                            .filter(campaign_model.Campaign.campaign_id == campaign_id,
                                                    campaign_model.Campaign.advertiser_id == advertiser_id))
    campaign_exists = campaign_exists.scalar_one_or_none()
    if campaign_exists is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    current_day = await redis_client.get_day(request.app.state.redis)

    if campaign_exists.start_date <= current_day:
        if data.start_date is not None or data.end_date is not None:
            raise HTTPException(status_code=400, detail="Forbidden to update dates after campaign start")
        if data.impressions_limit is not None or data.clicks_limit is not None:
            raise HTTPException(status_code=400,
                                detail="Forbidden to update impressions or clicks limits after campaign start")

    current_start_date = campaign_exists.start_date
    if data.start_date is not None:
        current_start_date = data.start_date
    current_end_date = campaign_exists.end_date
    if data.end_date is not None:
        current_end_date = data.end_date

    if not (current_day <= current_start_date <= current_end_date):
        raise HTTPException(status_code=400,
                            detail="Start date must be current day or later. End date must be start date or later")

    campaign_exists.start_date = current_start_date
    campaign_exists.end_date = current_end_date

    if data.impressions_limit is not None:
        campaign_exists.impressions_limit = data.impressions_limit
    if data.clicks_limit is not None:
        campaign_exists.clicks_limit = data.clicks_limit

    if data.cost_per_impression is not None:
        campaign_exists.cost_per_impression = data.cost_per_impression
    if data.cost_per_click is not None:
        campaign_exists.cost_per_click = data.cost_per_click
    if data.ad_title is not None:
        campaign_exists.ad_title = data.ad_title
    if data.ad_text is not None:
        campaign_exists.ad_text = data.ad_text

    if llm is not None:
        attempts = 3
        while True:
            try:
                campaign_exists.ad_text = create_llm_text(campaign_exists.ad_title)
                break
            except Exception:
                attempts -= 1
                if attempts == 0:
                    raise HTTPException(status_code=500, detail="Error due creating llm text")

    campaign_exists.targeting['gender'] = data.targeting.gender
    campaign_exists.targeting['age_from'] = data.targeting.age_from
    campaign_exists.targeting['age_to'] = data.targeting.age_to
    campaign_exists.targeting['location'] = data.targeting.location
    await session.commit()
    return campaign_exists


@router.delete("/advertisers/{advertiser_id}/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(advertiser_id: Annotated[uuid.UUID, Path()],
                          campaign_id: Annotated[uuid.UUID, Path()],
                          session: AsyncSession = Depends(create_session)):
    campaign_exists = await session.execute(select(campaign_model.Campaign)
                                            .filter(campaign_model.Campaign.campaign_id == campaign_id,
                                                    campaign_model.Campaign.advertiser_id == advertiser_id))
    campaign_exists = campaign_exists.scalar_one_or_none()
    if campaign_exists is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    await session.delete(campaign_exists)
    await session.commit()
