import os

class Config:
  API_KEY=os.environ.get("RIOT_API_KEY")
  SUMMONER_BATCH_HOUR = int(os.environ.get("SUMMONER_BATCH_HOUR"))
  MATCH_BATCH_HOUR = int(os.environ.get("MATCH_BATCH_HOUR"))
  MONGO_HOST =os.environ.get("MONGO_HOST")
  MONGO_PORT= os.environ.get("MONGO_PORT")
  MONGO_USERNAME= os.environ.get("MONGO_USERNAME")
  MONGO_PASSWORD= os.environ.get("MONGO_PASSWORD")
  MONGO_ADMIN_DB=os.environ.get("MONGO_ADMIN_DB")
  MONGO_STATISTICS_DB=os.environ.get("MONGO_STATISTICS_DB")
  MONGO_RIOTDATA_DB=os.environ.get("MONGO_RIOTDATA_DB")
  
  FLASK_PORT=os.environ.get("FLASK_RUN_PORT")
  FLASK_HOST=os.environ.get("FLASK_RUN_HOST")
  FLASK_DEBUG = os.environ.get("FLASK_DEBUG")
  LOGGING_LEVEL = os.environ.get("LOGGING_LEVEL")
  LOGGING_WHEN = os.environ.get("LOGGING_WHEN")
  REDIS_HOST = os.environ.get("REDIS_HOST")
  REDIS_PORT = os.environ.get("REDIS_PORT")
  
  BATCH_LIMIT = int(os.environ.get("BATCH_LIMIT"))
  API_REQUEST_LIMIT = int(os.environ.get("API_REQUEST_LIMIT"))
  
class DevelopmentConfig(Config):
  MONGO_URI=f"mongodb://{Config.MONGO_USERNAME}:{Config.MONGO_PASSWORD}@{Config.MONGO_HOST}:{Config.MONGO_PORT}"


class ProductionConfig(Config):
  MONGO_URI=f"mongodb://{Config.MONGO_USERNAME}:{Config.MONGO_PASSWORD}@{Config.MONGO_HOST}:{Config.MONGO_PORT}/{Config.MONGO_ADMIN_DB}"
    
class LocalConfig(Config):
  MONGO_URI=f"mongodb://{Config.MONGO_HOST}:{Config.MONGO_PORT}"

config = dict(dev=DevelopmentConfig, prod=ProductionConfig, local = LocalConfig)