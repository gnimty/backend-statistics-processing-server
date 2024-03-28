from pymongo import *
from config.appconfig import current_config as config
import logging

logger = logging.getLogger("app")  # 로거


class Mongo:
  mongo_client = None

  @classmethod
  def set_client(cls):
    conn = MongoClient(config.MONGO_URI)
    cls.mongo_client = {
        "riot": conn[config.MONGO_RIOTDATA_DB],
        "stat": conn[config.MONGO_STATISTICS_DB]
    }
    # cls.init_index(cls.mongo_client["riot"])

  @classmethod
  def get_client(cls, db):
    return cls.mongo_client.get(db)

  @classmethod
  def add_index(cls):
    db = cls.mongo_client.get("riot")
      
    db.matches.create_index("matchId", unique=True)
    db.participants.create_index([("matchId", 1), ("participantId", 1)], unique=True)
    db.teams.create_index([("matchId", 1), ("teamId", 1)], unique=True)
    db.summoners.create_index("puuid", unique=True)

  @classmethod
  def init_index(cls, db) -> None:
    summoners_index_by_summoner_id = IndexModel([
        ("id", ASCENDING)
    ], name="summoners_index_by_summoner_id")  
      
    summoners_index_by_mmr = IndexModel([
        ("mmr", DESCENDING)
    ], name="summoners_index_by_mmr")
    
    summoners_index_by_mmr_flex = IndexModel([
        ("mmr_flex", DESCENDING)
    ], name="summoners_index_by_mmr_flex")
    
    summoners_index_by_internal_tagname = IndexModel([
        ("internal_tagname", ASCENDING)
    ], name="summoners_index_by_internal_tagname")

    summoners_index_by_internal_tagname_and_mmr = IndexModel([
        ("internal_tagname", ASCENDING),
        ("mmr", DESCENDING)
    ], name="summoners_index_by_internal_tagname_and_mmr")
    
    summoner_history_index = IndexModel([
        ("puuid", ASCENDING)
    ], name="summoner_history_index")
    
    summoner_history_flex_index = IndexModel([
        ("puuid", ASCENDING)
    ], name="summoner_history_flex_index")

    summoner_matches_index = IndexModel([
        ("puuid", ASCENDING)
    ], name="summoner_matches_index")

    summoner_plays_index = IndexModel([
        ("puuid", ASCENDING),
        ("totalPlays", DESCENDING),
        ("championId", ASCENDING),
    ], name="summoner_plays_index")
    
    summoner_plays_flex_index = IndexModel([
        ("puuid", ASCENDING),
        ("totalPlays", DESCENDING),
        ("championId", ASCENDING),
    ], name="summoner_plays_flex_index")
    
    summoner_plays_total_index = IndexModel([
        ("puuid", ASCENDING),
        ("totalPlays", DESCENDING),
        ("championId", ASCENDING),
    ], name="summoner_plays_total_index")

    matches_index = IndexModel([
        ("matchId", DESCENDING),
        ("gameCreation", DESCENDING),
    ], name="matches_index")

    participants_index = IndexModel([
        ("matchId", DESCENDING),
        ("puuid", ASCENDING),
        ("teamId", ASCENDING),
    ], name="participants_index")
    
    participants_index_by_puuid = IndexModel([
        ("puuid", ASCENDING),
        ("queueId", ASCENDING),
    ], name="participants_index_by_puuid")
    

    teams_index = IndexModel([
        ("matchId", DESCENDING),
        ("teamId", ASCENDING),
    ], name="teams_index")

    # champion_statistics_lane_index = IndexModel([
    #     ("championName", ASCENDING),
    #     ("plays", DESCENDING),
    #     ("win_rate", DESCENDING),
    # ], name="champion_statistics_lane_index")

    # champion_statistics_index = IndexModel([
    #     ("championName", ASCENDING),
    #     ("plays", DESCENDING),
    #     ("win_rate", DESCENDING),
    # ], name="champion_statistics_index")
    
    raw_index = IndexModel([
        ("collectAt", DESCENDING), 
        ("queueId", ASCENDING)
    ], name = "raw_index")
    
    version_index = IndexModel([
        ("order",ASCENDING)
    ], name = "version_index")
    
    db.summoners.create_indexes([summoners_index_by_mmr, summoners_index_by_mmr_flex, summoners_index_by_internal_tagname, summoners_index_by_summoner_id, summoners_index_by_internal_tagname_and_mmr])
    db.summoner_history.create_indexes([summoner_history_index])
    db.summoner_history_flex.create_indexes([summoner_history_flex_index])
    db.summoner_matches.create_indexes([summoner_matches_index])
    db.matches.create_indexes([matches_index])
    db.participants.create_indexes([participants_index, participants_index_by_puuid])
    # db.champion_statistics_lane.create_indexes(
    #     [champion_statistics_lane_index])
    # db.champion_statistics.create_indexes([champion_statistics_index])
    db.teams.create_indexes([teams_index])
    db.summoner_plays.create_indexes([summoner_plays_index])
    db.summoner_plays_flex.create_indexes([summoner_plays_flex_index])
    db.summoner_plays_total.create_indexes([summoner_plays_total_index])
    db.raw.create_indexes([raw_index])
    db.version.create_indexes([version_index])