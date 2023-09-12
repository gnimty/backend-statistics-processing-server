import redis

def redisClient(app):
  return redis.Redis(
    host = app.config["REDIS_HOST"],
    port = app.config["REDIS_PORT"],
    charset = "utf-8",
    decode_responses = True)
