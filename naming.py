"""Extract the branch label from a store name and resolve it to one canonical district.

Two problems this solves, both named in the PRD §4:
  1. OpenRice writes "Tamjai Yunnan Mixian (Cheung Sha Wan Plaza)", Google Maps writes
     "TamJai Yunnan Mixian (Amoy Plaza)" — casing and parenthetical style differ, but the
     branch inside the brackets is the join key.
  2. Threads and XHS rarely name a branch at all. Those records go to an UNLOCATED bucket
     rather than being guessed onto a store.
"""
import re

PAREN = re.compile(r"[\(（]([^\)）]+)[\)）]")


# Names that carry no location information at all: the chain title, in any of the forms
# Google Maps returns it. Left unhandled, fifteen unrelated outlets collapsed into one
# pseudo-branch called "譚仔雲南米線", which then appeared on the map and in the worst-performer
# table as if it were a real place.
GENERIC = {
    "tamjai yunnan mixian", "tam jai yunnan mixian", "tams jai", "tamjai", "tam jai",
    "譚仔雲南米線", "谭仔云南米线", "譚仔", "谭仔", "譚仔三哥", "谭仔三哥",
}


def is_generic(name: str) -> bool:
    """True when a 'store name' identifies the chain rather than a branch."""
    return norm_key(name) in GENERIC or (name or "").strip().lower() in GENERIC


def branch_of(name: str) -> str:
    """Pull the branch label out of a full store name."""
    if not isinstance(name, str):
        return ""
    m = PAREN.search(name)
    raw = m.group(1) if m else ""
    raw = re.sub(r"^\+\s*", "", raw).strip()          # "+WOO" -> "WOO"
    return raw or name.strip()


def norm_key(label: str) -> str:
    """Aggressive normalisation used for fuzzy matching across platforms."""
    s = branch_of(label).lower()
    s = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", s)
    drop = {"plaza", "shopping", "centre", "center", "mall", "commercial", "building",
            "circuit", "court", "house", "tower", "gallery", "podium", "garden", "city",
            "stage", "block", "phase", "shop", "flat", "new", "the"}
    toks = [t for t in s.split() if t not in drop and len(t) > 1]
    return " ".join(sorted(set(toks)))


# District assignment by territory. HK districts grouped the way a manager would read them.
TERRITORY = {
    "Kowloon": ["Mong Kok", "旺角", "Tsuen Wan", "Cheung Sha Wan", "长沙湾", " Sham Shui Po",
                "深水埗", "Kwun Tong", "觀塘", "Wong Tai Sin", "黄大仙", "Jordan", "油麻地",
                "Yau Ma Tei", "Hung Hom", "紅磡", "Ma On Shan", "Wong Kiong", "Hamkok"],
    "New Territories": ["Sha Tin", "沙田", "Tseung Kwan O", "將軍澳", "Amoy", "Po Lam",
                        "Tsing Yi", "青衣", "Tuen Mun", "屯門", "Yuen Long", "元朗",
                        "Tai Po", "大埔", "Fanling", "粉嶺", "Sheung Shui", "上水",
                        "Ma Wan", "Pat Heung", "Tai Wo", "Heng On", "Kam Tin"],
    "HK Island": ["Admiralty", "金鐘", "Central", "中環", "Wan Chai", "灣仔", "Causeway Bay",
                  "銅鑼灣", "Soho", "Sheung Wan", "上環", "Chai Wan", "柴灣", "Cyberport",
                  "Aberdeen", "黃竹坑", "Whampoa", "Pok Fu Lam"],
    "Outlying": ["Po Lun", "Mun Lai", "Lai King", "Tung Chung", "東涌", "Discovery Park",
                 "Olympian", "The LOHAS", "Airport", "國際機場"],
}


def territory_of(district: str) -> str:
    d = (district or "").strip()
    for terr, keys in TERRITORY.items():
        for k in keys:
            if k.lower() in d.lower():
                return terr
    return "Other"


def territory_from_coords(lat: float, lng: float) -> str:
    """Derive territory from coordinates rather than street text.

    Street addresses ("Jaffe Rd", "Po Lun St") carry no district name, so name matching
    left two thirds of Google Maps rows unclassified. The bands below were read off the
    actual store coordinates in this dataset (lat 22.244–22.504, lng 113.942–114.270):

      < 22.27                    HK Island   — Wah Kwai, Cyberport, Chengtu Rd, Aberdeen
      lng < 114.05 & lat > 22.34 New Territories west — Tuen Mun, Yuen Long, Ma Wan
      > 22.36                    New Territories north — Fanling, KOLOUR, OP Mall
      otherwise                  Kowloon
    """
    if lat is None or lng is None:
        return "Unlocated"
    try:
        lat, lng = float(lat), float(lng)
    except (TypeError, ValueError):
        return "Unlocated"
    if lat != lat or lng != lng:                      # NaN guard without importing math
        return "Unlocated"
    if lat < 22.27:
        return "HK Island"
    if lng < 114.05 and lat > 22.34:
        return "New Territories"                      # NW NT / Lantau approaches
    if lat > 22.36:
        return "New Territories"
    return "Kowloon"
