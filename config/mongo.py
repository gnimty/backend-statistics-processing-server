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
    cls.init_index(cls.mongo_client["riot"])

  @classmethod
  def get_client(cls, db):
    return cls.mongo_client.get(db)

  @classmethod
  def init_index(cls, db) -> None:
    summoners_index = IndexModel([
        ("mmr", ASCENDING),
        ("puuid", ASCENDING),
        ("internal_name", ASCENDING)
    ], name="summoners_index")

    summoner_history_index = IndexModel([
        ("puuid", ASCENDING)
    ], name="summoner_history_index")

    summoner_matches_index = IndexModel([
        ("puuid", ASCENDING)
    ], name="summoner_matches_index")

    summoner_plays_index = IndexModel([
        ("puuid", ASCENDING),
        ("totalPlays", DESCENDING),
        ("championId", ASCENDING),
    ], name="summoner_plays_index")

    matches_index = IndexModel([
        ("matchId", DESCENDING),
        ("gameCreation", DESCENDING),
    ], name="matches_index")

    participants_index = IndexModel([
        ("matchId", DESCENDING),
        ("puuid", ASCENDING),
        ("teamId", ASCENDING),
    ], name="participants_index")

    teams_index = IndexModel([
        ("matchId", DESCENDING),
        ("teamId", ASCENDING),
    ], name="teams_index")

    champion_statistics_lane_index = IndexModel([
        ("championName", ASCENDING),
        ("plays", DESCENDING),
        ("win_rate", DESCENDING),
    ], name="champion_statistics_lane_index")

    champion_statistics_index = IndexModel([
        ("championName", ASCENDING),
        ("plays", DESCENDING),
        ("win_rate", DESCENDING),
    ], name="champion_statistics_index")

    db.summoners.create_indexes([summoners_index])
    db.summoner_history.create_indexes([summoner_history_index])
    db.summoner_matches.create_indexes([summoner_matches_index])
    db.matches.create_indexes([matches_index])
    db.participants.create_indexes([participants_index])
    db.champion_statistics_lane.create_indexes(
        [champion_statistics_lane_index])
    db.champion_statistics.create_indexes([champion_statistics_index])
    db.teams.create_indexes([teams_index])
    db.summoner_plays.create_indexes([summoner_plays_index])
