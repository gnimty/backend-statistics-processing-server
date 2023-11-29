class RawMatch():
  def __init__(self, matchId, avg_tier, info, timelines):
    self.metadata = {
      "matchId": matchId,
      "tier": avg_tier
    }
    
    self.info = {
      "gameCreation": info["gameCreation"],
      "gameDuration": info["gameDuration"],
      "gameVersion": info["gameVersion"],
      "teams": info["teams"],
      "participants": []
    }
    
    for participant, timelines in zip(info["participants"], timelines):
      self.info["participants"].append(
        {
          "assists": participant["assists"],
          "champExperience": participant["champExperience"],
          "championId": participant["championId"],
          "damageDealtToBuildings": participant["damageDealtToBuildings"],
          "damageDealtToObjectives": participant["damageDealtToObjectives"],
          "deaths": participant["deaths"],
          "detectorWardsPlaced": participant["detectorWardsPlaced"],
          "firstBloodKill": participant["firstBloodKill"],
          "firstTowerKill": participant["firstTowerKill"],
          "gameEndedInEarlySurrender": participant["gameEndedInEarlySurrender"],
          "gameEndedInSurrender": participant["gameEndedInSurrender"],
          "goldEarned": participant["goldEarned"],
          "kills": participant["kills"],
          "magicDamageDealtToChampions": participant["magicDamageDealtToChampions"],
          "perks": participant["perks"],
          "physicalDamageDealtToChampions": participant["physicalDamageDealtToChampions"],
          "summoner1Id": participant["summoner1Id"],
          "summoner2Id": participant["summoner2Id"],
          "teamId": participant["teamId"],
          "teamPosition": participant["teamPosition"],
          "timeCCingOthers": participant["timeCCingOthers"],
          "totalDamageTaken": participant["totalDamageTaken"],
          "totalHeal": participant["totalHeal"],
          "totalHealsOnTeammates": participant["totalHealsOnTeammates"],
          "totalMinionsKilled": participant["totalMinionsKilled"],
          "trueDamageDealtToChampions": participant["trueDamageDealtToChampions"],
          "visionScore": participant["visionScore"],
          "wardsKilled": participant["wardsKilled"],
          "wardsPlaced": participant["wardsPlaced"],
          "win": participant["win"],
          # "damageTakenOnTeamPercentage": participant["damageTakenOnTeamPercentage"],
          # "teamDamagePercentage": participant["teamDamagePercentage"],
          "skillTree":timelines["skillBuild"],
          "itemBuild":timelines["itemBuild"]
        }
      )
    
    