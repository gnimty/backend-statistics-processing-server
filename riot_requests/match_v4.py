from error import custom_exception
from flask_api import status
from riot_requests.common import delayableRequest
import logging

logger = logging.getLogger("app")

def getSummonerMatches(puuid, limit, start=0, count = 30):
  """
  유저의 최근 전적 id 리스트 가져오기
  2000 requests every 10 seconds

  2023.02.06 추가 : killParticipations가 들어오지 않는 데이터 확인, 에러 처리
  2023.02.06 추가 : participants의 assists 필드 추가
  2023.03.06 추가 : participants의 win, gameDuration 필드 추가

  Args:
      puuid (str)
      start (int, optional): 조회 시작 index, Defaults to 0.
      count (int, optional): 조회할 row 수, Defaults to 30.

  Returns:
      [matchIds]: 전적 id 리스트
  """
  
  queue = 420 # rank solo
  type = "ranked"
  
  url = f"https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue={queue}&type={type}&start={start}&count={count}"
  
  result = delayableRequest(url, 30, limit)
  
  return result


def getMatchAndTimeline(matchId, limit):
  """
  특정한 매치 정보 가져오기
  2000 requests every 10 seconds
  2023/01/21 수정 : Return type 수정 (timeline)
  
  Args:
      matchId (str)

  Returns:
      {match,teams,participants, timelines}(Nullable)
  """
  
  url = f"https://asia.api.riotgames.com/lol/match/v5/matches/{matchId}"
  
  # 여기서부터는 필수 정보 제외하고 죄다 갖다 버리기
  result = delayableRequest(url, 20, limit)
  result_timeline = delayableRequest(url+'/timeline', 20, limit)
  
  # 코드 수정 : result와 result_timeline 둘 중 하나도 존재하지 않으면 return none
  if result.get("status") or result_timeline.get("status"):
    raise custom_exception.CustomUserError(
      "매치정보를 가져오는 데 실패했습니다.", 
      "Result of request to Riot not exists", status.HTTP_404_NOT_FOUND )
  
  return {"result":result, "result_timeline":result_timeline}
