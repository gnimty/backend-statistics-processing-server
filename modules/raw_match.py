import datetime
from modules.item import get_item_maps
from collections import OrderedDict
from config.mongo import Mongo
import pandas as pd
from gcs import upload_many
import os
import log
import pyarrow as pa
import pyarrow.parquet as pq

logger = log.get_logger()  # 로거

def game_version_to_api_version(version):
  return version[:-1]+"1"

class RawMatch():
  
  db = Mongo.get_client("riot")
  raw_col = db["raw"]
  
  PATH_DIR = "./raw"
  if not os.path.exists(PATH_DIR):
      os.makedirs(PATH_DIR)
  
  QUEUE = {
    420:"RANK_SOLO",
    440:"RANK_FLEX",
    450:"ARAM"
  }
  
  def __init__(self, matchId, avg_tier, info, timelines):
    self.collectAt = datetime.datetime.now()
    self.queueId = info["queueId"]
    self.metadata = {
      "matchId": matchId,
      "tier": avg_tier
    }
    
    self.info = {
      "gameCreation": info["gameCreation"],
      "gameDuration": info["gameDuration"],
      "gameVersion": info["gameVersion"],
      "teams": info["teams"],
      "participants": []
    }
    
    for participant, timelines in zip(info["participants"], timelines):
      # 1. participant가 올린 아이템 중 최종 아이템을 선별하기
      temp_items = []
      item_builds = []
      item_starts = []
      item_middle = None
      api_version = game_version_to_api_version(info["gameVersion"])    
      # 1. item 정보를 가져오기 -> 매치되는 버전정보 없으면 가장 최신 버전으로 
      all_items = get_item_maps(api_version)
      
      total_items, middle_items = all_items["total"], all_items["middle"]
      
      for field in ["item"+str(i) for i in range(6)]:
        temp = total_items.get(str(participant[field]))
        if temp!=None:
          # 오른 업그레이드 아이템이라면 하위 아이템을, 그게 아니라면 해당 아이템을 추가
          temp_items.append(temp.get("orrnItemFrom") or temp.get("id"))
          
      # 2. itemBuild를 순회하면서 tem_items에 있는 아이템이라면 최종 아이템 빌드 순서로 선정
      bundles = OrderedDict()
      for bundle in timelines["itemBuild"].values():
        for b in bundle:
          bundles[str(b)] = None
      
      for item in bundles.keys():  
        if item in temp_items:
          item_builds.append(int(item))
        if item_middle==None and item in middle_items.keys():
          item_middle = int(item)
          
      if len(timelines["itemBuild"])!=0:
        item_starts = timelines["itemBuild"][list(sorted(timelines["itemBuild"]))[0]]
      
      damageTakenOnTeamPercentage = None
      teamDamagePercentage = None
      
      if "challenges" in participant:
        if "damageTakenOnTeamPercentage" in participant["challenges"]:
          damageTakenOnTeamPercentage = participant["challenges"]["damageTakenOnTeamPercentage"]
        if "teamDamagePercentage" in participant["challenges"]:
          teamDamagePercentage = participant["challenges"]["teamDamagePercentage"]
      
      self.info["participants"].append(
        {
          "assists": participant["assists"],
          "champExperience": participant["champExperience"],
          "championId": participant["championId"],
          "damageDealtToBuildings": participant["damageDealtToBuildings"],
          "damageDealtToObjectives": participant["damageDealtToObjectives"],
          "deaths": participant["deaths"],
          "detectorWardsPlaced": participant["detectorWardsPlaced"],
          "firstBloodKill": participant["firstBloodKill"],
          "firstTowerKill": participant["firstTowerKill"],
          "gameEndedInEarlySurrender": participant["gameEndedInEarlySurrender"],
          "gameEndedInSurrender": participant["gameEndedInSurrender"],
          "goldEarned": participant["goldEarned"],
          "kills": participant["kills"],
          "magicDamageDealtToChampions": participant["magicDamageDealtToChampions"],
          "perks": participant["perks"],
          "physicalDamageDealtToChampions": participant["physicalDamageDealtToChampions"],
          "summoner1Id": participant["summoner1Id"],
          "summoner2Id": participant["summoner2Id"],
          "teamId": participant["teamId"],
          "teamPosition": participant["teamPosition"],
          "timeCCingOthers": participant["timeCCingOthers"],
          "totalDamageTaken": participant["totalDamageTaken"],
          "totalHeal": participant["totalHeal"],
          "totalHealsOnTeammates": participant["totalHealsOnTeammates"],
          "totalMinionsKilled": participant["totalMinionsKilled"],
          "trueDamageDealtToChampions": participant["trueDamageDealtToChampions"],
          "visionScore": participant["visionScore"],
          "wardsKilled": participant["wardsKilled"],
          "wardsPlaced": participant["wardsPlaced"],
          "win": participant["win"],
          "damageTakenOnTeamPercentage": damageTakenOnTeamPercentage,
          "teamDamagePercentage": teamDamagePercentage,
          "skillTree":timelines["skillBuild"],
          "itemStart": item_starts,
          "itemMiddle": item_middle,
          "itemBuild":item_builds
        }
      )
 
  @classmethod
  def raw_to_parquet_and_upload(cls, scale:int):
    current_date = datetime.datetime.now()
    formatted_date = current_date.strftime('%Y%m%d_%H%M%S')
    
    logger.info("현재 시간 : %s", formatted_date)
    parquets = []
    try:
      for queueId, queue in cls.QUEUE.items():
        # 1. queueId에 해당하는 raw data 불러오기
        result = []
        page = 0
        while True:
          logger.info("queue %s page %d", queue, page)
          temp_result = list(cls.raw_col.find({"collectAt":{"$lte":current_date}, "queueId":queueId}, {"_id":0})
                        .skip(page*scale).limit(scale))  
          
          if len(temp_result)==0:
            break
          
          result.extend(temp_result)
          page+=1
        
        logger.info("queueId = %s에 해당하는 결과 : %d개", queueId, len(result))
        # 2. parquet 파일로 압축
        # 솔로 랭크 : {YYYY_MM_DD}_RANK_SOLO.parquet
        # 자유 랭크 : {YYYY_MM_DD}_RANK_FLEX.parquet
        # 칼바람 나락 : {YYYY_MM_DD}_ARAM.parquet
        df = pd.DataFrame(result)
        logger.info("dataframe 변환 완료")
        parquet_filename = f"{formatted_date}_{queue}.parquet"
        
        table = pa.Table.from_pandas(df)
        # PyArrow Table을 Parquet 파일로 저장
        pq.write_table(table, f"{cls.PATH_DIR}/{parquet_filename}")
        logger.info("parquet 변환 완료")
        parquets.append(parquet_filename)
      
      # 모두 처리 성공 시 gcs에 보낸 후 delete
      upload_many(cls.PATH_DIR, parquets)
      cls.raw_col.delete_many({"collectAt":{"$lte":current_date}})
    except Exception as e:
      print(e)