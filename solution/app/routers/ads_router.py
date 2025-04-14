import random
from typing import Annotated, Sequence

from fastapi import APIRouter, Body, Path, Depends, HTTPException, Request, Query
from sqlalchemy.orm import selectinload
from starlette import status

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.db_session import create_session
from ..db import client_model
from ..db import action_model
from ..db import campaign_model

from ..schemas.advertiser_schemas import Ad
from ..schemas.client_schemas import ClientUUID

from ..redis import redis_client

import uuid


router = APIRouter(tags=["Ads"])


# async def target_campaigns(campaigns_all: Sequence[campaign_model.Campaign], client: client_model.Client):
#     ok_campaigns = []
#     for campaign in campaigns_all:
#         if campaign.targeting.get('gender') in ['MALE', 'FEMALE']:
#             if campaign.targeting['gender'] != client.gender:
#                 continue
#         if campaign.targeting.get('age_from') is not None and campaign.targeting['age_from'] > client.age:
#             continue
#         if campaign.targeting.get('age_to') is not None and campaign.targeting['age_to'] < client.age:
#             continue
#         if campaign.targeting.get('location') is not None and campaign.targeting['location'] != client.location:
#             continue
#
#         ok_campaigns.append(campaign)
#     return ok_campaigns


async def filter_campaigns(campaigns_all: Sequence[campaign_model.Campaign], client: client_model.Client):
    can_impression_campaigns = []
    can_click_campaigns = []
    show_again_campaigns = []

    impression_campaigns_actions = set()
    click_campaigns_actions = set()
    for action in client.actions:
        if action.action == 'impression':
            impression_campaigns_actions.add(action.campaign_id)
        if action.action == 'click':
            click_campaigns_actions.add(action.campaign_id)

    for campaign in campaigns_all:
        impressioned = campaign.campaign_id in impression_campaigns_actions
        clicked = campaign.campaign_id in click_campaigns_actions

        if campaign.current_impressions < campaign.impressions_limit and \
            campaign.current_clicks < campaign.clicks_limit and not impressioned:
            can_impression_campaigns.append(campaign)
        elif campaign.current_clicks < campaign.clicks_limit and not clicked:
            can_click_campaigns.append(campaign)
        elif clicked:
            show_again_campaigns.append(campaign)

    return can_impression_campaigns, can_click_campaigns, show_again_campaigns


async def calc_combined_scores(campaigns_all: list[campaign_model.Campaign], client: client_model.Client):
    alpha = 0.8
    beta = 0.2

    campaigns_data = []
    max_ml = 0
    max_profit = 0

    ml_scores = {cur_score.advertiser_id: cur_score.score for cur_score in client.ml_scores}

    for campaign in campaigns_all:
        ctr_numerator = campaign.current_clicks + 1
        ctr_denominator = campaign.current_impressions + 2
        ctr = ctr_numerator / ctr_denominator

        profit = campaign.cost_per_impression + campaign.cost_per_click * ctr

        campaigns_data.append({
            'campaign': campaign,
            'ml': ml_scores.get(campaign.advertiser_id, 0),
            'profit': profit,
            'ctr': ctr
        })

        max_ml = max(max_ml, ml_scores.get(campaign.advertiser_id, 0))
        max_profit = max(max_profit, profit)

    for data in campaigns_data:
        normalized_ml = (data['ml'] / max_ml) if max_ml != 0 else 0
        normalized_profit = (data['profit'] / max_profit) if max_profit != 0 else 0
        data['score'] = alpha * normalized_profit + beta * normalized_ml

    return sorted([(d['campaign'], d['score']) for d in campaigns_data],
                  key=lambda x: x[1], reverse=True)


