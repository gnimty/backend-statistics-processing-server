import requests
import time
from flask_api import status
import log
from error.custom_exception import ForbiddenError
from config.appconfig import current_config as config
import urllib3
import os

process = os.getenv("PROCESS") or "master"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = log.get_logger()

headers = {"X-Riot-Token": config.API_KEY}

def delayable_request(url, timeout=10) -> any:
  """Riot API Rate Limit에 의해 지연될 수 있는 요청 Handle

  Args:
      url (str): 요청 url
      headers : RIOT API KEY 정보를 담고 있는 헤더
      timeout (int): 지연시킬 시간(seconds)

  Returns:
      request (any)
  """
  
  if process=="master":
    logger.info(f'다음으로 request : {url}')
    
  response = requests.get(url, headers=headers, timeout=timeout, verify=False)

  # API Key 만료
  if response.status_code == status.HTTP_403_FORBIDDEN:
    raise ForbiddenError("Riot API key가 만료되었습니다.")

  # Riot API Rate Limit 초과 시
  while response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
    retry_after_time = int(response.headers.get("Retry-After"))
    logger.info("API LIMIT이 모두 소모되었습니다. %s초 후 실행", retry_after_time)

    time.sleep(retry_after_time)
    response = requests.get(url, headers=headers, timeout=timeout, verify=False)

  # rate_limit_count = get_rate_limit_cnt(
  #     response.headers["X-App-Rate-Limit-Count"])
  # logger.info("rate_limit_count = %s", rate_limit_count)

  return response.json()

# X-App-Rate-Limit-Count 파싱
def get_rate_limit_cnt(header):
  # 20:1,100:120
  return int(header.split(",")[1].split(":")[0])


