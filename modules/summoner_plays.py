from error.custom_exception import *
from config.mongo import Mongo

col = "summoner_plays"
db = Mongo.get_client("riot")

def update_by_puuid(puuid):
  pipeline = [
    # puuid와 일치하는 participants 정보 가져오기
    {
      '$match':{
        'puuid': puuid
      }
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
  
  # 2. 이 정보를 summoner_plays collection에 update
  for result in aggregate_result:
    db[col].update_one(
      {
        "puuid": puuid,
        "championId":result["championId"]
      },
      {
        "$set": result
      },
      True
    )
  
def find_most_champions(puuid, queueId=420):
  pipeline_champion =  [
    {
      "$match":{
        "puuid":puuid
      }
    },
    {
      "$sort":{
        "totalPlays": -1  
      }
    },
    {
      "$limit":3
    },
    {
      "$project":{
        "_id":0,
        "championId":1   
      }
    }
  ]
  
  aggregated = list(db[col].aggregate(pipeline_champion))
  
  result  = [r["championId"] for r in aggregated]
  
  return result                    