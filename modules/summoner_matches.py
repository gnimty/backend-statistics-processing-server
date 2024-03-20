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

  queues = [420,440]
  if not collect:
    queues.append(490, 450)
  
  # 수집 모드일 때
  if collect:
    recent_days_match_ids=[]
    for queue in queues:
      start_index=0
      while True:
        results = match_v4.get_summoner_match_ids(puuid, start = start_index, count = 100, queue=queue, collect = collect)
        recent_days_match_ids.extend(list(results))
        start_index+=100
        if len(results)<100:
          break
      
    return recent_days_match_ids
  
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
  
  total = {}
  
  for queue in queues:
    # 모든 matchId 담을 변수, 최근 matchId 우선 가져오기 (100개씩))
    all_match_ids = []
    old_matches_set = set(old_matches[queue])
    
    start_index=0
    
    # API로 최근 전적 가져온 후 그 안에 latest_match_id가 존재하면 db와 sync가 맞음
    # 그렇지 않으면 계속 가져와서 all_matches_ids에 갖다붙이기
    while True:
      results =match_v4.get_summoner_match_ids(puuid, start = start_index, count = 100, queue=queue, collect = collect)
      all_match_ids.extend(list(results))
      start_index+=100
      if len(results)<100:
        break
      elif results[-1] in old_matches_set:
        extended = old_matches[queue][old_matches[queue].index(all_match_ids[-1])+1:]
        all_match_ids.extend(extended)
        break
  
    total[queue] = all_match_ids
    
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