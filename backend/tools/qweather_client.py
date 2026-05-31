"""和风天气 API 客户端（国内城市）。"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import Any

import httpx

FORECAST_DAYS_OPTIONS = (3, 7, 10, 15, 30)


def _get_config() -> tuple[str, str]:
    api_host = os.getenv("QWEATHER_API_HOST", "").strip().rstrip("/")
    api_key = os.getenv("QWEATHER_API_KEY", "").strip()
    if not api_host or not api_key:
        raise RuntimeError(
            "未配置和风天气 API。请在 backend/.env 中设置 "
            "QWEATHER_API_HOST 和 QWEATHER_API_KEY。"
        )
    if not api_host.startswith("http"):
        api_host = f"https://{api_host}"
    return api_host, api_key


def _headers(api_key: str) -> dict[str, str]:
    return {
        "X-QW-Api-Key": api_key,
        "Accept-Encoding": "gzip",
    }


def _request(path: str, params: dict[str, Any]) -> dict[str, Any]:
    api_host, api_key = _get_config()
    url = f"{api_host}{path}"
    with httpx.Client(timeout=15.0, follow_redirects=True) as client:
        response = client.get(url, params=params, headers=_headers(api_key))
        response.raise_for_status()
        data = response.json()

    code = str(data.get("code", ""))
    if code != "200":
        raise RuntimeError(f"和风天气 API 错误（code={code}）")
    return data


def lookup_city(city: str, adm: str | None = None) -> dict[str, Any]:
    params: dict[str, Any] = {
        "location": city,
        "range": "cn",
        "number": 5,
        "lang": "zh",
    }
    if adm:
        params["adm"] = adm

    data = _request("/geo/v2/city/lookup", params)
    locations = data.get("location") or []
    if not locations:
        raise RuntimeError(f"未找到国内城市「{city}」，请检查城市名称是否正确")

    for loc in locations:
        if loc.get("country") == "中国":
            return loc
    return locations[0]


def fetch_now(location_id: str) -> dict[str, Any]:
    return _request("/v7/weather/now", {"location": location_id, "lang": "zh"})


def fetch_daily(location_id: str, days: int) -> dict[str, Any]:
    if days not in FORECAST_DAYS_OPTIONS:
        days = min((d for d in FORECAST_DAYS_OPTIONS if d >= days), default=30)
    return _request(f"/v7/weather/{days}d", {"location": location_id, "lang": "zh"})


def _parse_date(date_str: str | None) -> date | None:
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日"):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    raise RuntimeError(f"无法解析日期「{date_str}」，请使用 YYYY-MM-DD 格式")


def _days_ahead(target: date) -> int:
    return (target - date.today()).days


def _pick_forecast_days(days_ahead: int) -> int:
    if days_ahead <= 0:
        return 7
    needed = days_ahead + 1
    for option in FORECAST_DAYS_OPTIONS:
        if option >= needed:
            return option
    return 30


def _format_location(loc: dict[str, Any]) -> str:
    parts = [loc.get("name", ""), loc.get("adm2", ""), loc.get("adm1", "")]
    seen: set[str] = set()
    unique = []
    for part in parts:
        if part and part not in seen:
            seen.add(part)
            unique.append(part)
    return " · ".join(unique)


def _format_now(now: dict[str, Any]) -> list[str]:
    lines = [
        f"- 观测时间：{now.get('obsTime', '未知')}",
        f"- 天气：{now.get('text', '未知')}",
        f"- 温度：{now.get('temp', '?')}°C（体感 {now.get('feelsLike', '?')}°C）",
        f"- 风向风力：{now.get('windDir', '?')} {now.get('windScale', '?')}级",
        f"- 湿度：{now.get('humidity', '?')}%",
        f"- 能见度：{now.get('vis', '?')} 公里",
    ]
    if now.get("precip") not in (None, "", "0.0", "0"):
        lines.append(f"- 1小时降水：{now.get('precip')} 毫米")
    return lines


def _relative_day_label(fx_date: str) -> str:
    try:
        day = datetime.strptime(fx_date, "%Y-%m-%d").date()
    except ValueError:
        return ""
    diff = (day - date.today()).days
    labels = {0: "今天", 1: "明天", 2: "后天", 3: "大后天"}
    return labels.get(diff, "")


def _format_daily(day: dict[str, Any]) -> list[str]:
    fx_date = day.get("fxDate", "?")
    label = _relative_day_label(fx_date)
    title = f"{fx_date}（{label}）" if label else fx_date
    lines = [
        f"### {title}",
        f"- 天气：白天{day.get('textDay', '?')}，夜间{day.get('textNight', '?')}",
        f"- 温度：{day.get('tempMin', '?')}°C ~ {day.get('tempMax', '?')}°C",
        f"- 风力：{day.get('windDirDay', '?')} {day.get('windScaleDay', '?')}级",
        f"- 湿度：{day.get('humidity', '?')}%",
    ]
    if day.get("precip") not in (None, "", "0.0", "0"):
        lines.append(f"- 降水量：{day.get('precip')} 毫米")
    if day.get("uvIndex"):
        lines.append(f"- 紫外线指数：{day.get('uvIndex')}")
    return lines


def get_weather(city: str, date_str: str | None = None, adm: str | None = None) -> str:
    """查询国内城市天气，返回面向 LLM 的结构化文本。"""
    loc = lookup_city(city, adm)
    location_id = loc["id"]
    place = _format_location(loc)
    target = _parse_date(date_str)

    sections: list[str] = [f"【{place}】"]

    if target is None:
        now_data = fetch_now(location_id)
        sections.append("## 实时天气")
        sections.extend(_format_now(now_data.get("now", {})))

        forecast = fetch_daily(location_id, 7)
        daily_list = forecast.get("daily") or []
        if daily_list:
            sections.append("\n## 未来7天预报")
            for day in daily_list:
                sections.extend(_format_daily(day))
                sections.append("")
        return "\n".join(sections).strip()

    days_ahead = _days_ahead(target)
    if days_ahead > 30:
        return (
            f"【{place}】\n"
            f"目标日期 {target.isoformat()} 超出 30 天预报范围，"
            "暂无法提供该日精确预报。"
        )

    if days_ahead < 0:
        return (
            f"【{place}】\n"
            f"暂不支持查询过去日期（{target.isoformat()}）的历史天气，"
            "以下为当前实时天气：\n"
            + "\n".join(_format_now(fetch_now(location_id).get("now", {})))
        )

    if days_ahead == 0:
        now_data = fetch_now(location_id)
        sections.append(f"## {target.isoformat()}（今天）实时天气")
        sections.extend(_format_now(now_data.get("now", {})))
        return "\n".join(sections)

    forecast_days = _pick_forecast_days(days_ahead)
    forecast = fetch_daily(location_id, forecast_days)
    daily_list = forecast.get("daily") or []
    target_str = target.isoformat()
    matched = next((d for d in daily_list if d.get("fxDate") == target_str), None)

    if matched:
        sections.extend(_format_daily(matched))
    else:
        sections.append(
            f"\n未找到 {target_str} 的预报数据（当前最多 {forecast_days} 天预报）。"
        )

    return "\n".join(sections)
