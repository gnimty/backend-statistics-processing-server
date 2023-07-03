import redis, json

class RedisClient():
  r = object()
  key = "API_LIMIT"
  
  @staticmethod
  def init(**redis_kwargs):
    RedisClient.r = redis.Redis(**redis_kwargs)
    RedisClient.setInitLimit()
    
  @staticmethod
  def setInitLimit(): 
    RedisClient.r.set(RedisClient.key, 100)
    
  @staticmethod
  def dec_limit():  # rate limit 값 줄이기
    if RedisClient.isAvailable(0):
      RedisClient.r.set(RedisClient.key, RedisClient.get()-1)
      return f"{RedisClient.get()}개 남음"
    return "API LIMIT 초과"
  
  @staticmethod
  def get():  # 꺼낼 데이터 조회
    return int(RedisClient.r.get(RedisClient.key))
  
  @staticmethod
  def isAvailable(limit):
    return RedisClient.get()>limit

rd = object()