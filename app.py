import os
# import dotenv
# dotenv.load_dotenv()
import datetime
from scheduler import start_schedule  # 스케줄러 로드
from error.custom_exception import *  # custom 예외
from error.error_handler import error_handle  # flask에 에러핸들러 등록
from flask_request_validator import *  # parameter validate
from flask import Flask, request

from config.appconfig import current_config  # 최초 환경변수 파일 로드
from config.mongo import Mongo
from config.redis import Redis
import asyncio
from utils.summoner_name import *

app = Flask(__name__)
env = os.getenv("APP_ENV") or "local"
app.config.from_object(current_config)  # 기본 앱 환경 가져오기
process = os.getenv("PROCESS") or "master"
import log
logger = log.get_logger()  # 로거

error_handle(app)  # app 공통 에러 핸들러 추가

logger.info("%s 환경에서 실행, PROCESS = %s",env, process)

Mongo.set_client()
Redis.set_client()

from modules import summoner, match, season



    
@app.route("/refresh/match/<match_id>", methods=["POST"])
def refresh_match(match_id):
  match.delete_match(match_id)
  match.update_match(match_id)
    

## Warning!!!!! 시즌 정보 프동기화 필요 ##
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
  
if process=="master":
  from route import master
  app.register_blueprint(master.master_route)
  
  if env!="local":
    start_schedule(master.schedule)
    logger.info("소환사 배치 및 통계 배치가 시작됩니다.")
  
elif process=="slave_summoner":
  from route import slave_summoner
  app.register_blueprint(slave_summoner.slave_summoner_route)
  
  loop = asyncio.get_event_loop()

  task = loop.create_task(slave_summoner.collect_summoners())
  loop.run_until_complete(task)
  
elif process=="slave_match" or process=="slave_match_2":
  from route import slave_match
  app.register_blueprint(slave_match.slave_match_route)
  
  loop = asyncio.get_event_loop()

  task = loop.create_task(slave_match.collect_match())
  loop.run_until_complete(task)


if __name__ == "__main__":
  app.run(
    host = app.config["FLASK_HOST"], 
    port=app.config["FLASK_PORT"],
    debug=bool(int(app.config["FLASK_DEBUG"])),
    threaded=True
  )
  
  
# app.register_blueprint(route, url_prefix='/route')


# @app.route('/batch/summoner', methods=["POST"])
# def summoner_rank_batch():
#   """모든 소환사의 rank 정보 업데이트
#   """
  
#   league_entries.update_all_summoners()
  
#   return {"message":"성공적으로 소환사 정보를 업데이트하였습니다."}

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

# @app.route("/batch/champion/statistics", methods=["POST"] )
# def generate_champion_statistics():
#   champion_analysis.championAnalysis()
  
#   return {"message":"통계정보 생성 완료"}

# @app.route("/memory-usage")
# def get_memory_usage():
  
#   memory_usage_dict = dict(psutil.virtual_memory()._asdict())
#   memory_usage_percent = memory_usage_dict['percent']
#   pid = os.getpid()
#   current_process = psutil.Process(pid)
#   current_process_memory_usage_as_KB = current_process.memory_info()[0] / 2.**20
#   print(f"AFTER  CODE: Current memory KB   : {current_process_memory_usage_as_KB: 9.f} KB")
    
#   return {
#     "memory_usage":f"{current_process_memory_usage_as_KB: 9.3f} KB",
#     "memory_usage_percent":f"{memory_usage_percent}%",
    
#   }