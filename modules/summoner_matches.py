from riot_requests import match_v4
from error.custom_exception import *

col = "summoner_matches"

def updateAndGetTotalMatchIds(db, limit: int, puuid):
  """
  소환사의 최근 match Id 리스트를 업데이트

  Args:
      db (connection)
      summonerName (str)

  Raises:
      DataNotExists
  
  Returns:
      puuid (str) : 소환사의 puuid
  """
  
  # 가장 최근 match id 가져오기
  old_matches = db[col].find_one({"puuid":puuid})
  
  # 모든 matchId 담을 변수, 최근 matchId 우선 가져오기 (100개씩))
  all_match_ids = set(match_v4.getSummonerMatches(
      puuid, limit, count = 100))
  
  # 다음 페이지 조회 시 이용하는 변수
  start_index=100
  
  # FIXME - 버그 발생지점 (startIdx=3000000 이상으로 넘어감)
  if old_matches:
    latest_match_id = old_matches["summoner_match_ids"][0]
    
    # API로 최근 전적 가져온 후 그 안에 latest_match_id가 존재하면 db와 sync가 맞음
    # 그렇지 않으면 계속 가져와서 all_matches_ids에 갖다붙이기
    while latest_match_id not in all_match_ids:
      all_match_ids.update(match_v4.getSummonerMatches(puuid, limit, start = start_index, count = 100))
      start_index+=100
      
  else:
    while True:
      new_match_list = match_v4.getSummonerMatches(puuid, limit, start = start_index, count = 100)
      if len(new_match_list)!=0:
        all_match_ids.update(new_match_list)
        start_index+=100
      else:
        break
  print("aweefwefaawefawefawefawefwf")
  total_list = sorted(list(all_match_ids), reverse=True)
  db[col].update_one(
      {'puuid': puuid},
      {"$set": {"summoner_match_ids": sorted(
          list(all_match_ids), reverse=True)}},
      True)

  return total_list