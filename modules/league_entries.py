from riot_requests import league_exp_v4
from error.custom_exception import DataNotExists, RequestDataNotExists
from modules import summoner
from utils.date_calc import lastModifiedFromNow
import logging

logger = logging.getLogger("app")

col = "league_entries"

def updateAll(db, limit):
  """리그 엔트리 정보 모두 업데이트

  Args:
      db (connection)

  Raises:
      RequestDataNotExists: 요청 데이터 정보가 존재하지 않을 때

  Returns:
      lengthOfEntries(int)
  """
  entries = []
  
  entries.extend(league_exp_v4.get_specific_league("challengerleagues", limit))
  entries.extend(league_exp_v4.get_specific_league("grandmasterleagues", limit))
  entries.extend(league_exp_v4.get_specific_league("masterleagues", limit))
  
  rank = 1 # 순위 정보 추가
  for entry in entries:
    entry["rank"] = rank
    logger.info("%s 정보 업데이트 시작", entry["summonerName"])
    summoner.updateBySummonerBrief(db, entry, limit)
    logger.info("%s 정보 업데이트 끝", entry["summonerName"])
    rank += 1

  logger.info('--------- 마스터 이상 소환사 정보 insert ---------')
  logger.info("총 소환사 수 : %s", len(entries))

  if len(entries) == 0:
    raise RequestDataNotExists("Riot Api 요청 정보가 존재하지 않습니다.")

  db[col].delete_many({}) # db에 넣기 전 league_entires collection 비우기
  db[col].insert_many(entries, ordered=True)

  logger.info("성공적으로 %s명의 엔트리 정보를 업데이트했습니다.", len(entries))
  return len(entries)