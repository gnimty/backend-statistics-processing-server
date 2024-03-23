from error.custom_exception import *
from riot_requests.common import delayable_request
from utils.summoner_name import *

import log
logger = log.get_logger()

def get_by_summoner_id(summoner_id):
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

  url = f"https://kr.api.riotgames.com/lol/summoner/v4/summoners/{summoner_id}"

  result = delayable_request(url)

  if "id" not in result:
    return None

  return post_process(result)

def get_by_puuid(puuid, tagNameEntry = None):
  if not puuid:
    raise AttributeError(f"{__name__}의 인자를 잘못 넘겼습니다.")

  url = f"https://kr.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
  result = delayable_request(url)

  if "id" not in result:
    return None

  return post_process(result, tagNameEntry=tagNameEntry)
  
  

def post_process(summoner, tagNameEntry = None):
  del (summoner["accountId"])  # 필요 없는 properties 제거
  
  if tagNameEntry == None:
    tagNameEntry = get_summoner_by_puuid(summoner["puuid"])
  
  summoner["tagLine"] = tagNameEntry.get("tagLine")
  summoner["name"] = tagNameEntry.get("gameName")
  
  summoner["internal_name"] = make_internal_name(summoner["name"])
  summoner["internal_tagname"] = f"{summoner['internal_name']}#{make_tagname(summoner['tagLine'])}"
  return summoner
  

def get_summoner_by_puuid(puuid):
  url = f"https://asia.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}"
  
  result = delayable_request(url)
  
  if "tagLine" not in result:
    return None
  
  return result
  
def get_summoner_by_name_and_tagline(gameName, tagLine):
  url = f"https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}"
  
  result = delayable_request(url)
  
  if "tagLine" not in result:
    return None
  
  return result
  