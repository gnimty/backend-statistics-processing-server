from riot_requests import summoner_v4
from error.custom_exception import TooManySummonerRequest, DataNotExists
import datetime
import logging
from utils.date_calc import lastModifiedFromNow
from modules import league_entries
from utils.summoner_name import makeInternalName

logger = logging.getLogger("app")
col = "summoners"

def findAllSummonerId(db):
  summonerIds = list(db[col].find({}, {"_id":0, "summonerId":1}))
  
  if len(summonerIds) == 0:
    raise DataNotExists("데이터베이스에서 소환사 정보를 찾을 수 없습니다.")
  return summonerIds

def findBySummonerId(db, summonerId):
  """소환사 ID로 소환사 정보 조회

  Args:
      db (connection)
      summonerId (str)

  Returns:
      summoner
  """
  summoner = db[col].find_one(
    {'id': summonerId},
    {"_id": 0, "accountId": 0})

  if not summoner:
    logger.info("소환사 정보가 존재하지 않습니다.")
    return None

  summoner["updatedAt"] = summoner["updatedAt"]+datetime.timedelta(hours=9)
  return summoner

def updateBySummonerName(db, summonerName, limit):
  """소환사 이름으로 소환사 정보 업데이트
  소환사 이름이 변경되어 API 서버에서 조회가 불가능한 시점에 호출
  소환사 이름이 정확히 일치해야 함
  
  Args:
      db (connection)
      summonerName (str)

  Raises:
      DataNotExists
      TooManySummonerRequest: 업데이트 최종 시각이 현재 시간과 2분 이하로 차이날 때

  Returns:
      summoner: 소환사 정보
  """
  summoner = summoner_v4.requestSummonerByName(summonerName, limit)
  summoner = updateSummoner(db, summoner, summoner)

  # 저장된 정보는 utc time이기 때문에 9시간 더해서 보여주기
  summoner["updatedAt"] = summoner["updatedAt"]+datetime.timedelta(hours=9)
  return summoner


def updateBySummonerBrief(db, summoner_brief, limit):
  summoner = updateSummoner(
      db,
      findBySummonerId(db, summoner_brief["summonerId"]) or
      summoner_v4.requestSummonerById(summoner_brief["summonerId"], limit), summoner_brief)

  logger.info("소환사 %s의 정보를 성공적으로 업데이트했습니다.", summoner["name"])

  summoner["updatedAt"] = summoner["updatedAt"]+datetime.timedelta(hours=9)
  return summoner



def findBySummonerName(db, summonerName):
  """소환사 이름으로 소환사 정보 조회

  Args:
      db (connection)
      summonerName (str)

  Returns:
      summoner
  """
  summoner = db[col].find_one(
    {"name": summonerName}, 
    {"_id": 0, "accountId": 0})

  if not summoner:
    return None

  summoner["updatedAt"] = summoner["updatedAt"]+datetime.timedelta(hours=9)
  return summoner



# startWith 전략으로 찾기
def findByInternalName(db, internal_name):
  summoners = list(db[col].find(
    {"internal_name":{"$regex":f"^{internal_name}"}},
    {"_id": 0, "accountId": 0}).limit(4))
  
  if len(summoners) == 0:
    return []
  
  return summoners
  



def updateSummoner(db, summoner, summoner_brief):
  """summoner 정보 업데이트 및 history 객체 추가

  Args:
      summoner: 현재 정보
      summoner_brief: 조회한 최신 entry 정보
  """
  summoner["updatedAt"] = datetime.datetime.utcnow()
  summoner["queue"] = summoner_brief["queue"]
  summoner["tier"] = summoner_brief["tier"]
  
  del summoner["rank"] # 랭크 정보 삭제
  
  summoner["internal_name"] = makeInternalName(summoner_brief["summonerName"])
  
  # history list 존재하면 갖다 붙이고 없으면 새로 생성
  if not summoner.get("history"):
    summoner["history"] = [{
      "queue":summoner_brief["queue"],
      "tier":summoner_brief["tier"],
      "leaguePoints":summoner_brief["leaguePoints"],
      "last":summoner["updatedAt"],
    }]
  else:
    # history 맨 처음에 insert
    summoner["history"].insert(0, {
      "queue":summoner_brief["queue"],
      "tier":summoner_brief["tier"],
      "leaguePoints":summoner_brief["leaguePoints"],
      "last":summoner["updatedAt"],
    })
    
  db[col].update_one(
      {"puuid": summoner["puuid"]},
      {"$set": summoner},
      True)
  return summoner
  
