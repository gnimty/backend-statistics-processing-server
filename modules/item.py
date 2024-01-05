from config.mongo import Mongo
from log import get_logger
from modules.version import get_latest_version

logger = get_logger()

db = Mongo.get_client("riot")
col = "items"

def get_item_maps(version):
  results = list(db[col].find({"version":version}))
  
  if len(results)==0:
    results = list(db[col].find({"version":get_latest_version()}))
  
  return {
    "total":{r["id"]:r for r in results if r["itemType"]=="total"},
    "middle":{r["id"]:r for r in results if r["itemType"]=="middle"},
    "boots":{r["id"]:r for r in results if r["itemType"]=="boots"},
  }