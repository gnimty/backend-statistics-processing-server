from flask import Blueprint
import os
# import dotenv
# dotenv.load_dotenv()
from flask_request_validator import *  # parameter validate
from modules import league_entries
import log

from utils.summoner_name import *


logger = log.get_logger()

slave_summoner_route = Blueprint('slave_summoner_route', __name__)

@slave_summoner_route.route("/collect", methods=["POST"])
def collect_summoners():
  league_entries.update_all_summoners(collect=True)

  return {
    "message":"success"
  }


schedule = [
    # 수집한 raw data 압축하여 cloud로 전송
    {
      "job":collect_summoners,
      "method":"interval",
      "time":{
        "hours":2
      }
    }
  ]

