from riot_requests import league_exp_v4
import logging
from modules import summoner
from error.custom_exception import RequestDataNotExists
import threading


logger = logging.getLogger("app")

def task(tier, division, queue, reverse):
  entries = league_exp_v4.get_summoners_under_master(tier, division, queue = queue)
  
  if reverse:
    entry = reversed(entry)
  
  for entry in entries:
    summoner.update_by_summoner_brief(entry)

def update_all() -> int:
  """소환사 랭킹 정보 모두 업데이트

  Raises:
      RequestDataNotExists: 요청 데이터 정보가 존재하지 않을 때

  Returns:
      lengthOfEntries(int)
  """

  entries = []

  # TODO 이후 master 하위 리그까지 전부 업데이트해야 함
  entries.extend(league_exp_v4.get_top_league("challengerleagues"))
  entries.extend(league_exp_v4.get_top_league("grandmasterleagues"))
  entries.extend(league_exp_v4.get_top_league("masterleagues"))

  for entry in entries:
    summoner.update_by_summoner_brief(entry)

  updated_cnt = len(entries)

  if updated_cnt == 0:
    raise RequestDataNotExists("Riot API 응답 데이터가 존재하지 않습니다.")

  return updated_cnt

def get_summoner_by_id(summoner_id, limit=None):
  return league_exp_v4.get_summoner_by_id(summoner_id, limit = limit)


def update_total_summoner():
  queues = ["RANKED_SOLO_5x5", "RANKED_FLEX_SR"]
  
  for queue in queues:
    entries = []

    # TODO 이후 master 하위 리그까지 전부 업데이트해야 함
    entries.extend(league_exp_v4.get_top_league("challengerleagues",queue = queue) )
    entries.extend(league_exp_v4.get_top_league("grandmasterleagues", queue = queue))
    entries.extend(league_exp_v4.get_top_league("masterleagues", queue = queue))
    
    for entry in entries:
      summoner.update_by_summoner_brief(entry)
   
    entries.clear()
    
    tiers = ["DIAMOND", "EMERALD", "PLATINUM", "GOLD","SILVER","BRONZE","IRON"]
    divisions = ["I", "II", "III", "IV"]
    
    for tier in tiers:
      for division in divisions:
          entries.extend(league_exp_v4.get_summoners_under_master(tier, division, queue = queue))
          for entry in entries:
            summoner.update_by_summoner_brief(entry)
          entries.clear()
    

def collect_all_summoners(reverse= False):
  # queues = ["RANKED_SOLO_5x5", "RANKED_FLEX_SR"]
  
  # entries = []

  # for queue in queues:
  # # TODO 이후 master 하위 리그까지 전부 업데이트해야 함
  #   entries.extend(league_exp_v4.get_top_league("challengerleagues",queue = queue) )
  #   entries.extend(league_exp_v4.get_top_league("grandmasterleagues", queue = queue))
  #   entries.extend(league_exp_v4.get_top_league("masterleagues", queue = queue))
  
  # for entry in entries:
  #   summoner.update_by_summoner_brief(entry)
  
  # del entries
  queues = ["RANKED_SOLO_5x5"]
  for queue in queues:
    threads = []
    
    tiers = ["DIAMOND", "EMERALD", "PLATINUM", "GOLD","SILVER","BRONZE","IRON"]
    divisions = ["I", "II", "III", "IV"]
    
    for tier in tiers:
      for division in divisions:
        t = threading.Thread(target = task, args = (tier, division, queue, reverse))
        t.start()
        threads.append(t)

    for thread in threads:
      thread.join()
    