import logging
from pymongo import UpdateOne
import traceback
# position, champion_id, champion_name, plays, avg_score(kda), win_rate, ban_rate, cs, gold
# win_rate와 ban_rate 정보를 가져오기 위해서 추가적으로 teams와 matches를 가져와야 함

logger = logging.getLogger("app")

def championAnalysis(db):
  # 1. total_plays 구하기
  total_plays = len(list(db["matches"].find({"gameDuration":{ "$gte" : 300 }})))
  # 2. champion_id, position으로 분류하기
  pipeline_with_lane = [
    {
      "$match":{
        "gameDuration": { "$gte" : 300 }
      }
    },
    {
      "$group" :{
        "_id" : {"championId":"$championId","lane":"$lane", "championName":"$championName"}, 
        "plays":{"$sum":1},
        "kills":{"$sum":"$kills"},
        "deaths":{"$sum":"$deaths"},
        "assists":{"$sum":"$assists"},
        # "kda":{"$avg":{"$toDouble":"$kda"}}, -> 전부 취합 후 나중에 다시 계산
        "gameDuration":{"$avg":{"$toDouble":"$gameDuration"}},
        "cs":{"$avg":{"$toDouble":"$cs"}},
        "total_wins":{
          "$sum":{
            "$cond":[{"$eq":["$win","true"]}, 1, 0]
          }
        },
        "total_defeats":{
          "$sum":{
            "$cond":[{"$eq":["$win","false"]}, 1, 0]
          }
        },
        "goldEarned":{"$avg":"$goldEarned"},
        
      }
    },
    {
      "$project":{
        "plays":1,
        "kills":1,
        "deaths":1,
        "assists":1,
        "total_wins":1,
        "total_defeats":1,
        "gameDuration":{"$round":["$gameDuration", 2]},
        "goldEarned":{"$round":["$goldEarned", 2]},
        "cs":{"$round":["$cs", 2]},
      }
    }
  ]
  
  # # pipeline_total = [
  #   {
  #     "$match":{
  #       "gameDuration": { "$gte" : 300 }
  #     }
  #   },
  #   {
  #     "$group" :{
  #       "_id" : {"championId":"$championId", "championName":"$championName"}, 
  #       "plays":{"$sum":1},
  #       "kills":{"$sum":"$kills"},
  #       "deaths":{"$sum":"$deaths"},
  #       "assists":{"$sum":"$assists"},
  #       "gameDuration":{"$avg":{"$toDouble":"$gameDuration"}},
  #       "cs":{"$avg":{"$toDouble":"$cs"}},
  #       "total_wins":{
  #         "$sum":{
  #           "$cond":[{"$eq":["$win","true"]}, 1, 0]
  #         }
  #       },
  #       "total_defeats":{
  #         "$sum":{
  #           "$cond":[{"$eq":["$win","false"]}, 1, 0]
  #         }
  #       },
  #       "goldEarned":{"$avg":"$goldEarned"},
        
  #     }
  #   },
  #   {
  #     "$project":{
  #       "plays":1,
  #       "kills":1,
  #       "deaths":1,
  #       "assists":1,
  #       "total_wins":1,
  #       "total_defeats":1,
  #       "gameDuration":{"$round":["$gameDuration", 2]},
  #       "goldEarned":{"$round":["$goldEarned", 2]},
  #       "cs":{"$round":["$cs", 2]},
  #     }
  #   }
  # ]
  
  pipeline_total = [
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
  
  results_with_lane = list(db["participants"].aggregate(pipeline_with_lane))
  
  operations = []
  
  # 일부 필드 정보 수정
  for result in results_with_lane:
    result["win_rate"] = round(result["total_wins"]/result["plays"], 2)
    result["kda"] = "perfect" if result["deaths"]==0 else round((result["kills"]+result["assists"])/result["deaths"], 2)
    result["championId"] = result["_id"]["championId"]
    
    result["pick_rate"] = round(result["plays"]/total_plays, 2)
    result["lane"] = result["_id"]["lane"]
    result["championName"] = result["_id"]["championName"]
    
    
    del result["_id"]
    operations.append(UpdateOne(
      {
        "championId":result["championId"], 
        "lane":result["lane"]
      },
      {
        "$set":result
      },
      upsert=True))
    
  result = db["champion_statistics_lane"].bulk_write(operations)
  
  operations.clear() # 재사용
  
  results_total = list(db["participants"].aggregate(pipeline_total))

  # teams를 돌면서 ban_list를 가져오기
  # 예외적인 상황에서 ban_list에 담긴 championId set이 results_total의 championId set보다 클 수 있음 (순서 중요)
  ban_list = {}
  
  teams_info = db["teams"].find({}, {"bans":1})
  
  for team in teams_info: # bans : []
    for ban in team["bans"]:
      
      if ban["championId"]!=-1:
        try:
      
          ban_list[ban["championId"]] = ban_list.get(ban["championId"], 0) + 1
          
        except Exception:
            traceback.print_exc()
  
  for result in results_total:
    try:
      result["bans"] = ban_list.get(result["championId"], 0)
    except Exception:
        traceback.print_exc()
    
    result["banRate"] = round((result["bans"])/total_plays, 2)
    
    operations.append(UpdateOne({"championId":result["championId"]},{"$set":result},upsert=True))

  db["champion_statistics"].bulk_write(operations)
  
  return  
  
