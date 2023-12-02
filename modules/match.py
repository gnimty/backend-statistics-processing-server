from riot_requests import match_v4
from log import get_logger
from utils import date_calc
from modules.summoner import find_history_by_std_date
from modules import summoner_matches, summoner_plays, summoner
from config.mongo import Mongo
import asyncio
from community import csmq
from modules.tier_division_mmr import MMR
from modules.raw_match import RawMatch


# FIXME - pymongo insert operation 동작 시 원본 객체에 영향을 미치는 문제 발견
# https://pymongo.readthedocs.io/en/stable/faq.html#writes-and-ids
# _id까지 보내주는 dump_utils 사용하거나 다시 db에서 조회하는 방법으로 가야 할듯
# 우선은 직접 제거

logger = get_logger()

col = "matches"
db = Mongo.get_client("riot")

def updateMatch(match_id, limit):
  """
  특정 matchId로 match, teams, participants 업데이트 후 결과 반환

  Args:
      db (connection)
      matchId (str)

  Raises:
      Exception: _description_
      Exception: _description_
      
  Returns:
      matchInfo: {
        match,
        teams,
        participants
      }
  """

  match = db[col].find_one(
      {"matchId": match_id},
      {"_id": 0}
  )

  if match: # DB에 match info가 이미 존재하면 업데이트 안함
    return

  data = match_v4.get_by_match_id(match_id, limit)
  
  result = data["result"]
  result_timeline = data["result_timeline"]
  
  # 코드 수정 : result와 result_timeline 둘 중 하나도 존재하지 않으면 return none
  if result.get("status") or result_timeline.get("status"):
    return
  
  info = result["info"]
  info_teams = []
  info_participants = []
  
  summoner_tiers = []
  
  # timeline에서 얻은 정보
  timelines = {}
  match = {
    "matchId" : match_id,
    "gameStartAt": date_calc.timeStampToDateTime(str(info["gameStartTimestamp"])),
    "gameDuration": int(info["gameDuration"]),
    "queueId": int(info["queueId"]),
    "gameEndAt": # gameEndTimestamp가 필드정보에서 누락되는 현상 확인, gameStartAt + gameDuration 값으로 환산
      date_calc.timeStampToDateTime(str(info["gameEndTimestamp"])) 
      if "gameEndTimestamp" in info 
      else date_calc.timeStampToDateTime(str(info["gameStartTimestamp"] + 1000*info["gameDuration"])) ,
    "version": short_game_version(info["gameVersion"]),
    "fullVersion": info["gameVersion"],
    "earlyEnded": False
  }
  
  if match["queueId"]==440:
    mode = "RANK_FLEX_SR"
  else: 
    mode = "RANK_SOLO_5x5"
  
  for team in info["teams"]:
    info_teams.append({
      "matchId" : match_id,
      "teamId":team["teamId"],
      "win":team["win"],
      "bans":team["bans"],
      "baron":team["objectives"]["baron"]["kills"],
      "dragon":team["objectives"]["dragon"]["kills"],
      "tower":team["objectives"]["tower"]["kills"],
      "riftHerald":team["objectives"]["riftHerald"]["kills"],
      "totalKills":team["objectives"]["champion"]["kills"],
    })
  
  if info_teams[0]["win"]=="true":
    win_team_id=info_teams[0]["teamId"]
  else:
    win_team_id=info_teams[1]["teamId"]
  
  for participant in info["participants"]:
    lane = participant["teamPosition"]
    
    # if lane not in ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]:
    #   logger.warning(f"잘못된 라인 정보가 들어왔습니다. {lane}")
    # elif lane == "UTILITY":
    #     lane=="SUPPORT"
    # elif lane == "BOTTOM":
    #     lane=="ADC"
    
    challenges=participant["challenges"]
    
    # 킬관여율 필드 : info["teams"]에서 teamId가 일치하는거 찾고 거기서 totalKill 가져오기
    # challenges에 killParticipations 필드가 존재하지 않는다면 직접 계산 후 소수 2번째 자리까지 반올림
    teamId = participant["teamId"]
    total_team_kills = int(list(filter(lambda x: x["teamId"]==teamId, info_teams))[0]["totalKills"])
    killParticipation = challenges.get("killParticipation")
    if not killParticipation:
      if total_team_kills==0:
        killParticipation = 0
      else:
        killParticipation = round(((participant["kills"]+participant["assists"])/ total_team_kills), 2)
    
    # 승리 여부
    if win_team_id == participant["teamId"]:
      win="true"
    else:
      win="false"
    
    history = find_history_by_std_date(participant["puuid"], match["gameStartAt"], mode)
      
    if history["queue"]!=None:
      summoner_tiers.append(MMR.rank_to_mmr(history["queue"], history["tier"], history["leaguePoints"]))
      
    # 게임 조기 종료
    if participant["gameEndedInEarlySurrender"]:
      match["earlyEnded"] = True
    
    
    info_participants.append({
      "matchId" : match_id,
      "teamId":participant["teamId"],
      "puuid":participant["puuid"],
      "participantId":participant["participantId"],
      "queueId":int(info["queueId"]),
      "totalDamageTaken":participant["totalDamageTaken"],
      "totalDamageDealtToChampions":participant["totalDamageDealtToChampions"],
      "wardsPlaced":participant["wardsPlaced"],
      "wardsKilled":participant["wardsKilled"],
      "visionWardsBoughtInGame":participant["visionWardsBoughtInGame"],
      # "summonerLevel":participant["summonerLevel"],
      "queue":history["queue"],
      "tier":history["tier"],
      "leaguePoints":history["leaguePoints"],
      "championLevel":participant["champLevel"],
      "championId":participant["championId"],
      "championName":participant["championName"],
      "kills":participant["kills"],
      "deaths":participant["deaths"],
      "assists": participant["assists"],
      "lane":lane,
      "cs":int(participant["totalMinionsKilled"])+int(participant["neutralMinionsKilled"]),
      "killParticipation":killParticipation,
      "goldEarned":participant["goldEarned"],
      "kda":str(round(float(challenges["kda"]),2)),
      "pentaKills":participant["pentaKills"],
      "quadraKills":participant["quadraKills"],
      "tripleKills":participant["tripleKills"],
      "doubleKills":participant["doubleKills"],
      "perks":participant["perks"],
      "item0":participant["item0"],
      "item1":participant["item1"],
      "item2":participant["item2"],
      "item3":participant["item3"],
      "item4":participant["item4"],
      "item5":participant["item5"],
      "item6":participant["item6"],
      "spellDId":participant["summoner1Id"],
      "spellFId":participant["summoner2Id"],
      "win":win,
      "gameDuration": info["gameDuration"],
      "ealryEnded":participant["gameEndedInEarlySurrender"]
    })
  
  for initial_timeline_info in result_timeline["info"]["participants"]:
    timelines[initial_timeline_info["participantId"]]={
      "matchId":match_id,
      "puuid": initial_timeline_info["puuid"],
      "participantId":initial_timeline_info["participantId"],
      "itemBuild":{},
      "skillBuild":[]
    }
    
  frameCount=0 # frameInteval로 나눈 event frame
  
  for timeline_info in result_timeline["info"]["frames"]:
    for event in timeline_info["events"]:
      
      # 아이템 구매 내역, 스킬 레벨업 내역이 담긴 event만 추출
      if "type" in event and event["type"] in ["ITEM_PURCHASED","SKILL_LEVEL_UP"]:
        event_type = event["type"]
        participantId = event["participantId"]
        target_timeline = timelines[participantId]
        
        #1. 아이템 빌드 stack
        if event_type=="ITEM_PURCHASED":
          itemId = event["itemId"]
          
          # 이미 interval이 존재하는 경우
          if str(frameCount) in target_timeline["itemBuild"]:
            target_timeline["itemBuild"][str(frameCount)].append(itemId)
          # interval 신규 생성
          else:
            target_timeline["itemBuild"][str(frameCount)] = [itemId]
        
        #2. 스킬 빌드 stack
        elif event_type=="SKILL_LEVEL_UP":
          target_timeline["skillBuild"].append(event["skillSlot"])
    frameCount+=1
  info_timelines = list(timelines.values())
  info_participants.sort(key=lambda x:x["participantId"])
  info_timelines.sort(key=lambda x:x["participantId"])
  
  for i in range(10):
    info_participants[i].update(info_timelines[i])
  
  if len(summoner_tiers)==0:
    avg_tier = None
  else:
    avg_tier = MMR.mmr_to_tier(sum(summoner_tiers)/len(summoner_tiers))
  
  raw = RawMatch(match_id, avg_tier, info, info_timelines)
  
  db["matches"].insert_one(match)
  db["teams"].insert_many(info_teams)
  db["participants"].insert_many(info_participants)
  db["raw"].insert_one(raw.__dict__)

def update_matches_by_puuid(puuid, limit=None):
  match_ids = summoner_matches.update_total_match_ids(puuid, limit)
  
  for match_id in match_ids:
    # try:
    updateMatch(match_id, limit)
    # except Exception:
    #   logger.error("matchId = %s에 해당하는 전적 정보를 불러오는 데 실패했습니다.", match_id)
  
  # 모든 매치정보 업데이트 후 summoner_matches, summoner_plays (전체 플레이 요약 정보), summoner (최근 플레이 요약 정보) 업데이트
  summoner_plays.update_by_puuid(puuid)
  summoner.update_summary(puuid)
  
  target_summoner = summoner.find_by_puuid(puuid)
  asyncio.run(csmq.add_summoner(target_summoner))
  
def short_game_version(version):
  split = version.split(".")[:3]
  if len(split)>=3:
    split[2] = split[2][0]
  
  return ".".join(split)