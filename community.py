import requests
import log
from config.appconfig import current_config
import json

logger = log.get_logger()


class SummonerUpdateEntry:
  def __init__(self, summoner):
    self.data = {}
    self.data["internalName"]:str = summoner.get("internal_name")
    self.data["name"]:str = summoner.get("name")
    self.data["internalTagName"]:str = summoner.get("internal_tagname")
    self.data["tagLine"]:str = summoner.get("tagLine")
    self.data["puuid"]:str = summoner.get("puuid")
    self.data["iconId"]:int = summoner.get("profileIconId") or 100
    
    for suffix, my_suffix in [("",""), ("Flex", "_flex")]:
      self.data["tier"+suffix]:str = summoner.get("queue"+my_suffix)  
      if self.data["tier"+suffix]:
        self.data["tier"+suffix] = self.data["tier"+suffix].lower()
      self.data["division"+suffix]:int = summoner.get("tier"+my_suffix)
      self.data["lp"+suffix]:int = summoner.get("leaguePoints"+my_suffix)
      self.data["mmr"+suffix]:int = summoner.get("mmr"+my_suffix)
      self.data["mostLanes"+suffix]:list(str) = summoner.get("mostLanes"+my_suffix) or []
      self.data["mostChampionIds"+suffix]:list(int) = summoner.get("mostChampionIds"+my_suffix) or []
    # print(self.data)
  # def toJSON(self):
	#   return json.dumps(self.data,default=lambda o:o.__dict__,sort_keys=True,indent=4)
 
class CustomSummonerMQ:
  '''
  역할 1. 단일 소환사 정보 갱신 시 puuid를 받아서 mongo에서 조회하여 즉시 PATCH  /community/summoners 호출
  역할 2. 묶음 소환사 정보 갱신 시 puuid를 저장하는 공간에 유저들을 추가 (set으로 관리), 1000명의 임계값에 도달하면 PATCH  /community/summoners 호출 후 set 비우기 
  '''
  
  def __init__(self):
    self.saved = dict()
    self.threshold = 1000
    self.host = current_config.COMMUNITY_HOST
  
  def get_saved_summoner_cnt(self):
    return len(self.saved)
  
  #1. 단일 갱신
  async def renew_one(self, summoner) -> bool:
    
    self.patch_summoners([SummonerUpdateEntry(summoner)])
    logger.info("community에서 업데이트 완료")
    
  
  #2. 묶음 갱신
  async def add_summoner(self, summoner):
    self.saved[summoner.get("puuid")] = SummonerUpdateEntry(summoner)

    if len(self.saved)>=1000:
      self.patch_summoners(list(self.saved.values()))
      self.saved.clear()
      
  
  #3. 공통 api 호출 메소드
  def patch_summoners(self, summoners:list):
    url = f"{self.host}/community/summoners"
    data = {
      "summonerUpdates": [summoner.data for summoner in summoners]
    }
    
    try:
      response = requests.patch(url, json=data, timeout=5)

      if response.status_code != 200:  #실패 시 
        logger.error("Community API 호출에 실패했습니다. status code = %s", response.status_code)
      else:
        logger.info(response.json())
    except Exception as e:
      logger.error("Community API 호출에 실패했습니다.")

csmq = CustomSummonerMQ()