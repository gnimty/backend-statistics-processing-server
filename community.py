import requests
import log
from config.appconfig import current_config
import json

logger = log.get_logger()


class SummonerUpdateEntry:
  def __init__(self, summoner):
    self.puuid:str = summoner.get("puuid")
    self.tier:str = summoner.get("queue").upper()
    self.division:int = summoner.get("tier")
    self.lp:int = summoner.get("leaguePoints")
    self.mmr:int = summoner.get("mmr")
    self.mostLanes:list(str) = summoner.get("mostLanes")
    self.mostChampionIds:list(str) = summoner.get("mostChampionIds")
    self.summonerName:str = summoner.get("name")
    self.profileIconId:int = summoner.get("profileIconId")

  def toJSON(self):
	  return json.dumps(self,default=lambda o:o.__dict__,sort_keys=True,indent=4)
 
class CustomSummonerMQ:
  '''
  역할 1. 단일 소환사 정보 갱신 시 puuid를 받아서 mongo에서 조회하여 즉시 PATCH  /community/summoners 호출
  역할 2. 묶음 소환사 정보 갱신 시 puuid를 저장하는 공간에 유저들을 추가 (set으로 관리), 1000명의 임계값에 도달하면 PATCH  /community/summoners 호출 후 set 비우기 
  '''
  
  def __init__(self):
    self.saved = dict()
    self.thresh_hold = 1000
    self.host = current_config.COMMUNITY_HOST
    self.port = current_config.COMMUNITY_PORT
  # def except_wrapper(func):
  #   def wrapper(*args, **kwargs) -> bool:
  #       try:
  #         func(*args, **kwargs)
  #         return True
  #       except Exception:
  #         return False        
  #   return wrapper
  
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
    url = f"https://{self.host}/community/summoners"
    data = {
      "summonerUpdates": [summoner.toJSON() for summoner in summoners]
    }
    
    response = requests.patch(url, json=data)

    if response.status_code != 200:  #실패 시 
      logger.error("Community API 호출에 실패했습니다. status code = %s", response.status_code)
    

csmq = CustomSummonerMQ()