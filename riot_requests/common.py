import requests
import time
from flask_api import status
import log
from error.custom_exception import ForbiddenError
from config.appconfig import current_config as config

DEFAULT_LIMIT = config.BATCH_LIMIT

logger = log.get_logger()

headers = {"X-Riot-Token": config.API_KEY}

def delayable_request(url, timeout=10, limit = None) -> any:
  """Riot API Rate Limit에 의해 지연될 수 있는 요청 Handle

  Args:
      url (str): 요청 url
      headers : RIOT API KEY 정보를 담고 있는 헤더
      timeout (int): 지연시킬 시간(seconds)

  Returns:
      request (any)
  """
  if not limit:
    limit = DEFAULT_LIMIT

  logger.info(f'다음으로 request : {url}')
  response = requests.get(url, headers=headers, timeout=timeout)

  # API Key 만료
  if response.status_code == status.HTTP_403_FORBIDDEN:
    raise ForbiddenError("Riot API key가 만료되었습니다.")

  # Riot API Rate Limit 초과 시
  while response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
    retry_after_time = int(response.headers.get("Retry-After"))
    logger.info("API LIMIT이 모두 소모되었습니다. %s초 후 실행", retry_after_time)

    time.sleep(retry_after_time)
    response = requests.get(url, headers=headers, timeout=timeout)

  rate_limit_count = get_rate_limit_cnt(
      response.headers["X-App-Rate-Limit-Count"])
  # logger.info("rate_limit_count = %s", rate_limit_count)

  # Rate Limit이 시스템에서 설정한 임계점 돌파 시 request 속도 slow down
  # if rate_limit_count >= limit:
  #   logger.info("Batch count 소모 시점이 도달하였습니다. 모두 소모되었습니다. 10초 후 실행")
  #   time.sleep(10)

  return response.json()

# X-App-Rate-Limit-Count 파싱


def get_rate_limit_cnt(header):
  # 20:1,100:120
  return int(header.split(",")[1].split(":")[0])


