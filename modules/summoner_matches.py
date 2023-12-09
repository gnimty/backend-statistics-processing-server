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

  # 가장 최근 match id 가져오기
  old_matches = db_riot[col].find_one({"puuid": puuid})
  
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
      results =match_v4.get_summoner_match_ids(puuid, start = start_index, count = 100, queue=queue, collect = collect)
      
      all_match_ids.update(set(results))
      if len(results)==0 or results[-1] <= latest_match_id:
        break
      else:
        start_index+=100
  
  all_match_ids.update(old_matches["summoner_match_ids"])
  
  total_list = sorted(list(all_match_ids), reverse=True)
  
  if not collect:
    db_riot[col].update_one(
      {'puuid': puuid},
      {"$set": {"summoner_match_ids": total_list}},
      True)

  return total_list