"""관리자 화면 (FR-4 기록 열람, FR-7 앱 설정).

인증 전에는 로그인 폼만 그리고 기록·설정은 읽지도 않는다.
버튼 동작은 on_click 콜백에서 처리하고, 결과 메시지는 session_state["flash_<구역>"]에
문구 키로 넣어 다음 실행에서 보여준다(언어를 바꿔도 메시지가 번역된다).
"""

from __future__ import annotations

import functools
import hmac
import os
import threading
import time
from datetime import datetime
from types import ModuleType

import streamlit as st

import settings
from i18n import t
from pages_impl import home_button
from storage import PLEDGE_FIELDS, StorageError, get_secret, get_storage, now_kst

MAX_FAILS = 5
TEXT_KINDS = ("notice", "pledge")
CSV_UNSAFE_PREFIX = ("=", "+", "-", "@", "\t", "\r")


def _env_seconds(name: str, default: int) -> int:
    """테스트에서 시간을 줄일 수 있도록 환경 변수로 초 단위 값을 덮어쓴다."""
    try:
        return max(1, int(os.environ.get(name, default)))
    except ValueError:
        return default


LOCK_SECONDS = _env_seconds("VISITOR_ADMIN_LOCK_SECONDS", 5 * 60)  # 첫 잠금 5분
LOCK_MAX_SECONDS = 60 * 60                                          # 잠금이 반복되면 두 배씩, 최대 60분
IDLE_SECONDS = _env_seconds("VISITOR_ADMIN_IDLE_SECONDS", 30 * 60)  # 무동작 30분이면 자동 로그아웃

# pandas는 관리자 화면에서만 필요하므로 그때 불러온다. app.py가 이 모듈을 import하므로
# 맨 위에서 불러오면 pandas를 못 쓰는 환경(예: DLL 차단)에서 방문자 화면까지 멈춘다.
pd: ModuleType = None  # type: ignore[assignment]
_PANDAS_ERROR: str | None = None


def _load_pandas() -> ModuleType:
    """pandas를 처음 필요할 때 불러온다.

    한 번 실패하면 pandas가 반쯤 불러온 상태로 남아 다음 시도에서 ImportError가 아닌
    AttributeError 등이 난다. 그래서 첫 실패 내용을 기억해 두고 같은 오류로 다시 알린다.
    """
    global pd, _PANDAS_ERROR
    if pd is not None:
        return pd
    if _PANDAS_ERROR:
        raise RuntimeError(_PANDAS_ERROR)
    try:
        import pandas
    except Exception as e:  # ImportError, DLL 차단, 반쯤 불러온 모듈 오류 등
        _PANDAS_ERROR = f"{type(e).__name__}: {e}"
        raise RuntimeError(_PANDAS_ERROR) from e
    pd = pandas
    return pd


