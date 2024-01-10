from riot_requests import match_v4
from error.custom_exception import *
from config.mongo import Mongo

col = "summoner_matches"
db_riot = Mongo.get_client("riot")

def get_all_match_id_set():
  return db_riot["summoner_matches"].aggregate([
    {
        "$unwind": "$summoner_match_ids"  # 배열을 풀어서 각 match_id를 개별 문서로 만듭니다.
    },
    {
        "$group": {
            "_id": None,
            "unique_match_ids": {"$addToSet": "$summoner_match_ids"}  # 중복되지 않는 match id들을 set으로 모읍니다.
        }
    }
])

def update_total_match_ids(puuid, collect = False) -> list:
  """
  소환사의 최근 match Id 리스트를 업데이트

  Args:
      db (connection)
      summonerName (str)

  Raises:
      DataNotExists
  """

  queues = [420,440,450]
  if not collect:
    queues.append(490)
  
  # 가장 최근 match id 가져오기
  result = db_riot[col].find_one({"puuid": puuid})
  
  if not result:
    old_matches = { #마지막으로 조회한 match id 하한선
      420:[],
      490:[],
      440:[],
      450:[],
    }
  else:
    old_matches = { #마지막으로 조회한 match id 하한선
      420:result.get("summoner_match_ids"),
      490:result.get("summoner_match_ids_blind"),
      440:result.get("summoner_match_ids_flex"),
      450:result.get("summoner_match_ids_aram"),
    }
  
  
  latest_match_id = { #마지막으로 조회한 match id 하한선
    420:"KR_0000000000",
    490:"KR_0000000000",
    440:"KR_0000000000",
    450:"KR_0000000000",
  }
  
  total = {}
  
  for queue in queues:
    # 모든 matchId 담을 변수, 최근 matchId 우선 가져오기 (100개씩))
    all_match_ids = set()
    
    if old_matches[queue] and len(old_matches[queue])>=1: 
      latest_match_id[queue] = old_matches[queue][0]
    else:
      old_matches[queue] = []
    
    start_index=0
    
    # API로 최근 전적 가져온 후 그 안에 latest_match_id가 존재하면 db와 sync가 맞음
    # 그렇지 않으면 계속 가져와서 all_matches_ids에 갖다붙이기
    while True:
      results =match_v4.get_summoner_match_ids(puuid, start = start_index, count = 100, queue=queue, collect = collect)
      if len(results)==0 or results[-1] <= latest_match_id[queue]:
        break
      else:
        all_match_ids.update(set(results))
        start_index+=100
  
    all_match_ids.update(old_matches[queue])
  
    total[queue] = sorted(list(all_match_ids), reverse=True)
  
  if not collect:
    db_riot[col].update_one(
      {'puuid': puuid},
      {"$set": {
        "summoner_match_ids": total.get(420),
        "summoner_match_ids_blind": total.get(490),
        "summoner_match_ids_flex": total.get(440),
        "summoner_match_ids_aram": total.get(450),
      }}, True)

  total_list = []
  for match_ids in total.values():
    total_list.extend(match_ids)

  return total_list