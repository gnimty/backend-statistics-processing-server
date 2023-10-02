from error.custom_exception import *
from riot_requests.common import delayable_request
import log
logger = log.get_logger()

def get_by_summoner_id(summoner_id):
  """
  summonerId로 Summoner 정보 가져오기\n
  1600 requests every 1 minutes\n
  
  Args:
      id (str): 소환사 ID
  Returns:
      Summoner: 소환사 정보
  """

  return get_summoner(summoner_id=summoner_id)


def get_by_summoner_name(summonerName, limit):
  """
  summonerName으로 Summoner 정보 가져오기\n
  1600 requests every 1 minutes\n
  
  Args:
      summonerName (str): 소환사이름
  Returns:
      Summoner : 소환사 정보
  """
  result = get_summoner(limit, summoner_name=summonerName)

  return result


def get_by_puuid(puuid, limit):
  if not puuid:
    raise AttributeError(f"{__name__}의 인자를 잘못 넘겼습니다.")

  url = f"https://kr.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
  result = delayable_request(url, limit)

  if "id" not in result:
    return None

  del (result["accountId"])  # 필요 없는 properties 제거

  return result


def get_summoner(summoner_name=None, summoner_id=None):
  """summonerName 또는 summoner Id로 Summoner 정보 가져오기
  둘 중 하나의 인자라도 주어져야 하며 summonerName이 주어지면 summonerId는 무시됨
  
  Args:
      summonerName (str, optional), Defaults to None.
      summonerId (str, optional), Defaults to None.

  Raises:
      AttributeError: summonerName과 summonerId가 둘 다 없을 때
      SummonerNotExists: 주어진 값으로 소환사 정보 조회 시 결과가 존재하지 않을 때

  Returns:
      Summoner: {
        id (str),
        puuid (str): 소환사 PUUID,
        name (str): 소환사명,
        profileIconId (int): 프로필 아이콘 id,
        revisionDate (long): 소환사 정보 최종 수정시각(epoch milliseconds),
        summonerLevel (int): 소환사 레벨,
        updatedAt(date) : 소환사 정보 최종 업데이트시각(우리서버관점)
      } : 소환사 정보
  """

  url = "https://kr.api.riotgames.com/lol/summoner/v4/summoners/"

  if summoner_name:  # 소환사 이름으로 조회
    url = url+f"by-name/{summoner_name}"
  elif summoner_id:  # 소환사 아이디로 조회
    url = url+summoner_id
  else:
    raise AttributeError(f"{__name__}의 인자를 잘못 넘겼습니다.")

  result = delayable_request(url)

  if "id" not in result:
    return None

  del (result["accountId"])  # 필요 없는 properties 제거

  return result
