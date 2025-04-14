from redis import asyncio as aioredis
import os


async def init_redis():
    host = os.getenv('REDIS_HOST', 'localhost')
    port = int(os.getenv('REDIS_PORT', '6379'))
    db = int(os.getenv('REDIS_DB', '0'))
    redis = aioredis.Redis(host=host, port=port, db=db)
    return redis


async def get_day(redis: aioredis.Redis):
    res = await redis.get('day')
    return int(res)


async def set_day(redis: aioredis.Redis, day: int):
    await redis.set('day', day)
