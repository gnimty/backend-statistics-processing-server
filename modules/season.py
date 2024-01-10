from config.mongo import Mongo
from log import get_logger
import datetime

logger = get_logger()

db = Mongo.get_client("riot")
col = "season"

season_start_epoch = None
season_name = None

def init():
  global season_start_epoch
  global season_name
  
  result = db[col].find_one({}, sort=[('startAt', -1)])

  if not result:
    epoch_seconds = int(datetime.datetime.strptime("20230719000000", "%Y%m%d%H%M%S").timestamp())

    result = {"startAt":epoch_seconds,
              "seasonName": "13_S2"}
    
  season_start_epoch = result["startAt"]
  season_name = result["seasonName"]
    
def update_season(new_start_at:datetime.datetime, new_season_name:str):
  global season_start_epoch
  global season_name
  
  is_changed = False
  
  new_season_start_epoch = int(new_start_at.timestamp())
  
  # 시즌 정보가 변동될 때 
  if season_name!=new_season_name:
    logger.info("시즌 정보 변동")
    # TODO
    is_changed =  True
  
  db[col].update_one({"seasonName":new_season_name},{"$set":{
    "startAt":new_season_start_epoch,
    "seasonName": new_season_name
    }}, True)
  
  season_start_epoch = new_season_start_epoch
  season_name = new_season_name
  
  return is_changed
  
  
  
  
  