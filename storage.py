"""저장소 인터페이스와 구현.

- SQLiteStorage: 로컬 개발·테스트용 (Streamlit Cloud에서는 재시작 시 파일이 지워지므로 운영에 쓰지 않는다)
- GoogleSheetsStorage: 운영용. 한 스프레드시트 안에 pledges 시트와 settings 시트를 둔다.

get_storage()는 st.secrets에 gcp_service_account가 있으면 Google Sheets, 없으면 SQLite를 돌려준다.
저장소 오류는 모두 StorageError로 바꿔 던지므로 화면 코드는 StorageError만 잡으면 된다.
"""

from __future__ import annotations

import os
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path

import streamlit as st

KST = timezone(timedelta(hours=9))

# PRD 6장 pledges 필드 순서
PLEDGE_FIELDS = [
    "id",
    "submitted_at",
    "language",
    "name",
    "phone",
    "nationality",
    "purpose",
    "privacy_agreed",
    "pledge_agreed",
]
BOOL_FIELDS = ("privacy_agreed", "pledge_agreed")
SETTINGS_HEADER = ["key", "value", "updated_at"]

DEFAULT_DB_PATH = Path(__file__).parent / "data" / "visitor.db"


class StorageError(Exception):
    """저장소 읽기·쓰기 실패 (네트워크 오류, 권한 오류 등)."""


def now_kst() -> datetime:
    """현재 한국 시간을 돌려준다."""
    return datetime.now(KST)


class Storage(ABC):
    """서약서 기록과 앱 설정을 저장하는 저장소 인터페이스."""

    @abstractmethod
    def save_pledge(self, record: dict) -> None:
        """서약서 한 건을 저장한다. record는 PLEDGE_FIELDS 키를 가진다."""

    @abstractmethod
    def list_pledges(self) -> list[dict]:
        """모든 서약서 기록을 최신순으로 돌려준다."""

    @abstractmethod
    def delete_pledges_before(self, cutoff: datetime) -> int:
        """cutoff 이전에 제출된 기록을 삭제하고 삭제 건수를 돌려준다."""

    @abstractmethod
    def get_setting(self, key: str) -> str | None:
        """설정값을 돌려준다. 없으면 None."""

    @abstractmethod
    def set_setting(self, key: str, value: str | None) -> None:
        """설정값을 저장한다. value가 None이면 삭제(기본값으로 되돌림)."""

    def set_settings(self, items: dict[str, str | None]) -> None:
        """여러 설정을 한 번에 저장한다. 구현체가 더 효율적인 방법으로 덮어쓸 수 있다."""
        for key, value in items.items():
            self.set_setting(key, value)


