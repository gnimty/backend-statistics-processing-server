from flask import Blueprint
from thread_task_match import CustomMatchThreadTask
from config.appconfig import current_config as config


slave_match_route = Blueprint('slave_match_route', __name__)

@slave_match_route.route("/status")
def get_status():
    return {
        "message": f"{CustomMatchThreadTask.await_match_ids_len()}개 match id 대기 중",
        "alive_threads": f"{CustomMatchThreadTask.alive_thread_len()}개",
    }


@slave_match_route.route("/collect/match", methods=["POST"])
def collect_match():
    CustomMatchThreadTask.start(skip = True if config.PROCESS=="slave_master_2" else False)

    return {
        "message": "success"
    }

@slave_match_route.route("/collect/match/stop", methods=["POST"])
def stop_collect_match():
    CustomMatchThreadTask.stop()

    return {
        "message": "success"
    }
    
schedule = [
    {
      "job":collect_match,
      "method":"cron",
      "time":{
        "hour":'2-22/2'
      }
    },
    {
        "job":stop_collect_match,
        "method":"cron",
        "time":{
            "hour": 23,
            "minute": 55,
        }
    },
    {
      "job":collect_match,
      "id":"re_collect_match",
      "method":"cron",
      "time":{
            "hour": 0,
            "minute": 20,
        }
    },
    
  ]