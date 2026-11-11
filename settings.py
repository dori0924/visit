"""관리자가 수정하는 앱 설정(안내문, 서약서 본문, 안전교육 URL, 로고)의 읽기·저장.

저장소에 값이 없으면 content/ 폴더의 기본 문구를 쓴다.
저장소를 읽지 못하면(네트워크 오류 등) 방문자 화면이 멈추지 않도록 기본값으로 대신한다.
"""

from __future__ import annotations

import base64
import io
import logging
import re
from pathlib import Path

from storage import StorageError, get_storage, now_kst

log = logging.getLogger(__name__)

CONTENT_DIR = Path(__file__).parent / "content"

# 설정 키 → 기본값 파일 (파일이 없는 키는 기본값이 빈 문자열)
DEFAULT_FILES = {
    "notice_ko": "notice_ko.md",
    "notice_en": "notice_en.md",
    "pledge_ko": "pledge_ko.md",
    "pledge_en": "pledge_en.md",
}
TEXT_KEYS = list(DEFAULT_FILES)
URL_KEYS = ["safety_url_ko", "safety_url_en"]
# 안전교육 기본 주소. 관리자 모드에서 바꾸면 그 값이 우선하고, 되돌리면 이 주소로 돌아온다.
# 영문 주소가 비어 있으면 한글 주소를 쓴다(safety_url 참고).
DEFAULT_VALUES = {
    "safety_url_ko": "https://visit.hyundai-steel.com/reserve/index.do",
}
MAX_TEXT_LEN = 20_000

URL_RE = re.compile(r"^https?://[^\s<>\"']+$", re.IGNORECASE)

# 로고: Google Sheets 셀 하나는 5만 자까지라 base64를 나눠 저장한다.
LOGO_MAX_UPLOAD = 2 * 1024 * 1024
LOGO_MAX_SVG = 200 * 1024
LOGO_MAX_WIDTH = 400
LOGO_CHUNK = 45_000


class LogoError(ValueError):
    """로고 파일이 올바르지 않음. args[0]은 i18n 키."""


# ── 텍스트·URL 설정 ─────────────────────────────────────────
def default(key: str) -> str:
    """설정 키의 기본값을 돌려준다."""
    filename = DEFAULT_FILES.get(key)
    if not filename:
        return DEFAULT_VALUES.get(key, "")
    return (CONTENT_DIR / filename).read_text(encoding="utf-8")


def stored(key: str) -> str | None:
    """저장소에 실제로 저장된 값만 돌려준다(기본값 대체 없음)."""
    return get_storage().get_setting(key)


def get(key: str) -> str:
    """저장된 설정값을, 없거나 읽지 못하면 기본값을 돌려준다."""
    try:
        value = stored(key)
    except StorageError:
        log.exception("설정을 읽지 못해 기본값을 사용합니다: %s", key)
        value = None
    return value if value else default(key)


def _touch(items: dict[str, str | None]) -> dict[str, str | None]:
    """저장할 항목에 마지막 수정 일시를 덧붙인다 (FR-7.8)."""
    return {**items, "updated_at": now_kst().isoformat()}


def set(key: str, value: str) -> None:
    """설정값을 저장한다. 실패하면 StorageError."""
    get_storage().set_settings(_touch({key: value}))


def set_many(items: dict[str, str | None]) -> None:
    """여러 설정을 한 번에 저장한다. 값이 None인 키는 기본값으로 되돌린다."""
    get_storage().set_settings(_touch(items))


def reset(key: str) -> None:
    """설정을 지워 기본값으로 되돌린다."""
    get_storage().set_settings(_touch({key: None}))


def localized(kind: str, lang: str) -> str:
    """kind(notice/pledge/safety_url)의 해당 언어 값을 돌려준다."""
    return get(f"{kind}_{lang}")


