from riot_requests import match_v4
from error.custom_exception import *
from config.mongo import Mongo

col = "summoner_matches"
db_riot = Mongo.get_client("riot")
db_stats = Mongo.get_client("stat")

def update_total_match_ids(puuid, limit, test = False) -> list:
  """
  소환사의 최근 match Id 리스트를 업데이트

  Args:
      db (connection)
      summonerName (str)

  Raises:
      DataNotExists
  """
  if test:
    target_db = db_stats
  else:
    target_db = db_riot

  # 가장 최근 match id 가져오기
  old_matches = target_db[col].find_one({"puuid": puuid})
  
  # 모든 matchId 담을 변수, 최근 matchId 우선 가져오기 (100개씩))
  all_match_ids = set()
  
  
  # 다음 페이지 조회 시 이용하는 변수
  start_index=100
  
  latest_match_id = "KR_0000000000" #마지막으로 조회한 match id 하한선
  
  if old_matches: 
    latest_match_id = old_matches["summoner_match_ids"][0]
  else:
    old_matches= {
      "summoner_match_ids":[]
    }
  for queue in [420,430,440,450]:
    start_index=0
    
    # API로 최근 전적 가져온 후 그 안에 latest_match_id가 존재하면 db와 sync가 맞음
    # 그렇지 않으면 계속 가져와서 all_matches_ids에 갖다붙이기
    while True:
      results =match_v4.get_summoner_match_ids(puuid, limit=limit, start = start_index, count = 100, queue=queue)
      
      all_match_ids.update(set(results))
      if len(results)==0 or results[-1] <= latest_match_id:
        break
      else:
        start_index+=100
  
  all_match_ids.update(old_matches["summoner_match_ids"])
  
  total_list = sorted(list(all_match_ids), reverse=True)
  
  target_db[col].update_one(
    {'puuid': puuid},
    {"$set": {"summoner_match_ids": total_list}},
    True)

  return total_list