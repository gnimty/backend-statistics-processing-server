import requests, log
from config.mongo import Mongo
from config.redis import Redis
from riot_requests.champion_v3 import get_rotation_champions
from modules.crawl import update_patch_note_image

logger = log.get_logger()
db = Mongo.get_client("riot")
rd = Redis.get_client()
col = "version"

# current_data={
#   "version":None,
#   "items":None,
# }

# def init():
#   update_latest_version()
#   update_champion_info(current_data["version"])
#   update_item_info(current_data["version"])

def update_latest_version():

  url = "https://ddragon.leagueoflegends.com/api/versions.json"
  response = requests.get(url)

  versions = list(response.json())

  latest_version = versions[0]
  
  logger.info("current version : %s", latest_version)
  # current_data["version"] = latest_version
  
  rd.set("version", latest_version)
  
  
  for v in [{"version": version, "order": i} for version, i in zip(versions, range(len(versions)))]:
    db["version"].update_one({"version":v["version"]},
                             {"$set":v})

  update_patch_note_image(latest_version)

  return latest_version

def update_champion_info(latest_version):

  url = f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/ko_KR/champion.json"
  response = requests.get(url)

  data = response.json()

  champions_data = dict(data['data'])

  champions = [{
    "championId": champion["key"],
    "en": champion["id"],
    "kr": champion["name"]} for champion in champions_data.values()]

  champion_map = {
    champion["championId"]: {
      "en":champion["en"],
      "kr":champion["kr"]
    } for champion in champions
  }
  
  for champion in champions:
    champion_id = champion["championId"]
    en = champion["en"]
    kr = champion["kr"]

    rd.hset("en", champion_id, en)
    rd.hset("kr", champion_id, kr)

  db["champion_info"].delete_many({})
  db["champion_info"].insert_many(champions)

  url = f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/ko_KR/champion.json"
  rotations = get_rotation_champions()
  
  db["rotations"].delete_many({})
  db["rotations"].insert_many([
    {
      "championId":champion_id, 
      "en":champion_map.get(str(champion_id))["en"], 
      "kr":champion_map.get(str(champion_id))["kr"]
    }  for champion_id in rotations
    ])


class Item():
  def __init__(self, id, name, version, itemType = "total", orrnItemFrom=None):
    self.id = id
    self.name = name
    self.version = version
    self.itemType = itemType
    self.ornnItemFrom = orrnItemFrom
    

def update_item_info(latest_version):
  db["items"].delete_many({"version":latest_version})
  result:dict = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/ko_KR/item.json").json()

  total_items = []

  for key, value in result["data"].items():
    if int(key)>9999:
      continue
    if value["gold"]["total"]<=2000:
      if value["gold"]["total"] >= 700 and value["gold"]["total"] <= 1300 and "Boots" not in value["tags"]:
        total_items.append(Item(key, value.get("name"), latest_version, itemType = "middle"))
    else:
      if "into" not in value:
        if value.get("requiredAlly")=="Ornn" or value.get("gold")["base"]==0:  
          total_items.append(Item(value["from"][0], result["data"][value["from"][0]].get("name"), latest_version))
          total_items.append(Item(key, value.get("name"),latest_version, orrnItemFrom=value["from"][0]))
        else:
          if "from" in value:
            total_items.append(Item(key, value.get("name"), latest_version))
  
  result = [item.__dict__ for item in total_items]
  
  db["items"].insert_many(result)
  
  # current_data["items"] = result
  
  
def get_latest_version() -> str:
  return db[col].find_one({"order":0}, {"version":1, "_id":0})["version"]

