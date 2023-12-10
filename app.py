import os
import asyncio
import requests, datetime
import psutil
from scheduler import start_schedule  # 스케줄러 로드
from error.custom_exception import *  # custom 예외
from error.error_handler import error_handle  # flask에 에러핸들러 등록
from flask_request_validator import *  # parameter validate
from flask import Flask, request

from config.appconfig import current_config  # 최초 환경변수 파일 로드
from config.mongo import Mongo
from config.redis import Redis

from community import csmq

from utils.summoner_name import *

app = Flask(__name__)
env = os.getenv("APP_ENV") or "local"
app.config.from_object(current_config)  # 기본 앱 환경 가져오기

import log
logger = log.get_logger()  # 로거

error_handle(app)  # app 공통 에러 핸들러 추가

logger.info("%s 환경에서 실행",env)

Mongo.set_client()
Redis.set_client()

from modules import summoner, league_entries, match, version, crawl, season, summoner_matches
from modules.analysis import champion as champion_analysis
from modules.raw_match import RawMatch
from riot_requests import summoner_v4

from thread_task import CustomMatchThreadTask


@app.route('/batch/summoner', methods=["POST"])
def summoner_rank_batch():
  """모든 소환사의 rank 정보 업데이트
  """
  
  league_entries.update_all_summoners()
  
  return {"message":"성공적으로 소환사 정보를 업데이트하였습니다."}

# ## local test 전용 TODO 추후 삭제
# @app.route('/scheduler/summoner/start')
# def startSummonerBatchScheduler():
#   start_schedule([
#   # 2시간에 한번씩 소환사 정보 배치
#   {
#     "job":summoner_rank_batch,
#     "method":"interval",
#     "time": {
#       "hours": app.config["SUMMONER_BATCH_HOUR"]
#     }
#   },
#   ])
#   logger.info("소환사 배치 스케줄 시작")
#   return {"message":"scheduler started"}

# 해당 tagName(gameName + tagLine)이 일치하는 소환사 정보 검색 또는 갱신
@app.route("/lookup/summoner/<game_name>/<tag_line>", methods=["POST"])
def lookup_summoner(game_name, tag_line):
  internal_tagname = f"{make_internal_name(game_name)} + {make_tagname(tag_line)}"
  
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
  

@app.route("/refresh/summoner/<puuid>", methods=["POST"] )
def refresh_summoner(puuid):
  
  # 만약 internal_name 해당하는 유저 정보가 존재한다면 가져온 summonerId로 refresh
  summoner_info = summoner.find_by_puuid(puuid)
  
  if not summoner_info:
    raise UserUpdateFailed("소환사 정보가 존재하지 않습니다. 업데이트 실패")
  
  # 이후 해당 소환사의 summonerId로 소환사 랭크 정보 가져오기 -> diamond 이하라면 버리기
  entry = league_entries.get_summoner_by_id(summoner_info["id"])
  
  if entry == None:
    raise UserUpdateFailed("유저 전적 업데이트 실패")    
  
  summoner.update(summoner_v4.get_by_puuid(puuid), entry, check_name=True, check_refresh=True)
  
  match.update_matches_by_puuid(summoner_info["puuid"])
  
  ##### 소환사 정보 업데이트 치기 #####
  new_summoner_info = summoner.find_by_puuid(puuid)
  asyncio.run(csmq.renew_one(new_summoner_info))
  
  logger.info("app에서 업데이트 완료")
  ##### 소환사 정보 업데이트 치기 #####
  
  return {"message":"업데이트 완료"}
    
@app.route("/refresh/match/<match_id>", methods=["POST"])
def refresh_match(match_id):
  match.delete_match(match_id)
  match.update_match(match_id)
    
@app.route("/batch/champion/statistics", methods=["POST"] )
def generate_champion_statistics():
  champion_analysis.championAnalysis()
  
  return {"message":"통계정보 생성 완료"}


@app.route("/crawl/update", methods = ["POST"])
def generate_crawl_data():
  latest_version = version.update_latest_version()
  
  version.update_champion_info(latest_version)
  version.update_item_info(latest_version)
  
  crawl.update_patch_note_summary(latest_version)
  crawl.update_sale_info()
  
  # API 서버에 알리기
  try:
    requests.patch(url=f"{app.config['COMMUNITY_HOST']}/asset/champion", timeout=4)
  except Exception:
    logger.error("API 서버 동기화에 실패했습니다.")
  
  return {
    "message":"챔피언 맵 정보 생성 완료"
  }


## Warning!!!!! ##
@app.route("/season/date", methods = ["PATCH"])
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

@app.route("/flush")
def flsuh_raw_datas():
  RawMatch.raw_to_parquet_and_upload(scale=10000)
  
  return {
    "message":"raw data 전송 완료"
  }

@app.route("/memory-usage")
def get_memory_usage():
  
  memory_usage_dict = dict(psutil.virtual_memory()._asdict())
  memory_usage_percent = memory_usage_dict['percent']
  pid = os.getpid()
  current_process = psutil.Process(pid)
  current_process_memory_usage_as_KB = current_process.memory_info()[0] / 2.**20
  print(f"AFTER  CODE: Current memory KB   : {current_process_memory_usage_as_KB: 9.f} KB")
    
  return {
    "memory_usage":f"{current_process_memory_usage_as_KB: 9.3f} KB",
    "memory_usage_percent":f"{memory_usage_percent}%",
    
  }
  
@app.route("/collect", methods=["POST"])
def collect_summoners():
  league_entries.update_all_summoners(reverse= True, collect=True)

  return {
    "message":"success"
  }
  
@app.route("/collect/match", methods=["POST"])
def collect_match():
  
  CustomMatchThreadTask.start()
  
  return {
    "message":"success"
  }

@app.route("/remove/duplicates")
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
  
@app.route("/test")
def test():
  alive = CustomMatchThreadTask.alive_thread_len()
  
  return {
    "message":f"{CustomMatchThreadTask.await_match_ids_len()}개 match id 대기 중",
    "thread_1":f"{alive[0]}개",
    "thread_2":f"{alive[1]}개"
  }

@app.route("/index")
def index():
  Mongo.add_index()
  
  return {
    "message":"success"
  }


if env!="local":
  logger.info("소환사 배치 및 통계 배치가 시작됩니다.")
  
  start_schedule([
    
    # SUMMONER_BATCH_HOUR시간마다 소환사 정보 배치
    # {
    #   "job":summoner_rank_batch,
    #   "method":"interval",
    #   "time": {
    #     "hours": app.config["SUMMONER_BATCH_HOUR"]
    #   }
    # },
    # 자정에 챔피언 분석 정보 배치
    # {
    #   "job":generate_champion_statistics,
    #   "method":"cron",
    #   "time":{
    #     "hour": 0
    #   }
    # },
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
      "method":"cron",
      "time":{
        "hour": 4
      }
    }
  ])

if __name__ == "__main__":
  app.run(
    host = app.config["FLASK_HOST"], 
    port=app.config["FLASK_PORT"],
    debug=bool(int(app.config["FLASK_DEBUG"])),
    threaded=True
  )