def safety_url(lang: str) -> str:
    """안전교육 URL. 영문 URL이 비어 있으면 한글 URL을 쓴다 (FR-5.2)."""
    url = get(f"safety_url_{lang}")
    if not url and lang != "ko":
        url = get("safety_url_ko")
    return url


def is_valid_url(url: str) -> bool:
    """http:// 또는 https://로 시작하는 공백 없는 주소인지 확인한다."""
    return bool(URL_RE.match(url))


def updated_at() -> str | None:
    """마지막 설정 수정 일시(ISO 문자열)."""
    try:
        return stored("updated_at")
    except StorageError:
        return None


# ── 로고 ───────────────────────────────────────────────────
def process_logo(data: bytes, filename: str) -> tuple[bytes, str]:
    """업로드한 로고를 검사하고 저장할 형태(bytes, MIME)로 바꾼다.

    PNG/JPG는 가로 400px 이하로 줄여 PNG로 저장한다. SVG는 크기·스크립트만 검사해 그대로 둔다.
    """
    if len(data) > LOGO_MAX_UPLOAD:
        raise LogoError("logo_err_size")
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext == "svg":
        if len(data) > LOGO_MAX_SVG:
            raise LogoError("logo_err_svg_size")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as e:
            raise LogoError("logo_err_invalid") from e
        if "<svg" not in text.lower():
            raise LogoError("logo_err_invalid")
        if re.search(r"<script|<foreignobject|\son\w+\s*=|javascript:", text, re.IGNORECASE):
            raise LogoError("logo_err_unsafe")
        return data, "image/svg+xml"

    if ext not in ("png", "jpg", "jpeg"):
        raise LogoError("logo_err_invalid")

    from PIL import Image, UnidentifiedImageError

    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as e:
        raise LogoError("logo_err_invalid") from e
    if img.format not in ("PNG", "JPEG"):
        raise LogoError("logo_err_invalid")
    if img.width > LOGO_MAX_WIDTH:
        height = max(1, round(img.height * LOGO_MAX_WIDTH / img.width))
        img = img.resize((LOGO_MAX_WIDTH, height), Image.LANCZOS)
    if img.mode not in ("RGB", "RGBA", "L", "LA", "P"):
        img = img.convert("RGBA")
    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue(), "image/png"


def save_logo(data: bytes, mime: str) -> None:
    """로고를 base64 조각(logo_0, logo_1 …)으로 저장한다. 이전 로고의 남는 조각은 지운다."""
    encoded = base64.b64encode(data).decode("ascii")
    chunks = [encoded[i : i + LOGO_CHUNK] for i in range(0, len(encoded), LOGO_CHUNK)]
    old_count = _logo_chunk_count()
    items: dict[str, str | None] = {f"logo_{i}": c for i, c in enumerate(chunks)}
    for i in range(len(chunks), old_count):
        items[f"logo_{i}"] = None
    items["logo_mime"] = mime
    items["logo_chunks"] = str(len(chunks))
    get_storage().set_settings(_touch(items))


def delete_logo() -> None:
    """로고를 삭제한다."""
    items: dict[str, str | None] = {f"logo_{i}": None for i in range(_logo_chunk_count())}
    items["logo_mime"] = None
    items["logo_chunks"] = None
    get_storage().set_settings(_touch(items))


def _logo_chunk_count() -> int:
    try:
        return int(stored("logo_chunks") or 0)
    except (StorageError, ValueError):
        return 0


def get_logo() -> tuple[bytes, str] | None:
    """저장된 로고(bytes, MIME)를 돌려준다. 없거나 읽지 못하면 None."""
    try:
        count = int(stored("logo_chunks") or 0)
        if count <= 0:
            return None
        mime = stored("logo_mime") or "image/png"
        parts = [stored(f"logo_{i}") for i in range(count)]
        if any(p is None for p in parts):
            return None
        return base64.b64decode("".join(parts)), mime
    except (StorageError, ValueError):
        log.exception("로고를 읽지 못했습니다.")
        return None
