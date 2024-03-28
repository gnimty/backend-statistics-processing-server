from riot_requests import league_exp_v4
import logging
from error.custom_exception import *

logger = logging.getLogger("app")

def get_summoner_by_id(summoner_id):
  return league_exp_v4.get_summoner_by_id(summoner_id)


def get_summoner_entries_under_master(tier, division, queue, page):
  return league_exp_v4.get_summoners_under_master(
        tier, division, queue=queue, page=page)

def get_summoner_entries_over_master(league, queue):
  return league_exp_v4.get_top_league(league, queue = queue)