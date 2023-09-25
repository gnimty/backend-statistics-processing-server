import requests, log
from config.mongo import Mongo
from config.redis import Redis

logger = log.get_logger()
db = Mongo.get_client("riot")
rd = Redis.get_client()

def update_latest_version():

  url = "https://ddragon.leagueoflegends.com/api/versions.json"
  response = requests.get(url)

  versions = list(response.json())

  rd.set("version", versions[0])

  db["version"].delete_many({})
  db["version"].insert_many(
    [{"version": version, "order": i} for version, i in zip(versions, range(len(versions)))])

  return versions[0]

def update_champion_info(latest_version):

  url = f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/ko_KR/champion.json"
  response = requests.get(url)

  data = response.json()

  champions_data = dict(data['data'])

  for champion in champions_data.values():
    champion_id = champion["key"]
    en = champion["id"]
    kr = champion["name"]

    rd.hset("en", champion_id, en)
    rd.hset("kr", champion_id, kr)

  db["champion_info"].delete_many({})
  db["champion_info"].insert_many([
      {
          "championId": champion["key"],
          "en": champion["id"],
          "kr": champion["name"]
      } for champion in champions_data.values()
  ])


