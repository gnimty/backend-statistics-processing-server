import os, dotenv
from scheduler import start_schedule  # 스케줄러 로드

from error.custom_exception import *  # custom 예외
from error.error_handler import error_handle  # flask에 에러핸들러 등록
from flask_request_validator import *  # parameter validate
from flask import Flask

from config.mongo import mongoClient

from scheduler import start_schedule

# dotenv.load_dotenv(dotenv_path=".env")
env = os.getenv("APP_ENV") or "local"
from config.config import config  # 최초 환경변수 파일 로드
import logging

app = Flask(__name__)
app.config.from_object(config[env])  # 기본 앱 환경 가져오기

from config.redis import redisClient

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
rd = redisClient(app)

from modules import summoner, league_entries, match, summoner_matches, summoner_plays
from modules.analysis import champion as champion_analysis
from modules import version, crawl 

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
    
    match.updateMatchesByPuuid(puuid, db_riot, api_limit=app.config["BATCH_LIMIT"])

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
  logger.info("소환사 배치 스케줄 시작")
  return {"message":"scheduler started"}


@app.route("/batch/summoner/refresh/<puuid>", methods=["POST"] )
def refreshSummonerInfo(puuid):
  
  # 만약 internal_name 해당하는 유저 정보가 존재한다면 가져온 summonerId로 refresh
  summonerInfo = summoner.findSummonerByPuuid(db_riot,puuid)
  
  if not summonerInfo:
    raise UserUpdateFailed("유저 전적 업데이트 실패")    
    
  # 이후 해당 소환사의 summonerId로 소환사 랭크 정보 가져오기 -> diamond 이하라면 버리기
  entry = summoner.findSummonerRankInfoBySummonerId(summonerInfo["id"], app.config["API_REQUEST_LIMIT"])
  
  # TODO 현재는 개인랭크 업데이트만 하고 있기 때문에 추후에 변경해야 함
  if entry==None:
    raise UserUpdateFailed("유저 전적 업데이트 실패")    
  
  entry["queue"] = entry["tier"].lower()
  entry["tier"] = entry["rank"]
  del entry["rank"]
  if entry["queue"] not in ["master", "challenger", "grandmaster"]:
    raise UserUpdateFailed("유저 전적 업데이트 실패")    
  
  summoner.updateSummoner(db_riot, summonerInfo, entry)
  
  match.updateMatchesByPuuid(summonerInfo["puuid"], app.config["API_REQUEST_LIMIT"])
  
  summoner.summonerRequestLimit(db_riot, puuid)
  
  return {"message":"업데이트 완료"}
    
@app.route("/batch/champion/statistics", methods=["POST"] )
def generateChampionStatistics():
  champion_analysis.championAnalysis(db_riot)
  
  return {"message":"통계정보 생성 완료"}


@app.route("/crawl/update", methods = ["POST"])
def createCrawlData():
  
  version.updateLatestVersion(rd)
  
  version.updateChampionMap(db_riot, rd)

  crawl.updateSaleInfos(db_riot)
  
  return {
    "message":"챔피언 맵 정보 생성 완료"
  }

if env=="dev":
  logger.info("소환사 배치 및 통계 배치가 시작됩니다.")
  
  start_schedule([
    # [SUMMONER_BATCH_HOUR]시간마다 소환사 정보 배치
    {
      "job":leagueEntriesBatch,
      "method":"interval",
      "time": {
        "hours": app.config["SUMMONER_BATCH_HOUR"]
      }
    },
    # 자정에 챔피언 분석 정보 배치
    {
      "job":generateChampionStatistics,
      "method":"cron",
      "time":{
        "hour": 0
      }
    },
    # [MATCH_BATCH_HOUR]시간마다 전적정보 배치
    # cf) 처리량이 매우 많고 API_LIMIT이 한정적이라 덮어씌워질 가능성 높음
    {
      "job":matchBatch,
      "method":"cron",
      "time":{
        "hour": app.config["MATCH_BATCH_HOUR"]
      }
    },
    {
      "job":createCrawlData,
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
    debug=bool(int(app.config["FLASK_DEBUG"])))