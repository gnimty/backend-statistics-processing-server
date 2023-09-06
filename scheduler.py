from apscheduler.schedulers.background import BackgroundScheduler
import logging

logger = logging.getLogger("app")

def start_schedule(batchList):
  schedule = BackgroundScheduler(daemon=True, timezone = 'Asia/Seoul')
  
  for batch in batchList:
    func, method, args = batch["job"], batch["method"], batch["time"]
    
    schedule.add_job(
      func, 
      method, 
      **args, 
      id = func.__name__, 
      replace_existing = False # 기존 id (함수명)과 똑같은 스케줄이 시작되면 이를 무시
    )
  
  schedule.start()
    