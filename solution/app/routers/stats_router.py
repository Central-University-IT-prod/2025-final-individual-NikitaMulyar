from typing import Annotated

from fastapi import APIRouter, Body, Path, Depends, HTTPException, Request

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db.db_session import create_session
from ..db import advertiser_model
from ..db import campaign_model

from ..schemas.stats_schemas import DateSetting, Stats, DailyStats

from ..redis import redis_client

import uuid


router = APIRouter(tags=["Statistics and Time"])


@router.post("/time/advance", response_model=DateSetting)
async def set_new_day(request: Request, new_day: Annotated[DateSetting, Body()]):
    current_day = await redis_client.get_day(request.app.state.redis)
    if new_day.current_date < current_day:
        raise HTTPException(status_code=400, detail=f"Day must be current day or later")

    await redis_client.set_day(request.app.state.redis, new_day.current_date)
    return new_day


@router.get("/stats/campaigns/{campaign_id}", response_model=Stats)
async def get_campaign_stats(campaign_id: Annotated[uuid.UUID, Path()],
                             session: AsyncSession = Depends(create_session)):
    campaign = await session.execute(select(campaign_model.Campaign)
                                     .options(selectinload(campaign_model.Campaign.actions))
                                     .where(campaign_model.Campaign.campaign_id == campaign_id))
    campaign = campaign.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    clicks_cost = 0
    impressions_cost = 0
    for action in campaign.actions:
        if action.action == 'click':
            clicks_cost += action.cost
        else:
            impressions_cost += action.cost
    d = {
        'impressions_count': campaign.current_impressions,
        'clicks_count': campaign.current_clicks,
        'spent_impressions': impressions_cost,
        'spent_clicks': clicks_cost,
        'spent_total': impressions_cost + clicks_cost
    }
    if campaign.current_impressions > 0:
        d['conversion'] = campaign.current_clicks / campaign.current_impressions
    else:
        d['conversion'] = 0
    return d


@router.get("/stats/campaigns/{campaign_id}/daily", response_model=list[DailyStats])
async def get_campaign_daily_stats(campaign_id: Annotated[uuid.UUID, Path()],
                                   session: AsyncSession = Depends(create_session)):
    campaign = await session.execute(select(campaign_model.Campaign)
                                     .options(selectinload(campaign_model.Campaign.actions))
                                     .where(campaign_model.Campaign.campaign_id == campaign_id))
    campaign = campaign.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    daily_stats = {}
    for action in campaign.actions:
        if action.day not in daily_stats:
            daily_stats[action.day] = {
                'impressions_count': 0,
                'clicks_count': 0,
                'spent_impressions': 0,
                'spent_clicks': 0
            }
        if action.action == 'click':
            daily_stats[action.day]['spent_clicks'] += action.cost
            daily_stats[action.day]['clicks_count'] += 1
        else:
            daily_stats[action.day]['spent_impressions'] += action.cost
            daily_stats[action.day]['impressions_count'] += 1
    result = []
    for day in daily_stats:
        d = {
            'date': day,
            'impressions_count': daily_stats[day]['impressions_count'],
            'clicks_count': daily_stats[day]['clicks_count'],
            'spent_impressions': daily_stats[day]['spent_impressions'],
            'spent_clicks': daily_stats[day]['spent_clicks'],
            'spent_total': daily_stats[day]['spent_impressions'] + daily_stats[day]['spent_clicks']
        }
        if daily_stats[day]['impressions_count'] > 0:
            d['conversion'] = daily_stats[day]['clicks_count'] / daily_stats[day]['impressions_count']
        else:
            d['conversion'] = 0
        result.append(d)
    return sorted(result, key=lambda d: d['date'])


@router.get("/stats/advertisers/{advertiser_id}/campaigns", response_model=Stats)
async def get_campaigns_stats_for_advertiser(advertiser_id: Annotated[uuid.UUID, Path()],
                                             session: AsyncSession = Depends(create_session)):
    advertiser_exists = await session.execute(select(advertiser_model.Advertiser)
                                              .options(selectinload(advertiser_model.Advertiser.campaigns))
                                              .options(selectinload(campaign_model.Campaign.actions))
                                              .where(advertiser_model.Advertiser.advertiser_id == advertiser_id))
    advertiser_exists = advertiser_exists.scalar_one_or_none()
    if advertiser_exists is None:
        raise HTTPException(status_code=404, detail="Advertiser not found")

    impressions_count = 0
    clicks_count = 0
    spent_impressions = 0
    spent_clicks = 0

    for campaign in advertiser_exists.campaigns:
        for action in campaign.actions:
            if action.action == 'click':
                spent_clicks += action.cost
            else:
                spent_impressions += action.cost
        impressions_count += campaign.current_impressions
        clicks_count += campaign.current_clicks

    d = {
        'impressions_count': impressions_count,
        'clicks_count': clicks_count,
        'spent_impressions': spent_impressions,
        'spent_clicks': spent_clicks,
        'spent_total': spent_impressions + spent_clicks
    }
    if impressions_count > 0:
        d['conversion'] = clicks_count / impressions_count
    else:
        d['conversion'] = 0
    return d


@router.get("/stats/advertisers/{advertiser_id}/campaigns/daily", response_model=list[DailyStats])
async def get_campaign_daily_stats_for_advertiser(advertiser_id: Annotated[uuid.UUID, Path()],
                                                  session: AsyncSession = Depends(create_session)):
    advertiser_exists = await session.execute(select(advertiser_model.Advertiser)
                                              .options(selectinload(advertiser_model.Advertiser.campaigns))
                                              .options(selectinload(campaign_model.Campaign.actions))
                                              .where(advertiser_model.Advertiser.advertiser_id == advertiser_id))
    advertiser_exists = advertiser_exists.scalar_one_or_none()
    if advertiser_exists is None:
        raise HTTPException(status_code=404, detail="Advertiser not found")

    daily_stats = {}
    for campaign in advertiser_exists.campaigns:
        for action in campaign.actions:
            if action.day not in daily_stats:
                daily_stats[action.day] = {
                    'impressions_count': 0,
                    'clicks_count': 0,
                    'spent_impressions': 0,
                    'spent_clicks': 0
                }
            if action.action == 'click':
                daily_stats[action.day]['spent_clicks'] += action.cost
                daily_stats[action.day]['clicks_count'] += 1
            else:
                daily_stats[action.day]['spent_impressions'] += action.cost
                daily_stats[action.day]['impressions_count'] += 1
    result = []
    for day in daily_stats:
        d = {
            'date': day,
            'impressions_count': daily_stats[day]['impressions_count'],
            'clicks_count': daily_stats[day]['clicks_count'],
            'spent_impressions': daily_stats[day]['spent_impressions'],
            'spent_clicks': daily_stats[day]['spent_clicks'],
            'spent_total': daily_stats[day]['spent_impressions'] + daily_stats[day]['spent_clicks']
        }
        if daily_stats[day]['impressions_count'] > 0:
            d['conversion'] = daily_stats[day]['clicks_count'] / daily_stats[day]['impressions_count']
        else:
            d['conversion'] = 0
        result.append(d)
    return sorted(result, key=lambda d: d['date'])
