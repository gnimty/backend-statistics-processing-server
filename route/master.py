from flask import Blueprint, request
from utils.summoner_name import *
from modules import summoner, league_entries, match, version, crawl, season
from riot_requests import summoner_v4
from error.custom_exception import *  # custom 예외
import asyncio
from community import csmq
from modules.raw_match import RawMatch
import requests
import datetime
from config.appconfig import current_config as config

master_route = Blueprint('master_route', __name__)

# 해당 tagName(gameName + tagLine)이 일치하는 소환사 정보 검색 또는 갱신
@master_route.route("/lookup/summoner/<game_name>/<tag_line>", methods=["POST"])
def lookup_summoner(game_name, tag_line):
  internal_tagname = f"{make_internal_name(game_name)}#{make_tagname(tag_line)}"
  
  found = summoner.find_one_by_internal_tagname(internal_tagname)
  
  if found:
    return {
      "message":"소환사 정보가 이미 존재합니다.",
      "puuid": found["puuid"]
    }
    
  tagname = summoner_v4.get_tagname_by_name_and_tagline(game_name, tag_line)
  
  if tagname==None:
    raise SummonerNotExists("소환사 정보가 존재하지 않습니다.")
  
  puuid = tagname.get("puuid")
  summoner.update_by_puuid(puuid, tagname)
  
  return {
    "message":"해당 소환사 정보가 존재하여 업데이트합니다.",
    "puuid": puuid
    }
  
@master_route.route("/refresh/summoner/<puuid>", methods=["POST"] )
def refresh_summoner(puuid):
  
  # 만약 internal_name 해당하는 유저 정보가 존재한다면 가져온 summonerId로 refresh
  summoner_info = summoner.find_by_puuid(puuid)
  
  if not summoner_info:
    raise UserUpdateFailed("소환사 정보가 존재하지 않습니다. 업데이트 실패")
  
  # 이후 해당 소환사의 summonerId로 소환사 랭크 정보 가져오기 -> diamond 이하라면 버리기
  entry = league_entries.get_summoner_by_id(summoner_info["id"])
  
  summoner.update(summoner_v4.get_by_puuid(puuid), entry, check_name=True, check_refresh=True)
  
  match.update_matches_by_summoner(summoner_info)
  
  ##### 소환사 정보 업데이트 치기 #####
  new_summoner_info = summoner.find_by_puuid(puuid)
  asyncio.run(csmq.renew_one(new_summoner_info))
  
  logger.info("app에서 업데이트 완료")
  ##### 소환사 정보 업데이트 치기 #####
  
  return {"message":"업데이트 완료"}

@master_route.route("/flush")
def flsuh_raw_datas():
  RawMatch.raw_to_parquet_and_upload(scale=10000)
  
  return {
    "message":"raw data 전송 완료"
  }

@master_route.route("/crawl/update", methods = ["POST"])
def generate_crawl_data():
  latest_version = version.update_latest_version()
  
  version.update_champion_info(latest_version)
  version.update_item_info(latest_version)
  
  crawl.update_patch_note_summary(latest_version)
  
  try:
    crawl.update_sale_info()
  except Exception:
    logger.error("챔피언 및 스킨 할인 정보 불러오기에 실패했습니다.")
  
  # API 서버에 알리기
  try:
    requests.patch(url=f"{config.COMMUNITY_HOST}/asset/champion", timeout=4)
  except Exception:
    logger.error("API 서버 동기화에 실패했습니다.")
  
  return {
    "message":"버전 및 크롤링 정보 업데이트 완료"
  }
    
@master_route.route("/refresh/match/<match_id>", methods=["POST"])
def refresh_match(match_id):
  match.delete_match(match_id)
  
  match.update_match(match_id)
  
  return {
    "message":"매치 정보 갱신 완료"
  }

## Warning!!!!! 시즌 정보 프동기화 필요 ##
@master_route.route("/season/date", methods = ["PATCH"])
def update_season_starts():
  data = request.get_json()
  
  try:
    # TODO 나중에 안전장치 다시 만들기
    key = data["key"]
    
    if not key or key!="rlathfals12#":
      raise Exception()
    
    startAt = datetime.datetime.strptime(data["startAt"], "%Y%m%d%H%M%S")
    seasonName = data["seasonName"]
    
    is_changed = season.update_season(startAt, seasonName)
    
    if is_changed:
      match.clear()
      summoner.clear_summoner()
      
  except Exception:
    return {
        "message":"시즌 정보 업데이트에 실패했습니다."
      }
  
  # try:
  #   startAt = data["startAt"]
  #   # season = data["season"]
  #   seasonName = data["seasonName"]
  #   season.update_season(startAt, seasonName)
    
  # except Exception:
  #   return {
  #       "message":"잘못된 날짜 정보입니다."
  #     }
    
  return {
    "message":"시즌 정보 갱신 완료"
  }

@master_route.route("/remove/duplicates")
def remove_duplicates():
  results = list(summoner.get_duplicates())
  for result in results:
    puuid = result["_id"]
    limit = int(result["count"]) - 1 
    for _ in range(limit):
      summoner.delete_one_by_puuid(puuid)
      
    logger.info("puuid = %s 중복 제거", puuid)
  
  
  results = list(match.get_duplicates())
  
  for result in results:
    match_id = result["_id"]
    limit = int(result["count"]) -1 
    for _ in range(limit):
      match.delete_one_by_match_id(match_id)
      
    logger.info("match id = %s 중복 제거", match_id)
  
  results = list(match.get_duplicates_team())
  
  for result in results:
    match_id = result["_id"]["matchId"]
    team_id = result["_id"]["teamId"]
    limit = int(result["count"]) - 1 
    for _ in range(limit):
      match.delete_team(match_id, team_id)
    logger.info("match id = %s, team id = %s 중복 제거", match_id, team_id)
    logger.info("")

  
  results = list(match.get_duplicates_participant())
  
  for result in results:
    match_id = result["_id"]["matchId"]
    participant_id = result["_id"]["participantId"]
    limit = int(result["count"]) - 1 
    for _ in range(limit):
      match.delete_participant(match_id, participant_id)
    logger.info("match id = %s, participant id = %s 중복 제거", match_id, participant_id)
  
  return {
    "message":"success"
  }



## 비동기 request를 통해 slave process API 요청




schedule = [
    # 수집한 raw data 압축하여 cloud로 전송
    {
      "job":flsuh_raw_datas,
      "method":"cron",
      "time":{
        "hour":0
      }
    },
    # [MATCH_BATCH_HOUR]시간마다 전적정보 배치
    # cf) 처리량이 매우 많고 API_LIMIT이 한정적이라 덮어씌워질 가능성 높음
    # {
    #   "job":summoner_match_batch,
    #   "method":"interval",
    #   "time": {
    #     "hours": app.config["MATCH_BATCH_HOUR"]
    #   }
    # },
    {
      "job":generate_crawl_data,
      "method":"interval",
      "time":{
        "hour": 4
      }
    }
  ]

