import os

import dotenv
import uvicorn

from fastapi import FastAPI

import app.db.db_session
from app.redis.redis_client import init_redis, set_day

from app.routers import (ads_router, advertisers_router, campaigns_router,
                         client_router, stats_router)


dotenv.load_dotenv()

server_app = FastAPI()
server_app.include_router(ads_router.router)
server_app.include_router(advertisers_router.router)
server_app.include_router(campaigns_router.router)
server_app.include_router(client_router.router)
server_app.include_router(stats_router.router)


@server_app.on_event("startup")
async def startup():
    await app.db.db_session.global_init()
    server_app.state.redis = await init_redis()
    await set_day(server_app.state.redis, 0)


@server_app.on_event("shutdown")
async def shutdown():
    await app.db.db_session.engine.dispose()
    await server_app.state.redis.aclose()


if __name__ == '__main__':
    uvicorn.run(server_app, host=os.getenv('SERVER_HOST'),
                port=int(os.getenv('SERVER_PORT')), log_level="info")
