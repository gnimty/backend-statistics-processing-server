import os
import asyncio
import requests, datetime, random
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

app = Flask(__name__)
env = os.getenv("APP_ENV") or "local"
app.config.from_object(current_config)  # 기본 앱 환경 가져오기

import log
logger = log.get_logger()  # 로거

error_handle(app)  # app 공통 에러 핸들러 추가

logger.info("%s 환경에서 실행",env)

# Datasource Connection set
Mongo.set_client()
Redis.set_client()

from modules import summoner, league_entries, match, version, crawl, season
from modules.analysis import champion as champion_analysis
from modules.raw_match import RawMatch
from riot_requests import summoner_v4
from gcs import upload

@app.route('/batch/summoner', methods=["POST"])
def summoner_rank_batch():
  """모든 소환사의 rank 정보 업데이트
  
  """
  league_entries.update_total_summoner()
  
  return {"message":"성공적으로 소환사 정보를 업데이트하였습니다."}

# @app.route('/batch/test', methods=["POST"])
# def summoner_rank_batch_test():
#   # updated_cnt = league_entries.update_all()
#   updated_cnt = league_entries.update_total_summoner()
  
#   return {"status": "ok", "updatedCnt": updated_cnt}


@app.route('/batch/match', methods=["POST"])
def summoner_match_batch():
  """소환사 정보 내에 있는 모든 소환사들의 summoner_match와 match정보를 업데이트
  
  Returns:
      updatedCnt(int) : 랭크 업데이트한 유저 수 
  """

  puuids = summoner.find_all_puuids()
  
  # 균일한 티어대 정보 수집을 위하여 shuffle
  random.shuffle(puuids)
  
  # 모든 puuid를 탐색하면서 해당 소환사가 진행한 모든 전적 정보 업데이트
  for puuid in puuids:
    match.update_matches_by_puuid(puuid)

  return {"status": "ok", "message": "전적 정보 배치가 완료되었습니다."}

## local test 전용 TODO 추후 삭제
@app.route('/scheduler/summoner/start')
def startSummonerBatchScheduler():
  start_schedule([
  # 2시간에 한번씩 소환사 정보 배치
  {
    "job":summoner_rank_batch,
    "method":"interval",
    "time": {
      "hours": app.config["SUMMONER_BATCH_HOUR"]
    }
  },
  ])
  logger.info("소환사 배치 스케줄 시작")
  return {"message":"scheduler started"}

@app.route("/batch/summoner/lookup/<gameName>/<tagLine>", methods=["POST"])
def lookup_summoner(gameName, tagLine):
  # 해당 소환사 이름과 tagLine이 일치하는 소환사 정보 갱신 또는 저장
  tagName = summoner_v4.get_tagline_by_name_and_tag(gameName, tagLine)
  if tagName==None:
    raise SummonerNotExists("소환사 정보가 존재하지 않습니다.")
  
  summoner.update_by_puuid(tagName.get("puuid"), tagName)
  
  return {"message":"해당 소환사 정보가 존재하여 업데이트합니다."}
  

@app.route("/batch/summoner/refresh/<puuid>", methods=["POST"] )
def refresh_summoner(puuid):
  
  # 만약 internal_name 해당하는 유저 정보가 존재한다면 가져온 summonerId로 refresh
  summoner_info = summoner.find_by_puuid(puuid)
  
  if not summoner_info:
    raise UserUpdateFailed("유저 전적 업데이트 실패")
  
  # 이후 해당 소환사의 summonerId로 소환사 랭크 정보 가져오기 -> diamond 이하라면 버리기
  entry = league_entries.get_summoner_by_id(summoner_info["id"], app.config["API_REQUEST_LIMIT"])
  
  if entry == None:
    raise UserUpdateFailed("유저 전적 업데이트 실패")    
  
  summoner.update(summoner_v4.get_by_puuid(puuid), entry, check_name=True, check_refresh=True)
  
  match.update_matches_by_puuid(summoner_info["puuid"], app.config["API_REQUEST_LIMIT"])
  
  ##### 소환사 정보 업데이트 치기 #####
  new_summoner_info = summoner.find_by_puuid(puuid)
  asyncio.run(csmq.renew_one(new_summoner_info))
  
  logger.info("app에서 업데이트 완료")
  ##### 소환사 정보 업데이트 치기 #####
  
  return {"message":"업데이트 완료"}
    
    
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

@app.route("/season/date", methods = ["PATCH"])
def update_season_starts():
  data = request.get_json()
  
  try:
    startAt = data["startsAt"]
    epoch_seconds = int(datetime.datetime.strptime(startAt, "%Y%m%d%H%M%S").timestamp())
    season.update_season(epoch_seconds)
    
  except Exception:
    return {
        "message":"잘못된 날짜 정보입니다."
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
  print(f"AFTER  CODE: Current memory KB   : {current_process_memory_usage_as_KB: 9.3f} KB")
    
    
  return {
    "memory_usage":f"{current_process_memory_usage_as_KB: 9.3f} KB",
    "memory_usage_percent":f"{memory_usage_percent}%",
    
  }

if env!="local":
  logger.info("소환사 배치 및 통계 배치가 시작됩니다.")
  
  start_schedule([
    # SUMMONER_BATCH_HOUR시간마다 소환사 정보 배치
    {
      "job":summoner_rank_batch,
      "method":"interval",
      "time": {
        "hours": app.config["SUMMONER_BATCH_HOUR"]
      }
    },
    # 자정에 챔피언 분석 정보 배치
    {
      "job":generate_champion_statistics,
      "method":"cron",
      "time":{
        "hour": 0
      }
    },
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
    {
      "job":summoner_match_batch,
      "method":"interval",
      "time": {
        "hours": app.config["MATCH_BATCH_HOUR"]
      }
    },
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
    threaded=True,
  )