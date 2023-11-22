from riot_requests import summoner_v4
from datetime import datetime
from utils.summoner_name import makeInternalName
from modules.TierDivisionMMR import MMR
from modules.summoner_plays import find_most_champions
from config.mongo import Mongo
import asyncio
from community import csmq

import log
logger = log.get_logger()

col = "summoners"
col_history = "summoner_history"

db_riot = Mongo.get_client("riot")

division = {
  "I":1,
  "II":2,
  "III":3,
  "IV":4
}

def find_all_puuids() -> list:
  puuids = list(db_riot[col].find({}, {"_id":0, "puuid":1}))
  
  return [s['puuid'] for s in puuids if 'puuid' in s]


def find_one_by_summoner_id(summoner_id):
  """소환사 ID로 소환사 정보 조회

  Args:
      db (connection)
      summonerId (str)

  Returns:
      summoner
  """
  target_db = db_riot
  
  summoner = target_db[col].find_one(
    {'id': summoner_id},
    {"_id": 0, "accountId": 0})

  if not summoner:
    logger.info("소환사 정보가 존재하지 않습니다.")
  
  return summoner


def update_by_puuid(puuid):
  summoner = find_by_puuid(puuid)
  
  new_summoner = summoner_v4.get_by_puuid(puuid)
  
  update(db_riot, summoner or new_summoner, new_summoner)

def recursive_tagline_update(summoner):
  matched = db_riot[col].find_one({"internal_tagname":summoner["internal_tagname"],
                                   "puuid":{"$ne":summoner["puuid"]}})
  if matched:
    logger.info("%s와 동일한 internal tagname 소환사 확인, 업데이트", summoner["internal_tagname"])
    tagName = summoner_v4.get_tagline(matched["puuid"])
    matched["name"] = tagName["gameName"]
    matched["internal_name"] = makeInternalName(matched["name"])
    matched["tagLine"] = tagName["tagLine"]
    matched["internal_tagname"] = matched["internal_name"] + matched["tagLine"]
    
    db_riot[col].update_one({"puuid":matched["puuid"]}, {"$set":matched})
    logger.info("업데이트 후 internal tagname : %s", matched["internal_tagname"])
    recursive_tagline_update(matched)
    
    

# 이부분 코드 완전히 개선해야 함
def update_by_summoner_brief(summoner_brief)->str:
  summoner = find_one_by_summoner_id(summoner_brief["summonerId"]) 
  
  if not summoner: # 기존에 존재하지 않는 데이터 -> request를 통해 붙어서 옴
    summoner = summoner_v4.get_by_summoner_id(summoner_brief["summonerId"])
    update(summoner, summoner_brief, check_name = True)
  else: # 기존에 존재하는 데이터 -> 랭킹 갱신 시 체크하지 않음
    update(summoner, summoner_brief)  
    
  return summoner["puuid"]
  

def find_by_puuid(puuid):
  summoner = db_riot[col].find_one(
    {"puuid": puuid}, 
    {"_id": 0, "accountId": 0})

  return summoner


