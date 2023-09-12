import redis, requests, logging, pymongo

logger = logging.getLogger("app")

# r=redis.Redis(host='15.164.93.32',port=6379,charset="utf-8", decode_responses=True)#utf-8로 인코딩
def updateChampionMap(db:pymongo.MongoClient, rd:redis.Redis, timeout:int = 10):
  
  url = "https://ddragon.leagueoflegends.com/cdn/13.16.1/data/ko_KR/champion.json"
  response = requests.get(url,timeout=timeout)
  
  data=response.json()

  champions_data = dict(data['data'])
  
  for champion in champions_data.values():
    id = champion["key"]
    en = champion["id"]
    kr = champion["name"]
    
    rd.hset(id, "en", en)
    rd.hset(id, "kr", kr)
  
  
  db["champion_info"].delete_many({})
  db["champion_info"].insert_many([
    {
      "id" : champion["key"],
      "en" : champion["id"],
      "kr" : champion["name"]
    } for champion in champions_data.values()
  ])

def updateLatestVersion(rd:redis.StrictRedis, timeout:int = 10):
  
  url = "https://ddragon.leagueoflegends.com/api/versions.json"
  response = requests.get(url,timeout=timeout)
  
  versions = list(response.json())

  rd.set("version", versions[0])
  
  
