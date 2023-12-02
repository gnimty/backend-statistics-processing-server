from config.mongo import Mongo
from log import get_logger
import datetime

logger = get_logger()

db = Mongo.get_client("riot")
col = "season"

season_start_epoch = None

def init():
  global season_start_epoch
  result = db[col].find_one({})
  
  if not result:
    epoch_seconds = int(datetime.datetime.strptime("20230719000000", "%Y%m%d%H%M%S").timestamp())

    result = {"startAt":epoch_seconds}
    db[col].insert_one(result)
    
  season_start_epoch = result["startAt"]
    
def update_season(epoch_seconds):
  global season_start_epoch
  
  db[col].delete_many({})
  season_start_epoch = epoch_seconds
  db[col].insert_one({"startAt":epoch_seconds})
  
  