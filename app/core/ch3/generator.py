# generator.py
from typing import Dict, Any, List

from core.common.llm import chat_json
from core.common.storage import save_json
from core.common.result import build_envelope
from core.common.schema import CommonInput
from .prompts import build_sns_prompt, platform_kind


def _clean_caption(x: Any) -> str:
    if not isinstance(x, str):
        return ""
    # LLM이 실수로 코드블록/마크다운 섞는 경우 최소 정리
    return x.replace("```", "").strip()


def _coerce_hashtags(x: Any) -> List[str]:
    if isinstance(x, list):
        return x
    if isinstance(x, str):
        # "#a #b #c" 형태로 올 때 대응
        return [t for t in x.replace("\n", " ").split(" ") if t.strip()]
    return []


def _clean_hashtags(tags: List[Any], kind: str) -> List[str]:
    cleaned: List[str] = []
    seen = set()

    for t in tags:
        if not isinstance(t, str):
            continue
        s = t.strip()
        if not s:
            continue

        # 공백 제거
        s = s.replace(" ", "")

        # '#' 보정
        if not s.startswith("#"):
            s = "#" + s

        if s == "#":
            continue

        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(s)

    # ✅ 프롬프트 규칙과 정합: Naver 5~10 / Instagram 12~15
    limit = 10 if kind == "naver" else 15
    return cleaned[:limit]


def generate_sns_post(
    input_obj: CommonInput,
    content_type: str = "sns",
    mock: bool = False
) -> Dict[str, Any]:
    # content_type은 호출부 호환을 위해 유지 (현재는 sns만 처리)
    prompt = build_sns_prompt(input_obj)

    menu_desc = getattr(input_obj, "menu_desc", "")
    platform = getattr(input_obj, "platform", "")
    kind = platform_kind(platform)

    # mock도 플랫폼별 차이를 확실히 보여주게 구성(권장)
    if kind == "naver":
        mock_caption = (
            f"{input_obj.cafe_name}에서 오늘은 '{input_obj.menu_name}'을(를) 소개해요.\n\n"
            f"{menu_desc}\n\n"
            "오늘의 포인트\n"
            "부담 없이 즐기기 좋은 구성이에요.\n\n"
            "추천 이유\n"
            "바쁜 하루 중간에 잠깐 쉬어가기 딱 좋아요.\n\n"
            "다음 방문 때 메뉴 고르기 쉽게 저장해두면 좋아요 🙂"
        )
        mock_hashtags = [
            "#카페", "#카페추천", "#오늘의메뉴", "#신메뉴", "#디저트",
            "#커피", "#분위기좋은카페"
        ]
    else:
        mock_caption = (
            f"{input_obj.cafe_name} ☕\n"
            f"{input_obj.menu_name}로 오늘 기분 리셋 ✨\n"
            f"{menu_desc}\n"
            "저장해두고 다음에 와서 골라봐요 🙂"
        )
        mock_hashtags = [
            "#카페추천", "#오늘의메뉴", "#신메뉴", "#디저트카페", "#커피",
            "#감성카페", "#카페투어", "#저장각", "#일상", "#맛집", "#디저트"
        ]

    mock_payload = {"caption": mock_caption, "hashtags": mock_hashtags}

    data = chat_json(prompt, mock=mock, mock_payload=mock_payload)

    # LLM 결과 방어 처리
    caption = _clean_caption(data.get("caption")) if isinstance(data, dict) else ""
    hashtags_raw = data.get("hashtags") if isinstance(data, dict) else []
    hashtags_list = _coerce_hashtags(hashtags_raw)
    hashtags = _clean_hashtags(hashtags_list, kind)

    output_obj = {"caption": caption, "hashtags": hashtags}
    envelope = build_envelope("ch3_sns", input_obj=input_obj, output_obj=output_obj, mock=mock)

    saved_path = save_json(envelope, filename_prefix="sns_result")
    return {"caption": caption, "hashtags": hashtags, "saved_path": saved_path}


