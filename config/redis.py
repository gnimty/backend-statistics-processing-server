from redis import Redis as RedisClient
from config.appconfig import current_config as config


class Redis:
  redisClient = None

  @classmethod
  def set_client(cls) -> None:
    cls.redisClient = RedisClient(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        charset="utf-8",
        decode_responses=True
    )
    
  @classmethod
  def get_client(cls) -> RedisClient:
    return cls.redisClient
