"""
地理位置工具 —— 地名提取和坐标匹配。

用法:
    from src.utils.geo import extract_location, geocode
    loc = extract_location("金水区经三路积水严重")
    coords = geocode("郑州市金水区经三路")
"""

import re
from typing import Any


# 郑州市主要行政区列表（按需扩展）
ZHENGZHOU_DISTRICTS = [
    "中原区", "二七区", "管城回族区", "管城区", "金水区", "上街区",
    "惠济区", "中牟县", "巩义市", "荥阳市", "新密市", "新郑市", "登封市",
    "郑东新区", "高新区", "经开区", "航空港区",
]

# 郑州常见地标/地名
ZHENGZHOU_LANDMARKS = [
    "二七广场", "郑州东站", "郑州站", "花园路", "经三路", "农科路",
    "文化路", "东风路", "京广路", "陇海路", "航海路", "农业路",
    "紫荆山", "碧沙岗", "国贸360", "正弘城", "大卫城",
    "龙子湖", "北龙湖", "象湖",
    "地铁1号线", "地铁2号线", "地铁3号线", "地铁4号线", "地铁5号线",
    "地铁14号线",
]


def extract_location(text: str) -> dict[str, Any]:
    """从文本中提取城市/区县/地标信息。"""
    result: dict[str, Any] = {
        "city": "郑州",
        "district": None,
        "address": None,
        "lat": None,
        "lng": None,
    }

    # 匹配行政区
    for district in ZHENGZHOU_DISTRICTS:
        if district in text:
            result["district"] = district
            break

    # 匹配地标
    found_landmarks = []
    for landmark in ZHENGZHOU_LANDMARKS:
        if landmark in text:
            found_landmarks.append(landmark)

    if found_landmarks:
        result["address"] = "、".join(found_landmarks[:3])

    # 尝试提取路名模式（XX路、XX街、XX大道）
    road_pattern = r"([一-龥]{2,6}(?:路|街|大道|巷|交叉口|立交|桥))"
    roads = re.findall(road_pattern, text)
    if roads and not result["address"]:
        result["address"] = "、".join(roads[:3])

    return result


def geocode(address: str) -> tuple[float | None, float | None]:
    """
    将地址转换为经纬度。
    需要设置高德或百度地图 API Key 环境变量。
    如果没有 API Key，返回 (None, None)。
    """
    import os
    import urllib.request
    import json

    api_key = os.environ.get("AMAP_API_KEY", "")
    if not api_key:
        print(f"[geo] 未设置 AMAP_API_KEY，跳过地理编码: {address}")
        return (None, None)

    try:
        url = (
            f"https://restapi.amap.com/v3/geocode/geo?"
            f"key={api_key}&address={address}&city=郑州"
        )
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            if data.get("status") == "1" and data.get("geocodes"):
                loc = data["geocodes"][0]["location"]
                lng, lat = loc.split(",")
                return (float(lat), float(lng))
    except Exception as e:
        print(f"[geo] 地理编码失败: {address} -> {e}")

    return (None, None)


# 预定义坐标字典：常见郑州地名 -> (lat, lng)
ZHENGZHOU_COORDS: dict[str, tuple[float, float]] = {
    "二七广场": (34.753, 113.665),
    "郑州东站": (34.760, 113.773),
    "郑州站": (34.748, 113.658),
    "花园路": (34.786, 113.685),
    "经三路": (34.786, 113.685),
    "紫荆山": (34.763, 113.682),
    "龙子湖": (34.797, 113.805),
    "郑东新区": (34.761, 113.728),
}
