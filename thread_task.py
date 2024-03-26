import threading
import queue
import time
import random

from modules import match, summoner_matches, summoner, raw_match
from log import get_logger
from error.custom_exception import AlreadyInTask
from config.redis import Redis

logger = get_logger()

class CustomMatchThreadTask():
  in_task = False
  
  # 공유 자원
  match_ids_queue = queue.Queue()

  # set_lock = raw_match.RawMatch.set_lock
  # match_id_set = raw_match.RawMatch.match_ids_set
  exit_event = threading.Event()
    
  # 쓰레드 생성
  threads = []
  # 해당 flag가 True면 thread1이 더 이상 동작하지 않음
  thread1_flag  = False
  
  @classmethod
  def await_match_ids_len(cls):
    return cls.match_ids_queue.qsize()
  
  @classmethod
  def alive_thread_len(cls):
    alive = [0, 0]
    
    for thread in cls.threads:
      if thread.is_alive():
        if thread.name == "thread_1":
          alive[0]+=1
        else:
          alive[1]+=1
          
    return alive

  # 1번 쓰레드 작업 : puuid 리스트를 받아 해당 puuid별로 summoner_match 최신 값들을 받아서 queue에 삽입
  @classmethod
  def thread_1(cls, puuids):
    for puuid in puuids:
      try:
        match_ids = summoner_matches.update_total_match_ids(puuid, collect=True)
      except Exception as e:
        logger.info("puuid = %s match id 수집 실패", puuid)
        continue
      for match_id in match_ids:
        if cls.exit_event.is_set():
          logger.info("강제 쓰레드 종료")
          return
        
        if cls.match_ids_queue.qsize() >= 1000:
          logger.info("저장된 match id가 너무 많습니다. 10초간 유휴")
          time.sleep(5)
        
        if not Redis.check_processed(match_id):
          Redis.add_to_set(match_id)
          cls.match_ids_queue.put(match_id)
    logger.info("thread1 종료")

  # 2번 쓰레드 작업 : queue에서 match_id를 하나씩 가져와서 전적정보 갱신
  @classmethod
  def thread_2(cls):
    while True:
        try:
            if cls.match_ids_queue.empty() and cls.thread1_flag:
              return
            match_id = cls.match_ids_queue.get(block=False)
            # 2번 쓰레드 작업 수행
            match.update_match(match_id, collect=True)
        except queue.Empty as e:
            # logger.info("match id queue가 비어 있으므로 5초 동안 유휴합니다.")
            time.sleep(10)
            continue
        except Exception as e:
            logger.info("match id = %s에 해당하는 전적 정보 업데이트를 실패했습니다.", match_id)

  @classmethod
  def start(cls, skip = False):
    if cls.in_task:
      raise AlreadyInTask("이미 소환사 전적 정보를 수집 중입니다.")
    
    cls.in_task = True
    # puuids = summoner.find_all_puuids()
    puuids = summoner.find_all_puuids_with_cond({"mmr":{"$gte":1600}})
    if skip:
        puuids = puuids[len(puuids)//2:]
    else:
        puuids = puuids[:len(puuids)//2]
    
    # 균일한 티어대 정보 수집을 위하여 shuffle
    random.shuffle(puuids)
    
    # 모든 puuid를 탐색하면서 해당 소환사가 진행한 모든 전적 정보 업데이트
    # 10개 구간으로 나누어 진행
    
    interval = len(puuids)//5
    
    thread1_list=[]
    thread2_list=[]
    for i in range(5):
      if i==4:
        target_puuids = list(puuids[i*interval:])
      else:
        target_puuids = list(puuids[i*interval:(i+1)*interval])
      t1 = threading.Thread(target = cls.thread_1, args = (target_puuids,), name = "thread_1")
      
      cls.threads.append(t1)
      thread1_list.append(t1)
      t1.start()
    
    time.sleep(2)
    
    for i in range(10):
      t2 = threading.Thread(target=cls.thread_2 , name = "thread_2")
      
      cls.threads.append(t2)
      thread2_list.append(t2)
      t2.start()

    # 모든 쓰레드 종료 대기
    for thread in thread1_list:
      thread.join()
    
    cls.thread1_flag = True
    
    for thread in thread2_list:
      thread.join()

    del cls.threads[:]
    logger.info("모든 쓰레드들을 종료합니다. ")
    cls.in_task = False
    cls.thread1_flag = False
    cls.exit_event.clear()
  
  @classmethod
  def stop(cls):
    cls.exit_event.set()
    cls.thread1_flag = True