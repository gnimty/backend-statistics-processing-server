from error.custom_exception import *

col = "summoner_plays"

def updateSummonerPlays(db, puuid):
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
            "totalAssist": 1
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
  
def updateMostChampions(db, puuid):
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
  
  
                    