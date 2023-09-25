from riot_requests import league_exp_v4
import logging
from modules import summoner
from error.custom_exception import RequestDataNotExists

logger = logging.getLogger("app")

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