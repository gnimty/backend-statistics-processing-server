from apscheduler.schedulers.background import BackgroundScheduler
import logging

logger = logging.getLogger("app")

def start_schedule(batchList):
  schedule = BackgroundScheduler(daemon=True, timezone = 'Asia/Seoul')
  
  for batch in batchList:
    if batch["method"]=="interval":
      schedule.add_job(batch["job"], "interval", **batch["time"], id = batch["job"].__name__, replace_existing=False)
    # 매일 4시에 돌아가게 변경
    elif batch["method"]=="cron":
      schedule.add_job(batch["job"], "cron", **batch["time"], id = batch["job"].__name__, replace_existing=False)
  
  schedule.start()
    