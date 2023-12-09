
from error import custom_exception
from flask_api import status
from riot_requests.common import delayable_request
import log

logger = log.get_logger()


def get_top_league(league, queue="RANKED_SOLO_5x5"):
  """
  해당 league에 존재하는 모든 소환사 정보 가져오기\n
  50 requests every 10 seconds

  Args:
      league (str): should be in ["challengerleagues", "grandmasterleagues","masterleagues"].
      queue (str, optional): 조회할 큐 선택, Defaults to "RANKED_SOLO_5x5".

  Returns:
      [LeagueListDTO]: {
        freshBlood (boolean) : 아직 뭔지모름,
        wins (int),
        summonerName (string),
        miniSeries (MiniSeriesDTO),
        inactive (boolean) : 아직 뭔지모름,
        veteran	(boolean) : 아직 뭔지모름,
        hotStreak	(boolean) : 아직 뭔지모름,	
        rank (string): 세부 티어 (ex: Diamond 1 -> rank : "I"),
        leaguePoints (int) 점수,	
        losses (int),
        summonerId (string),
      }
  """
  if league not in ["challengerleagues", "grandmasterleagues", "masterleagues"]:
    return []

  url = f"https://kr.api.riotgames.com/lol/league/v4/{league}/by-queue/{queue}"

  result = delayable_request(url)
  entries = result["entries"]

  if not entries or not isinstance(entries, list):
    raise custom_exception.CustomUserError(
        "리그 엔트리 정보를 가져오는 데 실패했습니다.",
        "Result of request to Riot not exists", status.HTTP_500_INTERNAL_SERVER_ERROR)

  # TODO - 요구사항 확장 시 이부분은 고쳐야함
  entries.sort(key=lambda x: x["leaguePoints"], reverse=True)

  # 티어, 큐 업데이트
  for entry in entries:
    if queue == "RANKED_SOLO_5x5":
      entry["queue"] = league[:-7]
      entry["tier"] = entry["rank"]
      
    else:
      entry["queue_flex"] = league[:-7]
      entry["tier_flex"] = entry["rank"]
      entry["leaguePoints_flex"] = entry["leaguePoints"]
      entry["wins_flex"] = entry["wins"]
      entry["losses_flex"] = entry["losses"]
      
      del entry["leaguePoints"]
      del entry["wins"]
      del entry["losses"]
      
    entry["metadata"] = {
      "id": entry["summonerId"],
    }
    
  return entries


def get_summoner_by_id(summoner_id):

  url = f"https://kr.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
  
  ranks = delayable_request(url)
  
  first = next((rank for rank in ranks))
  
  total = {
    "summonerName":first["summonerName"],
    "summonerId":first["summonerId"],
    "metadata":{
      "id": first["summonerId"],
    },
  }
  
  for rank in ranks:
    if rank["queueType"]=="RANKED_SOLO_5x5":
      total["queue"] = rank["tier"].lower()
      total["tier"] = rank["rank"]
      total["leaguePoints"] = rank["leaguePoints"]
      total["wins"] = rank["wins"]
      total["losses"] = rank["losses"]
      
    elif rank["queueType"]=="RANKED_FLEX_SR":
      total["queue_flex"] = rank["tier"].lower()
      total["tier_flex"] = rank["rank"]
      total["leaguePoints_flex"] = rank["leaguePoints"]
      total["wins_flex"] = rank["wins"]
      total["losses_flex"] = rank["losses"]
  return total


def get_summoners_under_master(tier, division, queue = "RANKED_SOLO_5x5", page=0):
  
  url = f"https://kr.api.riotgames.com/lol/league-exp/v4/entries/{queue}/{tier}/{division}?page={page}"
  results = delayable_request(url)
  
  if not results or not isinstance(results, list) or len(results) == 0:
    return []
  
  for result in results:
    result["queue"] = str(result["tier"]).lower()
    result["tier"] = result["rank"]
    result["metadata"] = {
        "id": result["summonerId"],
    }
  
  return results
  