@router.get("/ads", response_model=Ad)
async def get_ad_for_client(request: Request,
                            client_id: Annotated[uuid.UUID, Query()],
                            session: AsyncSession = Depends(create_session)):
    client = await session.execute(select(client_model.Client)
                                   .options(selectinload(client_model.Client.actions))
                                   .options(selectinload(client_model.Client.ml_scores))
                                   .where(client_model.Client.client_id == client_id))
    client = client.scalar_one_or_none()
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    current_day = await redis_client.get_day(request.app.state.redis)

    campaigns_all = await session.execute(select(campaign_model.Campaign)
                                          .filter(campaign_model.Campaign.start_date <= current_day,
                                                  current_day <= campaign_model.Campaign.end_date,
                                                  or_(
                                                      campaign_model.Campaign.targeting['gender'].is_(None),
                                                      ~campaign_model.Campaign.targeting['gender'].astext.in_(['MALE', 'FEMALE']),
                                                      campaign_model.Campaign.targeting['gender'].astext == client.gender
                                                  ),
                                                  or_(
                                                      campaign_model.Campaign.targeting['age_from'].is_(None),
                                                      campaign_model.Campaign.targeting['age_from'].as_integer() <= client.age
                                                  ),
                                                  or_(
                                                      campaign_model.Campaign.targeting['age_to'].is_(None),
                                                      campaign_model.Campaign.targeting['age_to'].as_integer() >= client.age
                                                  ),
                                                  or_(
                                                      campaign_model.Campaign.targeting['location'].is_(None),
                                                      campaign_model.Campaign.targeting['location'].astext == client.location
                                                  )
                                                  ))
    ok_campaigns = campaigns_all.scalars().all()

    if len(ok_campaigns) == 0:
        raise HTTPException(status_code=404, detail="No campaigns found")

    can_impression_campaigns, can_click_campaigns, show_again_campaigns = \
        await filter_campaigns(ok_campaigns, client)
    if len(can_impression_campaigns) > 0:
        calculated_campaigns = await calc_combined_scores(can_impression_campaigns, client)
        choiced = calculated_campaigns[0][0]
        choiced.current_impressions += 1
        new_action = action_model.Action(
            client_id=client.client_id,
            campaign_id=choiced.campaign_id,
            cost=choiced.cost_per_impression,
            action='impression',
            day=current_day
        )
        session.add(new_action)
        await session.commit()
    elif len(can_click_campaigns) > 0:
        calculated_campaigns = await calc_combined_scores(can_click_campaigns, client)
        choiced = calculated_campaigns[0][0]
    elif len(show_again_campaigns) > 0:
        choiced = random.choice(show_again_campaigns)
    else:
        raise HTTPException(status_code=404, detail="No campaigns found")

    return {'ad_id': choiced.campaign_id, 'ad_title': choiced.ad_title, 'ad_text': choiced.ad_text,
            'advertiser_id': choiced.advertiser_id}


@router.post("/ads/{ad_id}/click", status_code=status.HTTP_204_NO_CONTENT)
async def set_ed_click(request: Request, ad_id: Annotated[uuid.UUID, Path()],
                       data: Annotated[ClientUUID, Body()], session: AsyncSession = Depends(create_session)):
    campaign = await session.execute(select(campaign_model.Campaign)
                                     .where(campaign_model.Campaign.campaign_id == ad_id))
    campaign = campaign.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    client = await session.execute(select(client_model.Client).where(client_model.Client.client_id == data.client_id))
    client = client.scalar_one_or_none()
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    current_day = await redis_client.get_day(request.app.state.redis)

    impressioned = await session.execute(select(action_model.Action)
                                         .filter(action_model.Action.client_id == client.client_id,
                                                 action_model.Action.campaign_id == campaign.campaign_id,
                                                 action_model.Action.action == 'impression'))
    impressioned = impressioned.scalar_one_or_none()

    if impressioned is None:
        raise HTTPException(status_code=403, detail="Campaign must be seen before click")

    clicked = await session.execute(select(action_model.Action)
                                    .filter(action_model.Action.client_id == client.client_id,
                                            action_model.Action.campaign_id == campaign.campaign_id,
                                            action_model.Action.action == 'click'))
    clicked = clicked.scalar_one_or_none()

    if clicked is None:
        campaign.current_clicks += 1
        new_action = action_model.Action(
            client_id=client.client_id,
            campaign_id=campaign.campaign_id,
            cost=campaign.cost_per_click,
            action='click',
            day=current_day
        )
        session.add(new_action)
        await session.commit()
