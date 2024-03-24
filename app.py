import os
# import dotenv
# dotenv.load_dotenv()

from scheduler import start_schedule  # 스케줄러 로드
from error.custom_exception import *  # custom 예외
from error.error_handler import error_handle  # flask에 에러핸들러 등록
from flask_request_validator import *  # parameter validate
from flask import Flask

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
import time
logger = log.get_logger()  # 로거

error_handle(app)  # app 공통 에러 핸들러 추가

logger.info("%s 환경에서 실행, PROCESS = %s",env, process)

Mongo.set_client()
Redis.set_client()

from modules import match
from threading import Thread

@app.route("/raw/<match_id>", methods=["GET"])
def get_raw_match(match_id):
  result = match.get_raw(match_id)
  return result


if process=="master":
  from route import master
  app.register_blueprint(master.master_route)
  
  if env!="local":
    start_schedule(master.schedule)
    logger.info("소환사 배치 및 통계 배치가 시작됩니다.")
  
elif process=="slave_summoner":
  from route import slave_summoner
  app.register_blueprint(slave_summoner.slave_summoner_route)
  
  Thread(target = slave_summoner.collect_summoners, name="main").start()
  
  if env!="local":
    start_schedule(slave_summoner.schedule)
    logger.info("소환사 배치 및 통계 배치가 시작됩니다.")
  
elif process=="slave_match" or process=="slave_match_2":
  from route import slave_match
  app.register_blueprint(slave_match.slave_match_route)
  # redis load 이슈로 10초 기다리기
  time.sleep(10)
  Thread(target = slave_match.collect_match, name="main").start()


if __name__ == "__main__":
  app.run(
    host = app.config["FLASK_HOST"], 
    port=5000,
    debug=bool(int(app.config["FLASK_DEBUG"])),
    threaded=True
  )