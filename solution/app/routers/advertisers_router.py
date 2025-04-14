from typing import Annotated

from fastapi import APIRouter, Body, Path, Depends, HTTPException
from starlette import status

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.db_session import create_session
from ..db import advertiser_model
from ..db import ml_score_model
from ..db import client_model

from ..schemas.advertiser_schemas import AdvertiserUpsert, Advertiser
from ..schemas.client_schemas import MLScore

import uuid


router = APIRouter(tags=["Advertisers"])


@router.post("/advertisers/bulk", status_code=status.HTTP_201_CREATED, response_model=list[Advertiser])
async def create_advertisers(advertisers: Annotated[list[AdvertiserUpsert], Body()],
                             session: AsyncSession = Depends(create_session)):
    uuids_array = []
    for data in advertisers:
        uuids_array.append(data.advertiser_id)
    if len(uuids_array) != len(set(uuids_array)):
        raise HTTPException(status_code=400, detail="UUID are not unique")

    for data in advertisers:
        result = await session.execute(select(advertiser_model.Advertiser)
                                       .where(advertiser_model.Advertiser.advertiser_id == data.advertiser_id))
        advertiser = result.scalar_one_or_none()
        if advertiser is None:
            new_advertiser = advertiser_model.Advertiser(
                advertiser_id=data.advertiser_id,
                name=data.name
            )
            session.add(new_advertiser)
        else:
            advertiser.name = data.name
        await session.commit()
    return advertisers


@router.get("/advertisers/{advertiser_id}", response_model=Advertiser)
async def get_advertiser_by_uuid(advertiser_id: Annotated[uuid.UUID, Path()],
                                 session: AsyncSession = Depends(create_session)):
    result = await session.execute(select(advertiser_model.Advertiser)
                                   .where(advertiser_model.Advertiser.advertiser_id == advertiser_id))
    advertiser = result.scalar_one_or_none()
    if advertiser is None:
        raise HTTPException(status_code=404, detail="Advertiser not found")

    return advertiser


@router.post("/ml-scores", response_model=MLScore)
async def create_ml_score(ml_score: Annotated[MLScore, Body()],
                          session: AsyncSession = Depends(create_session)):
    client_exists = await session.execute(select(client_model.Client)
                                          .where(client_model.Client.client_id == ml_score.client_id))
    advertiser_exists = await session.execute(select(advertiser_model.Advertiser)
                                              .where(advertiser_model.Advertiser.advertiser_id == ml_score.advertiser_id))
    client_exists = client_exists.scalar_one_or_none()
    advertiser_exists = advertiser_exists.scalar_one_or_none()
    if client_exists is None or advertiser_exists is None:
        raise HTTPException(status_code=404, detail="Advertiser or Client not found")

    result = await session.execute(select(ml_score_model.MLScore)
                                   .filter(ml_score_model.MLScore.client_id == ml_score.client_id,
                                           ml_score_model.MLScore.advertiser_id == ml_score.advertiser_id))
    data = result.scalar_one_or_none()
    if data is None:
        new_ml_score = ml_score_model.MLScore(
            client_id=ml_score.client_id,
            advertiser_id=ml_score.advertiser_id,
            score=ml_score.score
        )
        session.add(new_ml_score)
        data = new_ml_score
    else:
        data.score = ml_score.score
    await session.commit()
    return data
