from riot_requests import summoner_v4, league_exp_v4
from datetime import datetime
from utils.summoner_name import *
from modules.tier_division_mmr import MMR
from config.mongo import Mongo
import asyncio
from community import csmq
from error.custom_exception import *

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

def clear_summoner():
  update_operation = {"$set": {
    "tier" : None,
    "queue" : None,
    "leaguePoints" : None,
    "wins" : None,
    "losses" : None,
    "mmr" : None,
    "tier_flex" : None,
    "queue_flex" : None,
    "leaguePoints_flex" : None,
    "wins_flex" : None,
    "losses_flex" : None,
    "mmr_flex" : None
  }}
  
  db_riot[col].update_many({}, update_operation)
  db_riot["summoner_history"].delete_many({})
  db_riot["summoner_history_flex"].delete_many({})
  
def delete_one_by_puuid(puuid):
  db_riot[col].delete_one({"puuid":puuid})

def find_all_puuids() -> list:
  puuids = list(db_riot[col].find({}, {"_id":0, "puuid":1}))
  
  return [s['puuid'] for s in puuids if 'puuid' in s]

def find_all_puuids_with_cond(cond) -> list:
  puuids = list(db_riot[col].find(cond, {"_id":0, "puuid":1}))
  
  return [s['puuid'] for s in puuids if 'puuid' in s]


def find_one_by_summoner_id(summoner_id):
  """소환사 ID로 소환사 정보 조회

  Args:
      db (connection)
      summonerId (str)

  Returns:
      summoner
  """
  
  summoner = db_riot[col].find_one(
    {'id': summoner_id},
    {"_id": 0, "accountId": 0})

  if not summoner:
    logger.info("소환사 정보가 존재하지 않습니다.")
  
  return summoner

def find_one_by_internal_tagname(internal_tagname):
  summoner = db_riot[col].find_one(
    {"internal_tagname":internal_tagname}
  )
  
  if not summoner:
    logger.info("소환사 정보가 존재하지 않습니다.")
  
  return summoner

# puuid에 해당하는 tagName 및 랭크 정보 업데이트
def update_by_puuid(puuid, tagNameEntry=None):
  summoner = summoner_v4.get_by_puuid(puuid, tagNameEntry=tagNameEntry)
  entry = league_exp_v4.get_summoner_by_id(summoner.get("id"))
  
  update(summoner, entry, check_name=True)

def recursive_tagline_update(summoner):
  matched = db_riot[col].find_one({"internal_tagname":summoner["internal_tagname"],
                                   "puuid":{"$ne":summoner["puuid"]}})
  if matched:
    logger.info("%s와 동일한 internal tagname 소환사 확인, 업데이트", summoner["internal_tagname"])
    tagNameEntry = summoner_v4.get_summoner_by_puuid(matched["puuid"])
    matched["name"] = tagNameEntry["gameName"]
    matched["internal_name"] = make_internal_name(matched["name"])
    matched["tagLine"] = tagNameEntry["tagLine"]
    matched["internal_tagname"] = f"{matched['internal_name']}#{make_tagname(matched['tagLine'])}"
    
    db_riot[col].update_one({"puuid":matched["puuid"]}, {"$set":matched})
    logger.info("업데이트 후 internal tagname : %s", matched["internal_tagname"])
    recursive_tagline_update(matched)
    

# 이부분 코드 완전히 개선해야 함
def update_by_summoner_brief(summoner_brief, collect = False)->str:
  summoner = find_one_by_summoner_id(summoner_brief["summonerId"]) 
  
  if not summoner: # 기존에 존재하지 않는 데이터 -> request를 통해 붙어서 옴
    summoner = summoner_v4.get_by_summoner_id(summoner_brief["summonerId"])
    update(summoner, summoner_brief, check_name = True, collect = collect)
  else: # 기존에 존재하는 데이터 -> 랭킹 갱신 시 체크하지 않음
    update(summoner, summoner_brief, collect = collect)  
    
  return summoner["puuid"]