class LoginGuard:
    """비밀번호 실패 횟수와 잠금을 서버 메모리에 보관한다(FR-4.7).

    session_state에 두면 새로고침(새 세션)으로 잠금이 풀려 무차별 대입이 가능하다.
    접속 주소별로 세지만, 프록시 뒤라 주소를 알 수 없으면 모두 한 묶음("unknown")으로 센다.
    이때 공격자가 일부러 틀려 관리자를 잠글 수 있으므로 잠금 시간에 상한(60분)을 둔다.
    서버가 재시작되면 초기화된다.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._state: dict[str, dict] = {}

    def _entry(self, client: str) -> dict:
        return self._state.setdefault(client, {"fails": 0, "locked_until": 0.0, "locks": 0})

    def remaining(self, client: str) -> float:
        """남은 잠금 시간(초). 잠겨 있지 않으면 0."""
        with self._lock:
            return max(0.0, self._entry(client)["locked_until"] - time.time())

    def fails(self, client: str) -> int:
        with self._lock:
            return self._entry(client)["fails"]

    def record_failure(self, client: str) -> None:
        """실패를 기록하고, MAX_FAILS번이면 잠근다. 잠금이 반복될수록 시간이 두 배로 는다."""
        with self._lock:
            e = self._entry(client)
            e["fails"] += 1
            if e["fails"] >= MAX_FAILS:
                e["locks"] += 1
                e["locked_until"] = time.time() + min(LOCK_SECONDS * 2 ** (e["locks"] - 1),
                                                      LOCK_MAX_SECONDS)
                e["fails"] = 0

    def record_success(self, client: str) -> None:
        with self._lock:
            self._state.pop(client, None)


@st.cache_resource
def login_guard() -> LoginGuard:
    """서버 프로세스 전체에서 하나만 쓰는 LoginGuard."""
    return LoginGuard()


def _client_id() -> str:
    """잠금을 셀 단위(접속 주소). 알 수 없으면 'unknown'."""
    try:
        ip = st.context.ip_address
    except Exception:
        ip = None
    # 문자열이 아닌 값(테스트 환경의 가짜 객체 등)은 매번 달라져 잠금이 무력화되므로 한 묶음으로 센다.
    return ip if isinstance(ip, str) and ip else "unknown"


# ── 공통 도우미 ─────────────────────────────────────────────
def _flash(section: str, level: str, key: str, **kwargs) -> None:
    """다음 실행에서 보여줄 메시지를 남긴다."""
    st.session_state[f"flash_{section}"] = (level, key, kwargs)


def _show_flash(section: str) -> None:
    """남겨둔 메시지를 한 번 보여주고 지운다."""
    item = st.session_state.pop(f"flash_{section}", None)
    if item:
        level, key, kwargs = item
        getattr(st, level)(t(key, **kwargs))


def retention_cutoff() -> datetime:
    """보유 기간(1년) 기준 시각. 이보다 먼저 제출된 기록이 파기 대상이다."""
    _load_pandas()
    return (pd.Timestamp(now_kst()) - pd.DateOffset(years=1)).to_pydatetime()


def csv_safe(value):
    """엑셀에서 수식으로 실행될 수 있는 값 앞에 '를 붙인다(CSV 수식 삽입 방지)."""
    if isinstance(value, str) and value.startswith(CSV_UNSAFE_PREFIX):
        return "'" + value
    return value


# ── 인증 (FR-4.1, 4.2, 4.6, 4.7) ─────────────────────────────
def _login() -> None:
    """로그인 폼 제출 콜백."""
    ss = st.session_state
    guard, client = login_guard(), _client_id()
    given = ss.get("admin_pw", "")
    ss["admin_pw"] = ""
    if guard.remaining(client) > 0:
        return
    expected = str(get_secret("ADMIN_PASSWORD") or "")
    if expected and hmac.compare_digest(given.encode(), expected.encode()):
        guard.record_success(client)
        ss["admin_ok"] = True
        ss["admin_last_seen"] = time.time()
        ss.pop("admin_idle_logout", None)
        return
    guard.record_failure(client)


def _logout() -> None:
    """인증을 해제하고 관리자 화면에서 쓰던 상태를 지운다."""
    ss = st.session_state
    for k in list(ss.keys()):
        if k in ("admin_ok", "admin_last_seen") or k.startswith(
            ("edit_", "flash_", "retention_ok", "logo_file")
        ):
            del ss[k]


def _check_idle() -> None:
    """마지막 관리자 동작 후 IDLE_SECONDS가 지났으면 자동 로그아웃한다(공용 PC 대비)."""
    ss = st.session_state
    if not ss.get("admin_ok"):
        return
    now = time.time()
    if now - ss.get("admin_last_seen", now) > IDLE_SECONDS:
        _logout()
        ss["admin_idle_logout"] = True
    else:
        ss["admin_last_seen"] = now


def _admin_action(fn):
    """관리자 버튼 콜백 장식자: 실행 전에 무동작 만료를 확인하고, 로그인 상태가 아니면 아무것도 하지 않는다.

    콜백은 화면을 그리기 전에 실행되므로 render()의 만료 확인만으로는 오래 방치된 탭의 버튼을 막지 못한다.
    """

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        _check_idle()
        if not st.session_state.get("admin_ok"):
            return None
        return fn(*args, **kwargs)

    return wrapper


