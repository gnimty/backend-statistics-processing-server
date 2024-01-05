from enum import Enum

class MMR(Enum):
    #  추후 개선
    challenger = 2800
    grandmaster = 2800
    master = 2800
    diamond = 2400
    emerald = 2000
    platinum = 1600
    gold = 1200
    silver = 800
    bronze = 400
    iron = 0
    
    def rank_to_mmr(queue, tier, lp):
        if MMR[queue].value==2800:
            return MMR[queue].value + lp
        else:
            return MMR[queue].value + lp + 100 * (4-tier)
    
    def mmr_to_tier(mmr: int): # 우선 2800 이상은 MASTER 이상으로 기재, 추후 그마/챌컷 db에 적재
        if mmr<0: 
            return None
        for std_mmr in MMR:
            if mmr >= std_mmr.value:
                if std_mmr.value>=2800:
                    return "master"
                return std_mmr.name