def get_duplicates():
  return db_riot[col].aggregate([
    {
      "$group": {
        "_id": "$puuid",
        "count": { "$sum": 1 },
      }
    },
    {
      "$match": {
        "count": { "$gt": 1 }
      }
    },
])
  

def find_by_puuid(puuid):
  summoner = db_riot[col].find_one(
    {"puuid": puuid}, 
    {"_id": 0})

  return summoner


# check_name : tagName 갱신을 거친 데이터일 때 True -> 업데이트 시 tagName 반영하지 않음
# check_refresh : 전적 갱신 시 타이머 적용할 때 True -> updateAt 필드를 갱신하지 않음
# collect : 유저정보 collect 시 호출된 메소드일 때 True -> 소환사 정보 집계 로직을 수행하지 않음
def update(summoner, summoner_brief, check_name = False, check_refresh = False, collect = False):
  """summoner 정보 업데이트 및 history collection 업데이트

  Args:
      summoner: 현재 정보
      summoner_brief: 조회한 최신 entry 정보
  """
  
  if not summoner:
    return None
  
  if "rank" in summoner:
    del summoner["rank"] # 랭크 정보 삭제
    
  if not summoner_brief:
    summoner_brief = dict()
  
  if not check_name: # tagLine 갱신을 거치지 않은 데이터일 경우 DB 업데이트에 반영하지 않음
    del summoner["name"]
    del summoner["internal_name"]
    del summoner["internal_tagname"]
  else:
    # DB에 동일한 internal tagname이 존재한다면 해당 소환사 업데이트
    recursive_tagline_update(summoner)

  # history list 존재하면 갖다 붙이고 없으면 새로 생성
  for queue in ["RANK_SOLO_5x5", "RANK_FLEX_SR"]:
    suffix= "" if queue=="RANK_SOLO_5x5" else "_flex"
    
    # if summoner_brief.get("tier"+suffix): # 솔로랭크, 자유랭크 정보가 각각 포함되어 있다면 => unrank update를 위해 무조건 실행
    if summoner_brief.get("tier"+suffix)!=None:
      summoner_brief["tier"+suffix] = division[summoner_brief.get("tier"+suffix)]
    summoner["tier"+suffix] = summoner_brief.get("tier"+suffix)
    
    summoner["queue"+suffix] = summoner_brief.get("queue"+suffix)
    if summoner["queue"+suffix]:
      summoner["queue"+suffix] = summoner["queue"+suffix].lower()
    summoner["leaguePoints"+suffix] = summoner_brief.get("leaguePoints"+suffix)
    summoner["wins"+suffix] = summoner_brief.get("wins"+suffix)
    summoner["losses"+suffix] = summoner_brief.get("losses"+suffix)
    summoner["mmr"+suffix] = MMR.rank_to_mmr(summoner.get("queue"+suffix), summoner.get("tier"+suffix), int(summoner.get("leaguePoints"+suffix)) if summoner.get("leaguePoints"+suffix) else None)  
    
    # summoner_history는 entry정보에 해당 큐 정보가 포함되어 있을 때만 추가 및 갱신
    if summoner_brief.get("tier"+suffix):
      summoner_history = find_history(summoner["puuid"], queue)
      if not summoner_history or not summoner_history.get("history"):
        summoner_history = {
            "puuid": summoner["puuid"],
            "history": [{
                "queue": summoner_brief.get("queue"+suffix),
                "tier":summoner_brief.get("tier"+suffix),
                "leaguePoints":summoner_brief.get("leaguePoints"+suffix),
                "updatedAt":datetime.now()
            }]
        }
      else:
        # history 맨 처음에 insert
        summoner_history["history"].insert(0, {
          "queue":summoner_brief.get("queue"+suffix),
          "tier":summoner_brief.get("tier"+suffix),
          "leaguePoints":summoner_brief.get("leaguePoints"+suffix),
          "updatedAt":datetime.now(),
        })
      
      target_collection = "summoner_history"+suffix
      
      db_riot[target_collection].update_one(
        {"puuid": summoner["puuid"]},
        {"$set": summoner_history},
        True)
    
  if check_refresh:
    summoner["updatedAt"] = datetime.now()
  
  if "accountId" in summoner:
    del summoner["accountId"]
  
  asyncio.run(csmq.add_summoner(summoner))
  
  db_riot[col].update_one(
      {"puuid": summoner["puuid"]},
      {"$set": summoner},
      True)
  
  return summoner