def render_login() -> None:
    """로그인 폼을 그린다."""
    if not get_secret("ADMIN_PASSWORD"):
        st.error(t("admin_no_password"))
        return
    if st.session_state.pop("admin_idle_logout", None):
        st.info(t("admin_idle_logout", minutes=max(1, IDLE_SECONDS // 60)))
    guard, client = login_guard(), _client_id()
    remaining = guard.remaining(client)
    if remaining > 0:
        st.error(t("admin_locked", minutes=int(remaining // 60) + 1))
        return
    with st.form("admin_login_form"):
        st.text_input(t("admin_password"), type="password", key="admin_pw")
        st.form_submit_button(t("admin_login"), type="primary", on_click=_login)
    fails = guard.fails(client)
    if fails:
        st.error(t("admin_wrong", left=MAX_FAILS - fails))


# ── 서약서 기록 (FR-4.3 ~ 4.5, 4.8, 4.9) ─────────────────────
def _records_frame(records: list[dict]) -> pd.DataFrame:
    """기록 목록을 DataFrame으로 바꾸고 제출 시각 열(_dt)을 붙인다."""
    df = pd.DataFrame(records, columns=PLEDGE_FIELDS)
    df["_dt"] = pd.to_datetime(df["submitted_at"], format="ISO8601", utc=True).dt.tz_convert(
        "Asia/Seoul"
    )
    return df


@_admin_action
def _purge() -> None:
    """보유 기간이 지난 기록을 파기한다."""
    st.session_state["retention_ok"] = False
    try:
        n = get_storage().delete_pledges_before(retention_cutoff())
    except StorageError:
        _flash("records", "error", "storage_error")
        return
    _flash("records", "success", "retention_done", n=n)


def _display_frame(df: pd.DataFrame) -> pd.DataFrame:
    """화면·CSV용 열 구성과 열 이름(현재 언어)."""
    out = df.copy()
    out["submitted_at"] = out["_dt"].dt.strftime("%Y-%m-%d %H:%M:%S")
    cols = [f for f in PLEDGE_FIELDS if f != "id"] + ["id"]
    return out[cols].rename(columns={c: t(f"col_{c}") for c in cols})


def render_records(df: pd.DataFrame, expired: int) -> None:
    """기록 표, 필터, CSV 다운로드, 파기를 그린다."""
    _show_flash("records")
    if df.empty:
        st.info(t("records_empty"))
    else:
        today = now_kst().date()
        first = min(df["_dt"].min().date(), today)
        c1, c2 = st.columns(2)
        dates = c1.date_input(t("filter_dates"), value=(first, today), key="flt_dates")
        name_q = c2.text_input(t("filter_name"), key="flt_name")
        c3, c4 = st.columns(2)
        nats = c3.multiselect(t("filter_nationality"), sorted(df["nationality"].unique()),
                              key="flt_nat", placeholder=t("filter_all"))
        purposes = c4.multiselect(t("filter_purpose"), sorted(df["purpose"].unique()),
                                  key="flt_purpose", placeholder=t("filter_all"))

        mask = pd.Series(True, index=df.index)
        if isinstance(dates, (tuple, list)) and len(dates) == 2:
            day = df["_dt"].dt.date
            mask &= (day >= dates[0]) & (day <= dates[1])
        if name_q.strip():
            mask &= df["name"].str.contains(name_q.strip(), case=False, regex=False)
        if nats:
            mask &= df["nationality"].isin(nats)
        if purposes:
            mask &= df["purpose"].isin(purposes)

        view = _display_frame(df[mask])
        st.caption(t("records_count", n=len(view), total=len(df)))
        st.dataframe(view, hide_index=True, width="stretch")
        csv = view.map(csv_safe).to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            t("download_csv"),
            data=csv,
            file_name=f"pledges_{now_kst():%Y%m%d_%H%M}.csv",
            mime="text/csv",
            key="dl_csv",
        )

    st.divider()
    st.subheader(t("retention_title"))
    if expired == 0:
        st.caption(t("retention_none"))
        return
    st.checkbox(t("retention_confirm", n=expired), key="retention_ok")
    st.button(t("retention_button"), key="retention_btn", type="primary",
              disabled=not st.session_state.get("retention_ok"), on_click=_purge)


# ── 앱 설정 (FR-7) ──────────────────────────────────────────
@_admin_action
def _save_text(key: str) -> None:
    """안내문·서약서 본문 저장 콜백."""
    text = st.session_state.get(f"edit_{key}", "")
    if not text.strip():
        _flash(key, "error", "set_err_empty")
        return
    if len(text) > settings.MAX_TEXT_LEN:
        _flash(key, "error", "set_err_long")
        return
    try:
        settings.set(key, text)
    except StorageError:
        _flash(key, "error", "storage_error")
        return
    _flash(key, "success", "set_saved")


@_admin_action
def _reset_text(key: str) -> None:
    """기본값으로 되돌리기 콜백."""
    try:
        settings.reset(key)
    except StorageError:
        _flash(key, "error", "storage_error")
        return
    st.session_state[f"edit_{key}"] = settings.default(key)
    _flash(key, "success", "set_reset_done")


@_admin_action
def _save_urls() -> None:
    """안전교육 URL 저장 콜백. 빈 칸은 설정 삭제(=기본 주소 사용)로 처리한다."""
    items: dict[str, str | None] = {}
    for key in settings.URL_KEYS:
        url = st.session_state.get(f"edit_{key}", "").strip()
        if url and not settings.is_valid_url(url):
            _flash("urls", "error", "set_url_invalid")
            return
        items[key] = url or None
    try:
        settings.set_many(items)
    except StorageError:
        _flash("urls", "error", "storage_error")
        return
    _flash("urls", "success", "set_saved")


@_admin_action
def _reset_urls() -> None:
    """안전교육 URL을 기본 주소로 되돌리는 콜백 (FR-7.6)."""
    try:
        settings.set_many({key: None for key in settings.URL_KEYS})
    except StorageError:
        _flash("urls", "error", "storage_error")
        return
    for key in settings.URL_KEYS:
        st.session_state[f"edit_{key}"] = settings.default(key)
    _flash("urls", "success", "set_reset_done")


@_admin_action
def _upload_logo() -> None:
    """로고 등록 콜백."""
    ss = st.session_state
    file = ss.get(f"logo_file_{ss.get('logo_nonce', 0)}")
    if file is None:
        _flash("logo", "warning", "set_logo_pick")
        return
    try:
        data, mime = settings.process_logo(file.getvalue(), file.name)
        settings.save_logo(data, mime)
    except settings.LogoError as e:
        _flash("logo", "error", e.args[0])
        return
    except StorageError:
        _flash("logo", "error", "storage_error")
        return
    ss["logo_nonce"] = ss.get("logo_nonce", 0) + 1  # 업로더 비우기
    _flash("logo", "success", "set_saved")


@_admin_action
def _delete_logo() -> None:
    """로고 삭제 콜백."""
    try:
        settings.delete_logo()
    except StorageError:
        _flash("logo", "error", "storage_error")
        return
    _flash("logo", "success", "set_logo_deleted")


def _init_edit(key: str, value: str) -> None:
    """편집창 초기값을 한 번만 채운다(사용자가 고치는 중인 값을 덮어쓰지 않게)."""
    st.session_state.setdefault(f"edit_{key}", value)


def render_text_setting(kind: str) -> None:
    """안내문 또는 서약서 본문 편집기를 그린다 (FR-7.2, 7.3, 7.6)."""
    st.subheader(t(f"set_{kind}"))
    for lang, tab in zip(("ko", "en"), st.tabs([t("set_lang_ko"), t("set_lang_en")])):
        key = f"{kind}_{lang}"
        with tab:
            _init_edit(key, settings.get(key))
            if not settings.stored(key):
                st.caption(t("set_using_default"))
            st.text_area(t(f"set_{kind}"), key=f"edit_{key}", height=300,
                         help=t("set_markdown_help"), label_visibility="collapsed")
            with st.expander(t("set_preview")):
                st.markdown(st.session_state.get(f"edit_{key}", ""))
            c1, c2 = st.columns(2)
            c1.button(t("set_save"), key=f"save_{key}", type="primary",
                      on_click=_save_text, args=(key,), width="stretch")
            c2.button(t("set_reset"), key=f"reset_{key}",
                      on_click=_reset_text, args=(key,), width="stretch")
            _show_flash(key)


def render_url_setting() -> None:
    """안전교육 URL 편집기를 그린다 (FR-7.4)."""
    st.subheader(t("set_safety"))
    for key in settings.URL_KEYS:
        _init_edit(key, settings.stored(key) or settings.default(key))
    st.text_input(t("set_safety_ko"), key="edit_safety_url_ko", placeholder="https://")
    st.text_input(t("set_safety_en"), key="edit_safety_url_en", placeholder="https://")
    c1, c2 = st.columns(2)
    c1.button(t("set_save"), key="save_urls", type="primary", on_click=_save_urls, width="stretch")
    c2.button(t("set_reset"), key="reset_urls", on_click=_reset_urls, width="stretch")
    _show_flash("urls")


def render_logo_setting() -> None:
    """로고 등록·교체·삭제를 그린다 (FR-7.5)."""
    st.subheader(t("set_logo"))
    logo = settings.get_logo()
    if logo:
        st.caption(t("set_logo_current"))
        show_logo(logo)
        st.button(t("set_logo_delete"), key="logo_delete", on_click=_delete_logo)
    else:
        st.caption(t("set_logo_none"))
    st.file_uploader(t("set_logo_upload"), type=["png", "jpg", "jpeg", "svg"],
                     key=f"logo_file_{st.session_state.get('logo_nonce', 0)}",
                     help=t("set_logo_help"))
    st.button(t("set_logo_upload"), key="logo_upload", type="primary", on_click=_upload_logo)
    _show_flash("logo")


def show_logo(logo: tuple[bytes, str], width: int = 160) -> None:
    """로고를 그린다. SVG는 문자열로 넘겨야 st.image가 그린다."""
    data, mime = logo
    st.image(data.decode("utf-8") if mime == "image/svg+xml" else data, width=width)


def render_settings() -> None:
    """앱 설정 탭을 그린다."""
    updated = settings.updated_at()
    if updated:
        st.caption(t("settings_updated",
                     time=datetime.fromisoformat(updated).strftime("%Y-%m-%d %H:%M")))
    else:
        st.caption(t("settings_never"))
    render_url_setting()
    st.divider()
    render_logo_setting()
    for kind in TEXT_KINDS:
        st.divider()
        render_text_setting(kind)


# ── 화면 ────────────────────────────────────────────────────
def render() -> None:
    """관리자 화면을 그린다."""
    home_button()
    st.header(t("admin_title"))

    _check_idle()
    if not st.session_state.get("admin_ok"):
        render_login()
        return

    st.button(t("admin_logout"), key="admin_logout", on_click=_logout)

    try:
        _load_pandas()
    except Exception as e:  # 첫 실패 뒤에는 RuntimeError로 같은 내용을 다시 알린다(#2)
        st.error(t("admin_pandas_error"))
        st.caption(str(e))
        return

    try:
        df = _records_frame(get_storage().list_pledges())
    except StorageError:
        st.error(t("storage_error"))
        df = None

    expired = 0
    if df is not None:
        expired = int((df["_dt"] < pd.Timestamp(retention_cutoff())).sum())
        today = int((df["_dt"].dt.date == now_kst().date()).sum())
        m1, m2, m3 = st.columns(3)
        m1.metric(t("metric_total"), f"{len(df):,}")
        m2.metric(t("metric_today"), f"{today:,}")
        m3.metric(t("metric_expired"), f"{expired:,}")
        if expired:
            st.warning(t("retention_banner", n=expired), icon="🗑️")

    tab_records, tab_settings = st.tabs([t("tab_records"), t("tab_settings")])
    with tab_records:
        if df is not None:
            render_records(df, expired)
    with tab_settings:
        try:
            render_settings()
        except StorageError:
            st.error(t("storage_error"))