def update(summoner, summoner_brief, check_name = False):
  """summoner 정보 업데이트 및 history collection 업데이트

  Args:
      summoner: 현재 정보
      summoner_brief: 조회한 최신 entry 정보
  """
  
  target_db = db_riot
  
  if not summoner:
    return None
  
  summoner_brief["tier"] = division[summoner_brief["tier"]]
  summoner["updatedAt"] = datetime.now()
  summoner["queue"] = summoner_brief["queue"]
  summoner["tier"] = summoner_brief["tier"]
  summoner["leaguePoints"] = summoner_brief["leaguePoints"]
  summoner["wins"] = summoner_brief["wins"] 
  summoner["losses"] = summoner_brief["losses"] 
  summoner["mmr"] = MMR[summoner["queue"]].value + int(summoner["leaguePoints"])
  
  if "rank" in summoner:
    del summoner["rank"] # 랭크 정보 삭제
  
  if not check_name: # tagLine 갱신을 거치지 않은 데이터일 경우 DB 업데이트에 반영하지 않음
    del summoner["name"]
    del summoner["internal_name"]
    del summoner["internal_tagname"]
  else:
    # DB에 동일한 internal tagname이 존재한다면 해당 소환사 업데이트
    recursive_tagline_update(summoner)
  
  # history list 존재하면 갖다 붙이고 없으면 새로 생성
  summoner_history = find_history(summoner["puuid"])
  
  if not summoner_history or not summoner_history.get("history"):
    summoner_history = {
        "puuid": summoner["puuid"],
        "history": [{
            "queue": summoner_brief["queue"],
            "tier":summoner_brief["tier"],
            "leaguePoints":summoner_brief["leaguePoints"],
            "updatedAt":summoner["updatedAt"]
        }]
    }
  else:
    # history 맨 처음에 insert
    summoner_history["history"].insert(0, {
      "queue":summoner_brief["queue"],
      "tier":summoner_brief["tier"],
      "leaguePoints":summoner_brief["leaguePoints"],
      "updatedAt":summoner["updatedAt"],
    })
    
  target_db[col].update_one(
      {"puuid": summoner["puuid"]},
      {"$set": summoner},
      True)
  
  target_db[col_history].update_one(
      {"puuid": summoner["puuid"]},
      {"$set": summoner_history},
      True)
  
  update_summary(summoner["puuid"])

  asyncio.run(csmq.add_summoner(summoner))
  
  return summoner


def find_history(puuid):
  
  target_db = db_riot
    
  return target_db[col_history].find_one({"puuid":puuid})
  

def find_history_by_std_date(puuid, stdDate):
  summoner_history = find_history(puuid)
  
  if not summoner_history or "history" not in summoner_history:
    return {
        "queue":None,
        "tier":None,
        "leaguePoints":None
      }
  
  for h in summoner_history["history"]:
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
    
def update_renewable_time(puuid):
  summoner = db_riot[col].find_one({"puuid":puuid})
  
  # TODO 여기 나중에 예외처리
  if not summoner:
    return 
  
  summoner["updatedAt"] = datetime.now()
  db_riot[col].update_one(
      {"puuid": summoner["puuid"]},
      {"$set": summoner},
      True)
  
  
def moveHistoryFields(db):
  summoners = list(db[col].find({}))
  
  for i in range(len(summoners)):
    summoner = summoners[i]
    
    # 1. history 필드가 있으면 summoner_history에 이관시키기
    if "history" in summoner:
      
      summoner_history = {
        "puuid": summoner["puuid"],
        "history": summoner["history"]
      }
      
      db[col_history].update_one(
        {"puuid": summoner["puuid"]},
        {"$set": summoner_history},
      True)
      
      db[col].update_one(
        {"puuid": summoner["puuid"]},
        {"$unset": {"history":""}})
      

def update_summary(puuid):
  summoner = find_by_puuid(puuid)
  
  if not summoner:
    return
  
  summoner["mostLanes"] = find_most_lane(puuid)
  summoner["mostChampionIds"] = find_most_champions(puuid)
  
  db_riot[col].update_one(
    {"puuid": summoner["puuid"]},
    {"$set":summoner},
    True)
  
def find_most_lane(puuid):
  
  # 1. summonerMatches에서 최근 20개의 gameId를 가져오기
  pipeline_lane = [
    {"$match":{
      "puuid":puuid,
      "lane":{
        "$in": ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
      }
    }},
    {"$sort": {"matchId": -1}},
    {"$limit": 20},
    {"$group":{
     "_id":"$lane",
     "plays":{"$sum":1} 
    }},
    {"$sort": {
      "plays": -1
    }},
    {"$project":{
      "lane":"$_id",
      "_id":0
    }}
  ]
  aggregated = list(db_riot["participants"].aggregate(pipeline_lane))
  
  return [r["lane"] for r in aggregated][:3]