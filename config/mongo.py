from pymongo import MongoClient,  IndexModel, ASCENDING, DESCENDING
import logging
logger = logging.getLogger("app")  # 로거

def mongoClient(app, db):
  mongoClient = MongoClient(app.config["MONGO_URI"])
  
  if db == app.config.get("MONGO_RIOTDATA_DB"):
    init_index(mongoClient[db])
  
  return mongoClient[db]

def init_index(db):
  
  summoners_index = IndexModel([
    ("mmr", ASCENDING),
    ("puuid", ASCENDING),
    ("internal_name", ASCENDING)
  ], name = "summoners_index")
  
  summoner_matches_index = IndexModel([
    ("puuid", ASCENDING)
  ], name = "summoner_matches_index")
  
  summoner_plays_index = IndexModel([
    ("puuid", ASCENDING),
    ("totalPlays", DESCENDING),
    ("championId", ASCENDING),
  ], name = "summoner_plays_index")
  
  matches_index = IndexModel([
    ("matchId", DESCENDING),
    ("gameCreation", DESCENDING),
  ], name = "matches_index")
  
  participants_index = IndexModel([
    ("matchId", DESCENDING),
    ("puuid", ASCENDING),
    ("teamId", ASCENDING),
  ],name = "participants_index")
  
  teams_index = IndexModel([
    ("matchId", DESCENDING),
    ("teamId", ASCENDING),
  ],name = "teams_index")
  
  # timelines_index = IndexModel([
  #   ("matchId", DESCENDING),
  #   ("puuid", ASCENDING),
  #   ("teamId", ASCENDING),
  #   ("participantId", ASCENDING),
  # ],name = "timelines_index")
  
  champion_statics_lane_index = IndexModel([
    ("championName", ASCENDING),
    ("plays", DESCENDING),
    ("win_rate", DESCENDING),
  ],name = "champion_statics_lane_index")
  
  champion_statics_index = IndexModel([
    ("championName", ASCENDING),
    ("plays", DESCENDING),
    ("win_rate", DESCENDING),
  ],name = "champion_statics_index")
  
  db.summoners.create_indexes([summoners_index])
  db.summoner_matches.create_indexes([summoner_matches_index])
  db.matches.create_indexes([matches_index])
  db.participants.create_indexes([participants_index])
  db.champion_statics_lane.create_indexes([champion_statics_lane_index])
  db.champion_statics.create_indexes([champion_statics_index])
  db.teams.create_indexes([teams_index])
  db.summoner_plays.create_indexes([summoner_plays_index])
  # db.timelines.create_indexes([timelines_index])
