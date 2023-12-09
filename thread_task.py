import threading
import queue
import time
import random

from modules import match, summoner_matches, summoner
from log import get_logger
from error.custom_exception import AlreadyInTask

logger = get_logger()


class CustomMatchThreadTask():
  in_task = False
  
  # 공유 자원
  match_ids_set = set()
  match_ids_queue = queue.Queue()

  # Locks
  set_lock = threading.Lock()
  queue_lock = threading.Lock()
  
  # 쓰레드 생성
  threads = []
  
  @classmethod
  def await_match_ids_len(cls):
    return cls.match_ids_queue.qsize()
  
  @classmethod
  def alive_thread_len(cls):
    return len(cls.threads)
  

  # 1번 쓰레드 작업 : puuid 리스트를 받아 해당 puuid별로 summoner_match 최신 값들을 받아서 queue에 삽입
  @classmethod
  def thread_1(cls, puuids):
    for puuid in puuids:
      match_ids = summoner_matches.update_total_match_ids(puuid, collect=True)
      
      for match_id in match_ids:
        if cls.match_ids_queue.qsize() >= 1000:
          logger.info("저장된 match id가 너무 많습니다. 10초간 유휴")
          time.sleep(10)
        with cls.set_lock:
          if match_id not in cls.match_ids_set:
            cls.match_ids_set.add(match_id)
            with cls.queue_lock:
              cls.match_ids_queue.put(match_id)

  # 2번 쓰레드 작업 : queue에서 match_id를 하나씩 가져와서 전적정보 갱신
  @classmethod
  def thread_2(cls):
    time.sleep(10)  # 1번 쓰레드 작업 시작 후 10초 대기
    
    while True:
      if cls.match_ids_queue.empty():
        time.sleep(5)
        continue
      with cls.queue_lock:
        match_id = cls.match_ids_queue.get()
        
      try:
      # 2번 쓰레드 작업 수행
        match.update_match(match_id)
      except Exception as e:
        logger.info("match id = %s에 해당하는 전적 정보 업데이트를 실패했습니다.")

  @classmethod
  def start(cls):
    if cls.in_task:
      raise AlreadyInTask("이미 소환사 전적 정보를 수집 중입니다.")
    
    cls.in_task = True
    puuids = summoner.find_all_puuids()
  
    # 균일한 티어대 정보 수집을 위하여 shuffle
    random.shuffle(puuids)
    
    # 모든 puuid를 탐색하면서 해당 소환사가 진행한 모든 전적 정보 업데이트
    # 10개 구간으로 나누어 진행
    
    interval = len(puuids)//10
    
    for i in range(3):
      target_puuids = list(puuids[i:i+interval])
      
      t1 = threading.Thread(target = cls.thread_1, args = (target_puuids,))
      
      cls.threads.append(t1)
    
    for i in range(50):
      t2 = threading.Thread(target=cls.thread_2 )
      
      cls.threads.append(t2)

    # 쓰레드 시작
    for thread in cls.threads:
      thread.start()

    # 모든 쓰레드 종료 대기
    for thread in cls.threads:
      thread.join()

  
    cls.in_task = False