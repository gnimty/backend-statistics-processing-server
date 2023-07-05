import json
from bson import json_util
from scheduler import start_schedule  # 스케줄러 로드

from error.custom_exception import *  # custom 예외
from error.error_handler import error_handle  # flask에 에러핸들러 등록
from flask_request_validator import *  # parameter validate
from flask import Flask, jsonify, request, url_for
import os, dotenv
from config.mongo import mongoClient
from utils.summoner_name import makeInternalName

from scheduler import start_schedule

env = os.getenv("APP_ENV") or "local"

if env == "local":
  dotenv.load_dotenv(dotenv_path="./env/.env")
from config.config import config  # 최초 환경변수 파일 로드
import logging

app = Flask(__name__)
app.config.from_object(config[env])  # 기본 앱 환경 가져오기
logger.info("PORT : %s", os.environ.get("FLASK_RUN_PORT"))


log_dir = './logs'  # 로그 남길 디렉토리 (없으면 자동으로 생성)
if not os.path.exists(log_dir):
    os.mkdir(log_dir)
from utils import initialize_logger

logger = logging.getLogger("app")  # 로거

error_handle(app)  # app 공통 에러 핸들러 추가

logger.info("%s 환경에서 실행",env)

# Mongo Connection
db_riot = mongoClient(app, app.config["MONGO_RIOTDATA_DB"])  # pymongo connection
db_stat = mongoClient(app, app.config["MONGO_STATISTICS_DB"])  # pymongo connection

# Redis Connection
# RedisClient.init(
#       host = app.config.get("REDIS_HOST") or "localhost", 
#       port = int(app.config.get("REDIS_PORT")) or 6379)

from modules import summoner, league_entries, match, summoner_matches

@app.route('/batch', methods=["POST"])
def leagueEntriesBatch():
  """수동 배치돌리기
  league_entries 가져와서 rank정보 업데이트해주기
  
  Returns:
      updated(int) : 마스터 이상 유저 업데이트수
  """
  updated_summoner_count = league_entries.updateAll(db_riot, int(app.config["BATCH_LIMIT"]))
  return {"status": "ok", "updated": updated_summoner_count}


@app.route('/batch/match', methods=["POST"])
def matchBatch():  # 전적정보 배치 수행
  """수동 배치돌리기
  소환사 정보 내에 있는 모든 소환사들의 summoner_match와 match정보를 업데이트
  실행 당시의 summoners 안에 있는 소환사들만 업데이트해주기
  
  Returns:
      updated(int) : 마스터 이상 유저 업데이트수
  """

  # 1. league_entries 가져오기
  puuids = summoner.findAllSummonerPuuid(db_riot)
  # 2. league_entries 안의 소환사 아이디를 돌아가면서 summoner_matches를 업데이트하기
  for puuid in puuids:
    
    matchIds = summoner_matches.updateAndGetTotalMatchIds(db_riot, app.config["BATCH_LIMIT"], puuid)
    for matchId in matchIds:
      match.updateMatch(db_riot, db_stat, matchId, app.config["BATCH_LIMIT"])

  return {"status": "ok", "message": "전적 정보 배치가 완료되었습니다."}

@app.route('/scheduler/summoner/start')
def startSummonerBatchScheduler():
  start_schedule([
  # 2시간에 한번씩 소환사 정보 배치
  {
    "job":leagueEntriesBatch,
    "method":"interval",
    "time": {
      "hours": app.config["SUMMONER_BATCH_HOUR"]
    }
  },
  ])
  return {"message":"scheduler started"}


# start_schedule([
#   # 2시간에 한번씩 소환사 정보 배치
#   {
#     "job":leagueEntriesBatch,
#     "method":"cron",
#     "time":{
#       "minute":1
#     }
#   },
# ])
#   # 4시 정각에 돌아가도록 설정
#   {
#     "job":matchBatch,
#     "method":"cron",
#     "time":{
#       "hour":app.config["BATCH_HOUR"]
#     }
#   }
#   ])

# if __name__ == "__main__":
#   app.run(
#     host = app.config["FLASK_HOST"], 
#     port=app.config["FLASK_PORT"],
#     debug=app.config["FLASK_DEBUG"])