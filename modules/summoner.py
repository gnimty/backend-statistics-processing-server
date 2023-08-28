from riot_requests import summoner_v4, league_exp_v4
from error.custom_exception import DataNotExists
from datetime import datetime, timedelta
import logging
from utils.date_calc import lastModifiedFromNow
from utils.summoner_name import makeInternalName
from modules.TierDivisionMMR import MMR

logger = logging.getLogger("app")
col = "summoners"

division = {
  "I":1,
  "II":2,
  "III":3,
  "IV":4
}


def findAllSummonerPuuid(db):
  puuids = list(db[col].find({}, {"_id":0, "puuid":1}))
  
  return [s['puuid'] for s in puuids if 'puuid' in s]


def findBySummonerId(db, summonerId):
  """소환사 ID로 소환사 정보 조회

  Args:
      db (connection)
      summonerId (str)

  Returns:
      summoner
  """
  summoner = db[col].find_one(
    {'id': summonerId},
    {"_id": 0, "accountId": 0})

  if not summoner:
    logger.info("소환사 정보가 존재하지 않습니다.")
  
  return summoner


def updateBySummonerPuuid(db, puuid, limit):
  summoner = findBySummonerPuuid(db, puuid)
  
  new_summoner = summoner_v4.requestBySummonerPuuid(puuid, limit)
  
  updateSummoner(db, summoner or new_summoner, new_summoner)


def updateBySummonerBrief(db, summoner_brief, limit):
  updateSummoner(
      db,
      findBySummonerId(db, summoner_brief["summonerId"]) or
      summoner_v4.requestSummonerById(summoner_brief["summonerId"], limit), summoner_brief)


def findBySummonerName(db, summonerName, limit):
  """소환사 이름으로 소환사 정보 조회

  Args:
      db (connection)
      summonerName (str)

  Returns:
      summoner
  """
  summoner = db[col].find_one(
    {"name": summonerName}, 
    {"_id": 0, "accountId": 0})

  if not summoner:
    return summoner_v4.requestSummonerByName(summonerName, limit)

  return summoner

def findSummonerRankInfoBySummonerId(summonerId, limit):
  return league_exp_v4.get_summoner_by_id(summonerId, limit)
  
  
  
  
  
def findBySummonerPuuid(db, puuid):
  summoner = db[col].find_one(
    {"puuid": puuid}, 
    {"_id": 0, "accountId": 0})

  return summoner

def findBySummonerPuuid(db, puuid):
  summoner = db[col].find_one(
    {"puuid": puuid}, 
    {"_id": 0, "accountId": 0})

  if not summoner:
    return None

  return summoner


def updateSummoner(db, summoner, summoner_brief):
  """summoner 정보 업데이트 및 history 객체 추가

  Args:
      summoner: 현재 정보
      summoner_brief: 조회한 최신 entry 정보
  """
  
  if not summoner:
    return None
  
  summoner_brief["tier"] = division[summoner_brief["tier"]]
  summoner["updatedAt"] = datetime.now()
  summoner["queue"] = summoner_brief["queue"]
  summoner["tier"] = summoner_brief["tier"]
  summoner["leaguePoints"] = summoner_brief["leaguePoints"]
  summoner["wins"] = summoner_brief["wins"] 
  summoner["losses"] = summoner_brief["losses"] 
  if "rank" in summoner:
    del summoner["rank"] # 랭크 정보 삭제
  
  summoner["name"] = summoner_brief["summonerName"]
  summoner["internal_name"] = makeInternalName(summoner["name"])
  summoner["mmr"] = MMR[summoner["queue"]].value + int(summoner["leaguePoints"])\
  
  # history list 존재하면 갖다 붙이고 없으면 새로 생성
  if not summoner.get("history"):
    summoner["history"] = [{
      "queue":summoner_brief["queue"],
      "tier":summoner_brief["tier"],
      "leaguePoints":summoner_brief["leaguePoints"],
      "updatedAt":summoner["updatedAt"]
    }]
  else:
    # history 맨 처음에 insert
    summoner["history"].insert(0, {
      "queue":summoner_brief["queue"],
      "tier":summoner_brief["tier"],
      "leaguePoints":summoner_brief["leaguePoints"],
      "updatedAt":summoner["updatedAt"],
    })
    
  db[col].update_one(
      {"puuid": summoner["puuid"]},
      {"$set": summoner},
      True)
  return summoner
  

def findSummonerHistory(db, puuid, stdDate):
  summoner = db[col].find_one({"puuid":puuid})
  
  if not summoner or "history" not in summoner:
    return {
        "queue":None,
        "tier":None,
        "leaguePoints":None
      }
  
  for h in summoner["history"]:
    # 히스토리 날짜와 매치 날짜 비교 후 매치 날짜가 히스토리 날짜보다 최신이면 다음 히스토리 탐색
    # 그렇지 않으면 현재 탐색한 히스토리 이전 데이터를 티어 정보로 산정
    # 만약 전부 탐색해도 결과가 나오지 않으면 가장 오래된 history를 티어 정보로 산정
    temp_history = h
    if stdDate >= h["updatedAt"]:
      break
  
  return temp_history

def mmrFix(db):
  summoners  = db[col].find({})
  for summoner in summoners:
    summoner["mmr"] = MMR[summoner["queue"]].value + int(summoner["leaguePoints"])
    db[col].update_one(
      {"puuid": summoner["puuid"]},
      {"$set": summoner},
      True)
    
  