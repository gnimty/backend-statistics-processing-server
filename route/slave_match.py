from flask import Blueprint
from thread_task import CustomMatchThreadTask
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
    # 수집한 raw data 압축하여 cloud로 전송
    {
      "job":collect_match,
      "method":"interval",
      "time":{
        "hours":2
      }
    }
  ]