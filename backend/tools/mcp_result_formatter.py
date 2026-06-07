import json
from typing import Any


_ERROR_MESSAGE_ZH = {
    "No available room types for this hotel": "该酒店在所选日期暂无可用房型或已满房",
}

def normalize_mcp_args(tool_name: str, kwargs: dict[str, Any]) -> dict[str, Any]:
    if tool_name == "searchHotels":
        return _normalize_search_hotels_args(kwargs)
    if tool_name == "getHotelDetail":
        return _normalize_hotel_detail_args(kwargs)
    return kwargs


def _normalize_hotel_detail_args(kwargs: dict[str, Any]) -> dict[str, Any]:
    args = dict(kwargs)
    check_in = args.pop("checkInDate", None) or args.pop("check_in_date", None)
    check_out = args.pop("checkOutDate", None) or args.pop("check_out_date", None)
    stay = args.pop("stayNights", None) or args.pop("nights", None)

    date_param = dict(args.get("dateParam") or {})
    if check_in:
        date_param["checkInDate"] = check_in
    if check_out:
        date_param["checkOutDate"] = check_out
    if date_param:
        args["dateParam"] = date_param

    if stay is not None and check_in and "dateParam" in args and not check_out:
        from datetime import date, timedelta

        try:
            start = date.fromisoformat(check_in)
            end = start + timedelta(days=int(stay))
            args["dateParam"]["checkOutDate"] = end.isoformat()
        except ValueError:
            pass

    args.setdefault(
        "localeParam",
        args.get("localeParam") or {"countryCode": "CN", "currency": "CNY"},
    )
    return args


def _normalize_search_hotels_args(kwargs: dict[str, Any]) -> dict[str, Any]:
    args = dict(kwargs)

    check_in = args.pop("checkInDate", None) or args.pop("check_in_date", None)
    stay = args.pop("stayNights", None) or args.pop("nights", None)
    adults = args.pop("adultCount", None) or args.pop("adults", None)
    place = (
        args.get("place")
        or args.pop("city", None)
        or args.pop("cityName", None)
        or args.pop("keyword", None)
        or args.pop("location", None)
    )
    if place and not args.get("place"):
        args["place"] = place

    stars = args.pop("starRating", None) or args.pop("starRatings", None)
    if stars is not None and "filterOptions" not in args:
        if isinstance(stars, (int, float)):
            star_value = float(stars)
            args["filterOptions"] = {"starRatings": [star_value, 5.0]}
        elif isinstance(stars, list):
            args["filterOptions"] = {"starRatings": stars}

    check_in_param = dict(args.get("checkInParam") or {})
    if check_in:
        check_in_param["checkInDate"] = check_in
    if stay is not None:
        check_in_param["stayNights"] = int(stay)
    if adults is not None:
        check_in_param["adultCount"] = int(adults)
    if check_in_param:
        args["checkInParam"] = check_in_param

    args.setdefault("countryCode", "CN")
    return args


def format_mcp_tool_result(tool_name: str, text: str, *, max_chars: int = 6000) -> str:
    if tool_name == "searchHotels":
        return _format_search_hotels_result(text)
    if tool_name == "getHotelDetail":
        return _format_hotel_detail_result(text)
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n（结果已截断，请根据以上内容回答）"
    return text


def _format_search_hotels_result(text: str, max_hotels: int = 8) -> str:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return text[:4000] if len(text) > 4000 else text

    hotels = data.get("hotelInformationList") or []
    if not hotels:
        message = data.get("message") or "未找到酒店"
        return f"{message}\n\n（请根据以上结果回答用户，不要再次调用 searchHotels）"

    lines = [
        f"酒店搜索成功，共 {len(hotels)} 家（展示前 {min(len(hotels), max_hotels)} 家）：",
        "",
    ]
    for index, hotel in enumerate(hotels[:max_hotels], start=1):
        price = hotel.get("price") or {}
        price_text = price.get("message") or str(price.get("amount") or "价格未知")
        lines.append(
            f"{index}. **{hotel.get('name', '未知酒店')}**"
            f" | 星级 {hotel.get('starRating', '-')}"
            f" | {hotel.get('address', '')}"
        )
        lines.append(f"   - 价格：{price_text}")
        if hotel.get("hotelId") is not None:
            lines.append(f"   - hotelId：{hotel['hotelId']}")
        if hotel.get("bookingUrl"):
            lines.append(f"   - 预订：{hotel['bookingUrl']}")
        lines.append("")

    if len(hotels) > max_hotels:
        lines.append(f"（另有 {len(hotels) - max_hotels} 家未列出）")
    lines.append("（请根据以上结果直接用自然语言回答用户，不要再次调用 searchHotels）")
    return "\n".join(lines)


def _translate_error_message(message: str) -> str:
    if not message:
        return "查询失败，请稍后重试"
    return _ERROR_MESSAGE_ZH.get(message, message)


def _format_hotel_detail_result(text: str, max_rooms: int = 8) -> str:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return text[:4000] if len(text) > 4000 else text

    if not isinstance(data, dict):
        return str(data)[:4000]

    if data.get("success") is False:
        error = _translate_error_message(data.get("errorMessage") or "")
        hotel_name = data.get("name") or "该酒店"
        check_in = data.get("checkIn") or ""
        check_out = data.get("checkOut") or ""
        date_hint = f"{check_in} → {check_out}" if check_in and check_out else "所选日期"
        lines = [
            f"**{hotel_name}** 详情查询未成功",
            f"- 原因：{error}",
            f"- 查询日期：{date_hint}",
            "",
            "（请用自然语言告知用户暂无房或无法查询，可建议更换入住日期、尝试简化酒店名称、"
            "或先用 searchHotels 获取 hotelId 后再调用 getHotelDetail）",
        ]
        return "\n".join(lines)

    lines = []
    name = data.get("name") or data.get("hotelName")
    if name:
        lines.append(f"**{name}**")
    if data.get("checkIn") and data.get("checkOut"):
        lines.append(f"- 入住：{data['checkIn']} → 离店：{data['checkOut']}")
    if data.get("hotelId") is not None:
        lines.append(f"- hotelId：{data['hotelId']}")
    if data.get("bookingUrl"):
        lines.append(f"- 预订链接：{data['bookingUrl']}")

    rooms = data.get("roomRatePlans") or data.get("roomList") or data.get("rooms") or []
    if isinstance(rooms, list) and rooms:
        lines.append("")
        lines.append(f"可订房型（展示前 {min(len(rooms), max_rooms)} 个）：")
        for room in rooms[:max_rooms]:
            if not isinstance(room, dict):
                continue
            room_name = (
                room.get("roomNameCn")
                or room.get("ratePlanName")
                or room.get("roomName")
                or room.get("name")
                or "房型"
            )
            currency = room.get("currency") or "CNY"
            total_price = room.get("totalPrice")
            price_text = (
                f"{currency} {total_price}"
                if total_price is not None
                else "价格未知"
            )
            bed = room.get("bedTypeDescription") or ""
            extra = f"（{bed}）" if bed else ""
            lines.append(f"- {room_name}{extra}：{price_text}")

    if not lines:
        compact = json.dumps(data, ensure_ascii=False)
        return compact[:4000] if len(compact) > 4000 else compact

    lines.append("")
    lines.append("（请根据以上详情直接用自然语言回答用户）")
    return "\n".join(lines)
