import string
from typing import Annotated

from fastapi import APIRouter, Body, Path, Depends, HTTPException
from starlette import status

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.db_session import create_session
from ..db import client_model

from ..schemas.client_schemas import ClientUpsert, Client

import uuid


router = APIRouter(tags=["Clients"])


@router.post("/clients/bulk", status_code=status.HTTP_201_CREATED, response_model=list[Client])
async def create_clients(clients: Annotated[list[ClientUpsert], Body()],
                         session: AsyncSession = Depends(create_session)):
    # ok_letters = set(string.ascii_lowercase + string.ascii_uppercase + string.digits)
    logins_array = []
    uuids_array = []
    for data in clients:
        # for ch in data.login:
        #     if ch not in ok_letters:
        #         raise HTTPException(status_code=400, detail=f"Bad login: {data.login}")

        result = await session.execute(select(client_model.Client)
                                       .where(client_model.Client.login == data.login))
        client = result.scalar_one_or_none()
        if client is not None and client.client_id != data.client_id:
            raise HTTPException(status_code=400, detail=f"Login {client.login} is already registered")

        logins_array.append(data.login)
        uuids_array.append(data.client_id)

    if len(logins_array) != len(set(logins_array)) or \
        len(uuids_array) != len(set(uuids_array)):
        raise HTTPException(status_code=400, detail="Login or UUID are not unique")

    for data in clients:
        result = await session.execute(select(client_model.Client)
                                       .where(client_model.Client.client_id == data.client_id))
        client = result.scalar_one_or_none()
        if client is None:
            new_client = client_model.Client(
                client_id=data.client_id,
                login=data.login,
                age=data.age,
                location=data.location,
                gender=data.gender
            )
            session.add(new_client)
        else:
            client.login = data.login
            client.age = data.age
            client.location = data.location
            client.gender = data.gender
        await session.commit()
    return clients


@router.get("/clients/{client_id}", response_model=Client)
async def get_client_by_uuid(client_id: Annotated[uuid.UUID, Path()],
                             session: AsyncSession = Depends(create_session)):
    result = await session.execute(select(client_model.Client).where(client_model.Client.client_id == client_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="Client not found")

    return user
