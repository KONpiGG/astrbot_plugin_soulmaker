import random
from typing import List, Dict, Any, Optional

import httpx

BASE_URL = "https://api.bilibili.com"


async def get_ranking(rid: int = 0, ranking_type: str = "all") -> List[Dict[str, Any]]:
    """Fetch ranking list from bilibili.

    Parameters
    ----------
    rid: int
        Partition ID. 0 means overall.
    ranking_type: str
        Ranking type, e.g. 'all', 'origin', 'rookie'.

    Returns
    -------
    List[Dict[str, Any]]
        List of ranking entries.
    """
    url = f"{BASE_URL}/x/web-interface/ranking/v2"
    params = {"rid": rid, "type": ranking_type}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
    return data.get("data", {}).get("list", [])


async def get_random_video() -> Optional[Dict[str, Any]]:
    """Fetch a random video from popular list."""
    url = f"{BASE_URL}/x/web-interface/popular"
    params = {"ps": 20, "pn": 1}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        items = resp.json().get("data", {}).get("list", [])
    if not items:
        return None
    return random.choice(items)


async def search_videos(keyword: str, page: int = 1) -> List[Dict[str, Any]]:
    """Search videos by keyword."""
    url = f"{BASE_URL}/x/web-interface/search/type"
    params = {"search_type": "video", "keyword": keyword, "page": page}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
    return data.get("data", {}).get("result", [])


async def search_partition(rid: int, page: int = 1, ps: int = 20) -> List[Dict[str, Any]]:
    """Fetch videos from a specific partition."""
    url = f"{BASE_URL}/x/web-interface/newlist"
    params = {"rid": rid, "pn": page, "ps": ps}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
    return data.get("data", {}).get("archives", [])
