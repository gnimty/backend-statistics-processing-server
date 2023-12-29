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
    420:"solo",
    440:"flex",
    450:"aram"
  }
  
  def __init__(self, matchId, avg_tier, info, timeline, processed_timeline):
    self.collectAt = datetime.datetime.now()
    self.queueId = info["queueId"]
    
    self.metadata = {
      "matchId": matchId,
      "tier": avg_tier,
      "gameStartTimestamp": info["gameStartTimestamp"],
      "gameDuration": info["gameDuration"],
      "gameVersion": info["gameVersion"],
    }
    
    self.teams = info["teams"]
    self.participants = []
    
    totalEffectiveDamageDealtToChampionsDict = {i:0 for i in range(1, 11)}

    for events in [frame["events"] for frame in timeline["info"]["frames"]]:
        target_event = [event for event in events if event["type"]=="CHAMPION_KILL"]
        for t in target_event:
            if "victimDamageDealt" in t:
                for damage in [dmg for dmg in t.get("victimDamageDealt") if dmg["type"]=="OTHER"]:
                    totalEffectiveDamageDealtToChampionsDict[damage["participantId"]]+=(
                    damage["magicDamage"]+
                    damage["physicalDamage"]+
                    damage["trueDamage"])
    
    for participant, processed_timeline in zip(info["participants"], processed_timeline):
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
      for bundle in processed_timeline["itemBuild"].values():
        for b in bundle:
          bundles[str(b)] = None
      
      for item in bundles.keys():  
        if item in temp_items:
          item_builds.append(int(item))
        if item_middle==None and item in middle_items.keys():
          item_middle = int(item)
          
      if len(processed_timeline["itemBuild"])!=0:
        item_starts = processed_timeline["itemBuild"][list(sorted(processed_timeline["itemBuild"]))[0]]
      
      totalDamageDoneToChampions5M = [None for i in range(7)]
      totalDamageTaken5M = [None for i in range(7)]
      minionsKilled5M = [None for i in range(7)]
      totalGold5M = [None for i in range(7)]
      xp5M = [None for i in range(7)]
      
      participantId = participant["participantId"]
      
      for i in range(5, min(36, len(timeline["info"]["frames"])), 5): #5, 10, 15, 20, 25, 30, 35 또는 frame 길이
        appended_idx = (i//5)-1
        
        targetParticipantFrame = timeline["info"]["frames"][i]["participantFrames"][str(participantId)]
        totalDamageDoneToChampions5M[appended_idx] = targetParticipantFrame["damageStats"]["totalDamageDoneToChampions"]
        totalDamageTaken5M[appended_idx] = targetParticipantFrame["damageStats"]["totalDamageTaken"]
        minionsKilled5M[appended_idx] = targetParticipantFrame["minionsKilled"] + targetParticipantFrame["jungleMinionsKilled"]
        totalGold5M[appended_idx] = targetParticipantFrame["totalGold"]
        xp5M[appended_idx] = targetParticipantFrame["xp"]
      
      
      added_participants = {
          "puuid": participant["puuid"],
          "teamId": participant["teamId"],
          "allInPings": participant["allInPings"],
          "assistMePings": participant["assistMePings"],
          "basicPings": participant["basicPings"],
          "dangerPings": participant["dangerPings"],
          "enemyMissingPings": participant["enemyMissingPings"],
          "enemyVisionPings": participant["enemyVisionPings"],
          "getBackPings": participant["getBackPings"],
          "needVisionPings": participant["needVisionPings"],
          "onMyWayPings": participant["onMyWayPings"],
          "pushPings": participant["pushPings"],
          "commandPings": participant["commandPings"],
          "championId": participant["championId"],
          "perks": participant["perks"],
          "teamPosition": participant["teamPosition"],
          "championTransform": participant["championTransform"],
          "champLevel": participant["champLevel"],
          "champExperience": participant["champExperience"],
          "kills": participant["kills"],
          "assists": participant["assists"],
          "deaths": participant["deaths"],
          "firstBloodKill": participant["firstBloodKill"],
          "goldEarned": participant["goldEarned"],
          "goldSpent": participant["goldSpent"],
          "damageDealtToBuildings": participant["damageDealtToBuildings"],
          "firstTowerKill": participant["firstTowerKill"],
          "damageDealtToObjectives": participant["damageDealtToObjectives"],
          "visionScore": participant["visionScore"],
          "detectorWardsPlaced": participant["detectorWardsPlaced"],
          "gameEndedInEarlySurrender": participant["gameEndedInEarlySurrender"],
          "gameEndedInSurrender": participant["gameEndedInSurrender"],
          "win": participant["win"],
          "physicalDamageDealtToChampions": participant["physicalDamageDealtToChampions"],
          "magicDamageDealtToChampions": participant["magicDamageDealtToChampions"],
          "trueDamageDealtToChampions": participant["trueDamageDealtToChampions"],
          "totalDamageTaken": participant["totalDamageTaken"],
          "damageSelfMitigated": participant["damageSelfMitigated"],
          "totalHeal": participant["totalHeal"],
          "totalDamageShieldedOnTeammates": participant["totalDamageShieldedOnTeammates"],
          "totalHealsOnTeammates": participant["totalHealsOnTeammates"],
          "totalMinionsKilled": participant["totalMinionsKilled"],
          "timeCCingOthers": participant["timeCCingOthers"],
          "totalTimeSpentDead": participant["totalTimeSpentDead"],
          "spell1Casts": participant["spell1Casts"],
          "spell2Casts": participant["spell2Casts"],
          "spell3Casts": participant["spell3Casts"],
          "spell4Casts": participant["spell4Casts"],
          "summoner1Id": participant["summoner1Id"],
          "summoner2Id": participant["summoner2Id"],
          "summoner1Casts": participant["summoner1Casts"],
          "summoner2Casts": participant["summoner2Casts"],
          
          ##################### processed_timeline #####################
          "skillTree":processed_timeline["skillBuild"],
          "itemStart": item_starts,
          "itemMiddle": item_middle,
          "itemBuild":item_builds,
          
          ##################### timeline #####################
          "totalDamageDoneToChampions5M" : totalDamageDoneToChampions5M,
          "totalDamageTaken5M" : totalDamageTaken5M,
          "minionsKilled5M" : minionsKilled5M,
          "totalGold5M" : totalGold5M,
          "xp5M" : xp5M,
          
          "totalEffectiveDamageDealtToChampions": totalEffectiveDamageDealtToChampionsDict[participantId]
        }
      if "challenges" in participant:
        # if "controlWardTimeCoverageInRiverOrEnemyHalf" not in participant["challenges"]:
        #   pass
        added_participants["controlWardTimeCoverageInRiverOrEnemyHalf"] = participant["challenges"].get("controlWardTimeCoverageInRiverOrEnemyHalf")
        added_participants["damageTakenOnTeamPercentage"] = participant["challenges"].get("damageTakenOnTeamPercentage")
        added_participants["teamDamagePercentage"] = participant["challenges"].get("teamDamagePercentage")
        added_participants["enemyChampionImmobilizations"] = participant["challenges"].get("enemyChampionImmobilizations")
        added_participants["immobilizeAndKillWithAlly"] = participant["challenges"].get("immobilizeAndKillWithAlly")
        added_participants["initialBuffCount"] = participant["challenges"].get("initialBuffCount")
        added_participants["initialCrabCount"] = participant["challenges"].get("initialCrabCount")
        added_participants["saveAllyFromDeath"] = participant["challenges"].get("saveAllyFromDeath")
        added_participants["soloKills"] = participant["challenges"].get("soloKills")
        added_participants["wardTakedowns"] = participant["challenges"].get("wardTakedowns")
        
      
      self.participants.append(added_participants)
 

    
      
  @classmethod
  def raw_to_parquet_and_upload(cls, scale:int):
    current_date = datetime.datetime.now() - datetime.timedelta(days=1)
    formatted_date = current_date.strftime('%Y-%m-%d')
    
    logger.info("현재 시간 : %s", formatted_date)
    
    try:
      for queueId, queue in cls.QUEUE.items():
        # 1. queueId에 해당하는 raw data 불러오기
        parquets = []
        page = 0
        while True:
          logger.info("queue %s page %d", queue, page)
          result = list(cls.raw_col.find({"collectAt":{"$lte":current_date}, "queueId":queueId}, {"_id":0})
                        .skip(page*scale).limit(scale))
          
          if len(result)==0:
            break
          
          logger.info("founded = %d", len(result))
          
          # 2. parquet 파일로 압축
          # 솔로 랭크 : {YYYY_MM_DD}_RANK_SOLO.parquet
          # 자유 랭크 : {YYYY_MM_DD}_RANK_FLEX.parquet
          # 칼바람 나락 : {YYYY_MM_DD}_ARAM.parquet
          df = pd.DataFrame(result)
          logger.info("dataframe 변환 완료")
          
          del result
          
          parquet_filename = f"{page}.parquet"
          
          table = pa.Table.from_pandas(df)
          # PyArrow Table을 Parquet 파일로 저장
          
          full_path = os.path.join(cls.PATH_DIR, queue, formatted_date, parquet_filename)
          os.makedirs(os.path.dirname(full_path), exist_ok=True)
          
          pq.write_table(table, full_path)
          logger.info("parquet 변환 완료")
          parquets.append(parquet_filename)
          
          page+=1
      
        # 모두 처리 성공 시 gcs에 보낸 후 delete
        upload_many(cls.PATH_DIR, parquets, queue, formatted_date)
      cls.raw_col.delete_many({"collectAt":{"$lte":current_date}})
    except Exception as e:
      print(e)