from riot_requests import league_exp_v4
import logging
from modules import summoner
import threading
from error.custom_exception import *

logger = logging.getLogger("app")

in_task = False


def get_summoner_by_id(summoner_id):
  return league_exp_v4.get_summoner_by_id(summoner_id)


def task_under_master(tier, division, queue, collect):
  page = 1
  while True:
    entries = league_exp_v4.get_summoners_under_master(
        tier, division, queue=queue, page=page)

    if len(entries) == 0:
      break

    for entry in entries:
      summoner.update_by_summoner_brief(entry, collect=collect)

    page += 1


def task_over_master(league, queue, collect):
  entries = league_exp_v4.get_top_league(league, queue=queue)

  for entry in entries:
    summoner.update_by_summoner_brief(entry, collect=collect)


# collect = True 시 소환사 업데이트 정보를 csmq로 보내지 않음
def update_all_summoners(collect=False):
  global in_task

  if in_task:
    raise AlreadyInTask("이미 소환사 수집이 진행되고 있습니다.")

  in_task = True

  queues = ["RANKED_FLEX_SR", "RANKED_SOLO_5x5",]

  for queue in queues:
    leagues = ["challengerleagues", "grandmasterleagues", "masterleagues"]

    tiers = ["DIAMOND", "EMERALD", "PLATINUM",
             "GOLD", "SILVER", "BRONZE", "IRON"]

    divisions = ["I", "II", "III", "IV"]

    threads = []

    for league in leagues:
      t = threading.Thread(target=task_over_master,
                           args=(league, queue, collect))
      t.start()
      threads.append(t)

    for tier in tiers:
      for division in divisions:
        t = threading.Thread(target=task_under_master,
                             args=(tier, division, queue, collect))
        t.start()
        threads.append(t)

    for thread in threads:
      thread.join()

  in_task = False
