from flask import Blueprint
from flask_request_validator import *  # parameter validate
import log
from thread_task_summoner import CustomSummonerTask
from utils.summoner_name import *

logger = log.get_logger()

slave_summoner_route = Blueprint('slave_summoner_route', __name__)

@slave_summoner_route.route("/status")
def get_status():
    return {  
        "alive_threads": f"{CustomSummonerTask.alive_thread_len()}개",
    }

@slave_summoner_route.route("/collect", methods=["POST"])
def collect_summoners():
  CustomSummonerTask.start(collect=False)

  return {
    "message":"success"
  }
  
@slave_summoner_route.route("/collect/stop", methods=["POST"])
def stop_collect_summoners():
  CustomSummonerTask.stop()

  return {
    "message":"success"
  }

schedule = [
    {
      "job":collect_summoners,
      "method":"cron",
      "time":{
        "hour":'3-21/3'
      }
    },
    {
      "job":stop_collect_summoners,
      "method":"cron",
      "time":{
          "hour": 23,
          "minute": 55,
      }
    },
  ]

