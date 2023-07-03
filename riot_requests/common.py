import requests, time
from flask_api import status
import logging, os
from error.custom_exception import ForbiddenError
# from config.redis import RedisClient

logger = logging.getLogger("app")

headers={"X-Riot-Token":os.getenv("RIOT_API_KEY")}

# TODO - 최종 시간 제한도 걸어놔야 api 서버 상황에 대처할 수 있을 듯
def delayableRequest(url, timeout, limit):
  """Riot API Rate Limit에 의해 지연될 수 있는 요청 Handle

  Args:
      url (str): 요청 url
      headers : RIOT API KEY 정보를 담고 있는 헤더
      timeout (int): 지연시킬 시간(seconds)

  Returns:
      request (any)
  """
  
  logger.info(f'다음으로 request : {url}')
  response = requests.get(url, headers=headers, timeout=timeout)
  
  if response.status_code == status.HTTP_403_FORBIDDEN:
    raise ForbiddenError("Riot API key가 만료되었습니다.")
  
  while response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
    retry_after_time = int(response.headers.get("Retry-After"))
    logger.info("API LIMIT이 모두 소모되었습니다. %s초 후 실행", retry_after_time)
    time.sleep(retry_after_time)
    response = requests.get(url, headers=headers, timeout=timeout)
    
  rate_limit_count = getRateLimitCount(response.headers["X-App-Rate-Limit-Count"])
  logger.info("rate_limit_count = %s", rate_limit_count)
  if rate_limit_count >= limit:
    logger.info("Batch count 소모 시점이 도달하였습니다. 모두 소모되었습니다. 10초 후 실행", )
    time.sleep(10)
  
  return response.json()

# X-App-Rate-Limit-Count 파싱
def getRateLimitCount(header):
  # 20:1,100:120
  return int(header.split(",")[1].split(":")[0])