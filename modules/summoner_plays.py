from error.custom_exception import *
from config.mongo import Mongo
from modules.season import season_name


col = "summoner_plays"
db = Mongo.get_client("riot")

def update_by_puuid(puuid, queueId):
  match_cond = {
    'puuid': puuid,
  }
  if queueId==None:
    target_col = "summoner_plays_total"
    match_cond['queueId'] = {'$in': [420, 440]}
  elif queueId == 420:
    match_cond['queueId'] = queueId
    target_col = col
  elif queueId == 440:
    match_cond['queueId'] = queueId
    target_col = "summoner_plays_flex"
  else:
    return None
  
  pipeline = [
    # puuid와 일치하는 participants 정보 가져오기
    {
      '$match':match_cond
    },
    # championId별로 그룹핑
    {
      '$group':{
        "_id": { "championId": '$championId', "championName": '$championName'},
        "totalPlays": { '$sum': 1 },
        "totalWin": { '$sum': { '$cond': [{ '$eq': ['$win', 'true'] }, 1, 0] } },
        "totalGameDuration": {'$sum': '$gameDuration'},
        "totalCs": {'$sum': '$cs'},
        "totalGold": {'$sum': '$goldEarned'},
        "totalDamage": {'$sum': '$totalDamageDealtToChampions'},
        "maxKill": {'$max': '$kills'},
        "maxDeath": {'$max': '$deaths'},
        "totalKill": { '$sum': '$kills' },
        "totalDeath": { '$sum': '$deaths' },
        "totalAssist": { '$sum': '$assists' },
      }
    },
    # 평균치 계산 및 추가 필드 넣기
    {
      '$addFields':{
        "avgCs": {'$round': [ {'$divide':['$totalCs', '$totalPlays']}, 2]},
        "avgCsPerMinute": {
          '$round': [ 
            {
              '$divide':[
                '$totalCs', {'$divide':['$totalGameDuration', 60]}
              ]
            }, 2]
        },
        "totalDefeat": { '$subtract': ['$totalPlays', '$totalWin']},
        "avgKill": {'$round': [ {'$divide':['$totalKill', '$totalPlays']}, 2]},
        "avgDeath": {'$round': [ {'$divide':['$totalDeath', '$totalPlays']}, 2]},
        "avgAssist": {'$round': [ {'$divide':['$totalAssist', '$totalPlays']}, 2]},
        "avgGold": {'$round': [ {'$divide':['$totalGold', '$totalPlays']}, 2]},
        "avgDamage": {'$round': [ {'$divide':['$totalDamage', '$totalPlays']}, 2]},
        
        "avgKda": {
          '$cond': [
            { '$eq': ['$totalDeath', 0] }, 
            0,
            {'$round': [{'$divide':[{'$add': ['$totalKill','$totalAssist']},'$totalDeath']}, 3]}
          ]
        },
        "winRate": {'$round': [{'$divide':['$totalWin','$totalPlays']}, 2]},
      }
    },
    # 최종 처리
    {
      '$project': { 
            "_id": 0,
            "championId": '$_id.championId',
            "championName": '$_id.championName',
            "avgCs": 1,
            "avgCsPerMinute": 1,
            "totalPlays": 1,
            "avgKill": 1,
            "avgDeath": 1,
            "avgAssist": 1,
            "avgKda": 1,
            "winRate": 1,
            "totalWin": 1,
            "totalDefeat": 1,
            "totalKill": 1,
            "totalDeath": 1,
            "totalAssist": 1,
            "avgGold": 1,
            "avgDamage": 1,
            "maxKill": 1,
            "maxDeath": 1,
      }
    }
  ]
  
  # 1. summoner가 play한 participant 정보를 전부 aggregation load
  aggregate_result = list(db["participants"].aggregate(pipeline))
  
  for result in aggregate_result:
    result["queueId"] = queueId
  
  # 2. 이 정보를 summoner_plays collection에 update
  for result in aggregate_result:
    db[target_col].update_one(
      {
        "puuid": puuid,
        "championId":result["championId"],
        "season": season_name
      },
      {
        "$set": result
      },
      True
    )             