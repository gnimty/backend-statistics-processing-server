from redis import Redis as RedisClient
from config.appconfig import current_config as config
import threading

class Redis:
  redis_client = None
  
  lock = threading.Lock()
  @classmethod
  def set_client(cls) -> None:
    cls.redis_client = RedisClient(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        charset="utf-8",
        decode_responses=True
    )
    
  @classmethod
  def get_client(cls) -> RedisClient:
    return cls.redis_client
  
  @classmethod
  def add_to_set(cls, match_id):
    with cls.lock:
        # 처리된 raw data의 id를 set에 추가
        cls.redis_client.sadd('processed_ids', match_id)
        
  @classmethod        
  def check_processed(cls, match_id):
        with cls.lock:
            # 처리 여부 확인
            return cls.redis_client.sismember('processed_ids', match_id)