def find_history(puuid, queue):
  if queue=="RANK_SOLO_5x5":
    return db_riot["summoner_history"].find_one({"puuid":puuid})
  elif queue=="RANK_FLEX_SR":
    return db_riot["summoner_history_flex"].find_one({"puuid":puuid})
  return None
  
def find_history_by_std_date(puuid, stdDate, mode):
  summoner_history = find_history(puuid, mode)
  
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
  
  summoner["renewableAt"] = datetime.now()
  db_riot[col].update_one(
      {"puuid": summoner["puuid"]},
      {"$set": summoner},
      True)


def update_summary(puuid):
  summoner = find_by_puuid(puuid)
  
  if not summoner:
    return
  
  summoner["mostLanes"] = find_most_lane(puuid)
  summoner["mostChampionIds"] = find_most_champions(puuid)
  
  summoner["mostLanes_flex"] = find_most_lane(puuid, queueId=440)
  summoner["mostChampionIds_flex"] = find_most_champions(puuid, queueId=440)
  
  db_riot[col].update_one(
    {"puuid": summoner["puuid"]},
    {"$set":summoner},
    True)
  
# summonerMatches에서 최근 20개의 gameId를 가져와서 자주 가는 라인 정보를 보어주기
def find_most_lane(puuid, queueId=420):
  
  pipeline_lane = [
    {"$match":{
      "puuid":puuid,
      "queueId":queueId,
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

def find_most_champions(puuid, queueId=420):
  pipeline_lane = [
    {"$match":{
      "puuid":puuid,
      "queueId":queueId,
    }},
    {"$sort": {"matchId": -1}},
    {"$limit": 20},
    {"$group":{
      "_id":"$championId",
      "plays":{"$sum":1}
    }},
    {"$sort": {
      "plays": -1
    }},
    {"$project":{
      "championId":"$_id",
      "_id":0
    }}
  ]
  
  aggregated = list(db_riot["participants"].aggregate(pipeline_lane))
  
  return [r["championId"] for r in aggregated][:3]
  
  # target_col = col
  # if queueId== 440:
  #   target_col = "summoner_plays_flex"
  # pipeline_champion =  [
  #   {
  #     "$match":{
  #       "puuid":puuid,
  #       "season":season_name
  #     }
  #   },
  #   {
  #     "$sort":{
  #       "totalPlays": -1  
  #     }
  #   },
  #   {
  #     "$limit":3
  #   },
  #   {
  #     "$project":{
  #       "_id":0,
  #       "championId":1   
  #     }
  #   }
  # ]
  
  
  # aggregated = list(db[target_col].aggregate(pipeline_champion))
  
  # result  = [r["championId"] for r in aggregated]
  
  # return result       

# def moveHistoryFields(db):
#   summoners = list(db[col].find({}))
  
#   for i in range(len(summoners)):
#     summoner = summoners[i]
    
#     # 1. history 필드가 있으면 summoner_history에 이관시키기
#     if "history" in summoner:
      
#       summoner_history = {
#         "puuid": summoner["puuid"],
#         "history": summoner["history"]
#       }
      
#       db[col_history].update_one(
#         {"puuid": summoner["puuid"]},
#         {"$set": summoner_history},
#       True)
      
#       db[col].update_one(
#         {"puuid": summoner["puuid"]},
#         {"$unset": {"history":""}})