class SQLiteStorage(Storage):
    """로컬 SQLite 파일 저장소."""

    def __init__(self, path: str | Path = DEFAULT_DB_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        """요청마다 새 연결을 연다(Streamlit은 여러 스레드에서 호출한다)."""
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        """테이블이 없으면 만든다."""
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pledges (
                    id TEXT PRIMARY KEY,
                    submitted_at TEXT NOT NULL,
                    language TEXT NOT NULL,
                    name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    nationality TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    privacy_agreed INTEGER NOT NULL,
                    pledge_agreed INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def save_pledge(self, record: dict) -> None:
        """서약서 한 건을 저장한다."""
        values = [record[f] for f in PLEDGE_FIELDS]
        placeholders = ",".join("?" * len(PLEDGE_FIELDS))
        try:
            with self._lock, self._connect() as conn:
                conn.execute(
                    f"INSERT INTO pledges ({','.join(PLEDGE_FIELDS)}) VALUES ({placeholders})",
                    values,
                )
        except sqlite3.Error as e:
            raise StorageError(str(e)) from e

    def list_pledges(self) -> list[dict]:
        """모든 기록을 최신순으로 돌려준다."""
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT * FROM pledges ORDER BY submitted_at DESC"
                ).fetchall()
        except sqlite3.Error as e:
            raise StorageError(str(e)) from e
        result = []
        for row in rows:
            item = dict(row)
            for f in BOOL_FIELDS:
                item[f] = bool(item[f])
            result.append(item)
        return result

    def delete_pledges_before(self, cutoff: datetime) -> int:
        """cutoff 이전 기록을 삭제한다. 시각은 KST ISO 문자열로 비교한다."""
        cutoff_iso = cutoff.astimezone(KST).isoformat()
        try:
            with self._lock, self._connect() as conn:
                cur = conn.execute("DELETE FROM pledges WHERE submitted_at < ?", (cutoff_iso,))
                return cur.rowcount
        except sqlite3.Error as e:
            raise StorageError(str(e)) from e

    def get_setting(self, key: str) -> str | None:
        """설정값을 돌려준다."""
        try:
            with self._connect() as conn:
                row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        except sqlite3.Error as e:
            raise StorageError(str(e)) from e
        return row["value"] if row else None

    def set_setting(self, key: str, value: str | None) -> None:
        """설정값을 저장하거나(None이면) 삭제한다."""
        self.set_settings({key: value})

    def set_settings(self, items: dict[str, str | None]) -> None:
        """여러 설정을 한 트랜잭션으로 저장한다."""
        ts = now_kst().isoformat()
        try:
            with self._lock, self._connect() as conn:
                for key, value in items.items():
                    if value is None:
                        conn.execute("DELETE FROM settings WHERE key = ?", (key,))
                    else:
                        conn.execute(
                            """
                            INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)
                            ON CONFLICT(key) DO UPDATE SET value = excluded.value,
                                                           updated_at = excluded.updated_at
                            """,
                            (key, value, ts),
                        )
        except sqlite3.Error as e:
            raise StorageError(str(e)) from e


class GoogleSheetsStorage(Storage):
    """Google Sheets 저장소.

    Sheets API는 분당 읽기 횟수 제한이 있으므로 읽은 내용을 잠시(CACHE_TTL초) 메모리에 두고,
    이 인스턴스로 쓰기를 하면 즉시 캐시를 비운다. 셀 값은 RAW로 써서 '='로 시작하는 입력이
    수식으로 실행되지 않게 하고, 휴대폰 번호 앞자리 0도 보존한다.
    """

    PLEDGE_SHEET = "pledges"
    SETTINGS_SHEET = "settings"
    CACHE_TTL = 60

    def __init__(self, service_account_info: dict, sheet_id: str):
        self.service_account_info = service_account_info
        self.sheet_id = sheet_id
        self._lock = threading.RLock()
        self._spreadsheet = None
        self._worksheets: dict = {}
        self._cache: dict[str, tuple[float, object]] = {}

    # ── 내부 도우미 ─────────────────────────────────────────
    def _run(self, fn):
        """gspread 호출을 실행하고 오류를 StorageError로 바꾼다."""
        try:
            with self._lock:
                return fn()
        except StorageError:
            raise
        except Exception as e:  # gspread·google-auth·네트워크 오류 전부
            raise StorageError(f"{type(e).__name__}: {e}") from e

    def _worksheet(self, name: str, header: list[str]):
        """시트를 가져오고, 없으면 헤더와 함께 만든다."""
        if name in self._worksheets:
            return self._worksheets[name]
        import gspread

        if not self.sheet_id:
            raise StorageError("SHEET_ID가 설정되지 않았습니다.")
        if self._spreadsheet is None:
            client = gspread.service_account_from_dict(self.service_account_info)
            self._spreadsheet = client.open_by_key(self.sheet_id)
        try:
            ws = self._spreadsheet.worksheet(name)
        except gspread.WorksheetNotFound:
            ws = self._spreadsheet.add_worksheet(title=name, rows=1000, cols=len(header))
        if ws.row_values(1) != header:
            if not ws.row_values(1):
                ws.update(values=[header], range_name="A1", value_input_option="RAW")
            else:
                raise StorageError(f"'{name}' 시트의 첫 줄이 {header}와 다릅니다.")
        self._worksheets[name] = ws
        return ws

    def _cached(self, name: str, loader):
        """name 캐시가 유효하면 그 값을, 아니면 loader()를 실행해 저장한 값을 돌려준다."""
        hit = self._cache.get(name)
        if hit and time.monotonic() - hit[0] < self.CACHE_TTL:
            return hit[1]
        value = loader()
        self._cache[name] = (time.monotonic(), value)
        return value

    def _invalidate(self, name: str) -> None:
        """캐시를 비운다."""
        self._cache.pop(name, None)

    @staticmethod
    def _delete_by_values(ws, values: set[str], col: int = 1) -> int:
        """col 열(1부터) 값이 values에 있는 행을 지우고 지운 행 수를 돌려준다.

        행 번호를 미리 계산해 두면, 그 사이 다른 요청(다른 관리자, 시트 직접 편집)이 행을 지웠을 때
        번호가 밀려 엉뚱한 행이 지워진다. 그래서 한 구간을 지우기 직전마다 그 열을 다시 읽어
        실제 위치를 확인하고, 맨 아래 연속 구간부터 하나씩 지운다.
        """
        remaining = set(values)
        deleted = 0
        for _ in range(len(values) + 1):  # 구간마다 한 번씩, 무한 반복 방지
            if not remaining:
                break
            column = ws.col_values(col)
            rows = [i + 1 for i, v in enumerate(column) if i > 0 and v in remaining]
            if not rows:
                break
            end = start = rows[-1]
            row_set = set(rows)
            while start - 1 in row_set:
                start -= 1
            ws.delete_rows(start, end)
            for r in range(start, end + 1):
                remaining.discard(column[r - 1])
            deleted += end - start + 1
        return deleted

    # ── 서약서 ──────────────────────────────────────────────
    def _pledge_ws(self):
        return self._worksheet(self.PLEDGE_SHEET, PLEDGE_FIELDS)

    def save_pledge(self, record: dict) -> None:
        """서약서 한 건을 시트 맨 아래에 추가한다."""
        row = [
            ("TRUE" if record[f] else "FALSE") if f in BOOL_FIELDS else str(record[f])
            for f in PLEDGE_FIELDS
        ]

        def _do():
            self._pledge_ws().append_row(row, value_input_option="RAW")
            self._invalidate("pledges")

        self._run(_do)

    def _load_pledges(self) -> list[dict]:
        values = self._pledge_ws().get_all_values()
        result = []
        for raw in values[1:]:
            if not any(raw):
                continue
            item = dict(zip(PLEDGE_FIELDS, raw + [""] * (len(PLEDGE_FIELDS) - len(raw))))
            for f in BOOL_FIELDS:
                item[f] = str(item[f]).upper() == "TRUE"
            result.append(item)
        result.sort(key=lambda r: r["submitted_at"], reverse=True)
        return result

    def list_pledges(self) -> list[dict]:
        """모든 기록을 최신순으로 돌려준다."""
        return self._run(lambda: list(self._cached("pledges", self._load_pledges)))

    def delete_pledges_before(self, cutoff: datetime) -> int:
        """cutoff 이전 기록을 id로 찾아 지운다(행 번호가 밀려도 안전하게)."""
        cutoff_iso = cutoff.astimezone(KST).isoformat()
        time_col = PLEDGE_FIELDS.index("submitted_at")
        id_col = PLEDGE_FIELDS.index("id")

        def _do():
            ws = self._pledge_ws()
            ids = {
                raw[id_col]
                for raw in ws.get_all_values()[1:]
                if len(raw) > time_col and raw[time_col] and raw[time_col] < cutoff_iso
                and raw[id_col]
            }
            deleted = self._delete_by_values(ws, ids, col=id_col + 1)
            self._invalidate("pledges")
            return deleted

        return self._run(_do)

    # ── 설정 ────────────────────────────────────────────────
    def _settings_ws(self):
        return self._worksheet(self.SETTINGS_SHEET, SETTINGS_HEADER)

    def _load_settings(self) -> dict[str, tuple[int, str]]:
        """{key: (행 번호, 값)}을 돌려준다."""
        values = self._settings_ws().get_all_values()
        return {
            raw[0]: (i + 2, raw[1] if len(raw) > 1 else "")
            for i, raw in enumerate(values[1:])
            if raw and raw[0]
        }

    def get_setting(self, key: str) -> str | None:
        """설정값을 돌려준다."""
        found = self._run(lambda: self._cached("settings", self._load_settings)).get(key)
        return found[1] if found else None

    def set_setting(self, key: str, value: str | None) -> None:
        """설정값 하나를 저장한다."""
        self.set_settings({key: value})

    def set_settings(self, items: dict[str, str | None]) -> None:
        """여러 설정을 API 호출 몇 번으로 저장한다.

        수정할 행 번호는 쓰기 바로 직전에 key 열을 다시 읽어 정하고, 삭제는 key로 확인하며 지운다.
        같은 서버 안의 요청은 self._lock으로 한 번에 하나씩 처리된다.
        """
        ts = now_kst().isoformat()

        def _do():
            ws = self._settings_ws()
            key_rows = {v: i + 1 for i, v in enumerate(ws.col_values(1)) if i > 0 and v}
            updates, appends, deletes = [], [], set()
            for key, value in items.items():
                if value is None:
                    if key in key_rows:
                        deletes.add(key)
                elif key in key_rows:
                    row = key_rows[key]
                    updates.append({"range": f"B{row}:C{row}", "values": [[value, ts]]})
                else:
                    appends.append([key, value, ts])
            if updates:
                ws.batch_update(updates, value_input_option="RAW")
            if appends:
                ws.append_rows(appends, value_input_option="RAW")
            if deletes:
                self._delete_by_values(ws, deletes, col=1)
            self._invalidate("settings")

        self._run(_do)


def _read_secrets() -> dict:
    """st.secrets를 dict로 읽는다. secrets.toml이 없으면 빈 dict."""
    try:
        return st.secrets.to_dict()
    except Exception:
        return {}


def get_secret(name: str, default=None):
    """비밀 설정값 하나를 돌려준다. secrets.toml이 없어도 오류 없이 default를 돌려준다."""
    return _read_secrets().get(name, default)


@st.cache_resource
def get_storage() -> Storage:
    """설정에 맞는 저장소 인스턴스를 하나만 만들어 돌려준다."""
    secrets = _read_secrets()
    sa_info = secrets.get("gcp_service_account")
    if sa_info:
        return GoogleSheetsStorage(dict(sa_info), secrets.get("SHEET_ID", ""))
    # 테스트에서는 VISITOR_APP_DB 환경 변수로 임시 DB 경로를 지정한다.
    return SQLiteStorage(os.environ.get("VISITOR_APP_DB", DEFAULT_DB_PATH))
