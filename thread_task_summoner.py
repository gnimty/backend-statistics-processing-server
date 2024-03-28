import threading

from modules import league_entries, summoner
from log import get_logger
from error.custom_exception import AlreadyInTask
from error.custom_exception import *

logger = get_logger()

class CustomSummonerTask():
  in_task = False

  exit_event = threading.Event()
    
  # 쓰레드 생성
  threads = []
  
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

  # 1번 쓰레드 작업 : master 이상 소환사 업데이트
  @classmethod
  def thread_1(cls, league, queue, collect):
    try:
      entries = league_entries.get_summoner_entries_over_master(league, queue)
    except CustomUserError:
      logger.error("랭크 정보가 존재하지 않습니다.")
      return 
    for entry in entries:
      if cls.exit_event.is_set():
        logger.info("강제 쓰레드 종료")
        return
      summoner.update_by_summoner_brief(entry, collect=collect)

  # 2번 쓰레드 작업 : master 이하 소환사 업데이트
  @classmethod
  def thread_2(cls, tier, division, queue, collect):
    page = 1
    while True:
      if cls.exit_event.is_set():
        logger.info("강제 쓰레드 종료")
        return
      entries = league_entries.get_summoner_entries_under_master(
        tier, division, queue=queue, page=page)
    
      if len(entries) == 0:
        break

      for entry in entries:
        if cls.exit_event.is_set():
          logger.info("강제 쓰레드 종료")
          return
        summoner.update_by_summoner_brief(entry, collect=collect)

      page += 1
  
  @classmethod
  def start(cls, collect = False):
    if cls.in_task:
      raise AlreadyInTask("이미 소환사 전적 정보를 수집 중입니다.")

    cls.in_task = True

    
    thread1_list=[]
    thread2_list=[]
    
    for queue in ["RANKED_FLEX_SR", "RANKED_SOLO_5x5"]:
      for league in ["challengerleagues", "grandmasterleagues", "masterleagues"]:
        t1 = threading.Thread(target=cls.thread_1,
                            args=(league, queue, collect),
                            name = "thread_1")
        t1.start()
        cls.threads.append(t1)
        thread1_list.append(t1)

      for tier in ["DIAMOND", "EMERALD", "PLATINUM", "GOLD", "SILVER", "BRONZE", "IRON"]:
        for division in ["I", "II", "III", "IV"]:
          t2 = threading.Thread(target=cls.thread_2,
                              args=(tier, division, queue, collect),
                              name = "thread_2")
          t2.start()
          cls.threads.append(t2)
          thread2_list.append(t2)

    # 모든 쓰레드 종료 대기
    for thread in thread1_list:
      thread.join()
    
    for thread in thread2_list:
      thread.join()

    del cls.threads[:]
    
    logger.info("모든 쓰레드들을 종료합니다. ")
    cls.in_task = False
    cls.exit_event.clear()
    
  @classmethod
  def stop(cls):
    if cls.in_task:
      cls.exit_event.set()