from error.custom_exception import *
from riot_requests.common import delayable_request
import log
logger = log.get_logger()

def get_rotation_champions(limit) -> list:
  
  url = f"https://kr.api.riotgames.com/lol/platform/v3/champion-rotations"
  result = delayable_request(url, limit)
  
  if "freeChampionIdsForNewPlayers" not in result:
    raise CustomUserError(
        "로테이션 챔피언 정보를 가져오는 데 실패했습니다.",
        "Failed to get rotation champion list.", status.HTTP_500_INTERNAL_SERVER_ERROR)
  
  return result["freeChampionIdsForNewPlayers"]
  