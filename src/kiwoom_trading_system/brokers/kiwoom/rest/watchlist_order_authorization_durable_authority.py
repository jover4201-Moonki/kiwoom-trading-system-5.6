from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import re
import sqlite3

from .watchlist_order_authorization_adapter_evidence import (
    KiwoomOrderAuthorizationAuthorityReportedResult,
    WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot,
)
from .watchlist_order_authorization_consumption_claim import (
    KiwoomOrderAuthorizationConsumptionClaimContext,
    WatchlistOrderAuthorizationConsumptionClaimSnapshot,
)
from .watchlist_order_send_request import WatchlistOrderSendRequestSnapshot

__all__ = [
    "WatchlistOrderAuthorizationDurableAuthorityError",
    "KiwoomOrderAuthorizationDurableAuthorityConfig",
    "KiwoomOrderAuthorizationDurableLedgerRecord",
    "KiwoomOrderAuthorizationSQLiteAuthority",
    "WatchlistOrderAuthorizationDurableVerificationSnapshot",
    "initialize_demo_watchlist_order_authorization_durable_ledger",
    "verify_demo_watchlist_order_authorization_durable_consumption",
]


class WatchlistOrderAuthorizationDurableAuthorityError(RuntimeError):
    pass


@dataclass(frozen=True)
class KiwoomOrderAuthorizationDurableAuthorityConfig:
    backend_instance_reference: str
    authorization_authority_reference: str
    authority_approval_reference: str
    authority_conformance_reference: str

    def __post_init__(self) -> None:
        if not all(
            _is_config_reference(value)
            for value in (
                self.backend_instance_reference,
                self.authorization_authority_reference,
                self.authority_approval_reference,
                self.authority_conformance_reference,
            )
        ):
            _raise("AUTHORITY_CONFIG_INVALID")


@dataclass(frozen=True)
class KiwoomOrderAuthorizationDurableLedgerRecord:
    backend_instance_reference: str
    authorization_authority_reference: str
    authorization_evidence_snapshot_id: str
    submission_attempt_reference: str
    send_authorization_reference: str
    claim_fingerprint: str
    authority_approval_reference: str
    authority_conformance_reference: str
    authority_result_reference: str
    consumption_reference: str
    sqlite_journal_mode: str
    sqlite_synchronous_level: int
    record_fingerprint: str


@dataclass(frozen=True)
class WatchlistOrderAuthorizationDurableVerificationSnapshot:
    source_snapshot: WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot
    durable_record: KiwoomOrderAuthorizationDurableLedgerRecord | None
    backend_instance_reference: str
    ledger_schema_reference: str
    verification_decision: str
    indeterminate_reason: str | None
    concrete_sqlite_authority_identity_verified: bool
    ledger_schema_verified: bool
    sqlite_connection_surface_verified: bool
    sqlite_durability_profile_verified: bool
    durable_record_present: bool
    exact_binding_verified: bool
    durable_consumption_record_verified: bool
    authority_approval_provenance_verified: bool
    authority_conformance_provenance_verified: bool
    provider_send_eligibility_authorized: bool
    production_authority_use_authorized: bool
    reconciliation_required: bool
    verification_fingerprint: str


_SCHEMA_ID = "kiwoom-watchlist-order-authorization-durable-ledger-v1"
_LEDGER_SCHEMA_REFERENCE = _SCHEMA_ID
_TRANSACTION_PROFILE_ID = "sqlite-autocommit-true-isolation-none-busy-zero-begin-immediate-v1"
_DURABILITY_PROFILE_ID = "sqlite-main-wal-synchronous-full-v1"
_JOURNAL_MODE = "wal"
_SYNCHRONOUS_LEVEL = 2

_META_TABLE = "kiwoom_order_authorization_meta"
_CONSUMPTION_TABLE = "kiwoom_order_authorization_consumption"
_META_CREATE_SQL = (
    "CREATE TABLE main.kiwoom_order_authorization_meta("
    "schema_key BLOB NOT NULL PRIMARY KEY,schema_value BLOB NOT NULL) STRICT"
)
_CONSUMPTION_CREATE_SQL = (
    "CREATE TABLE main.kiwoom_order_authorization_consumption("
    "backend_instance_reference BLOB NOT NULL,"
    "authorization_authority_reference BLOB NOT NULL,"
    "authorization_evidence_snapshot_id BLOB NOT NULL,"
    "submission_attempt_reference BLOB NOT NULL,"
    "send_authorization_reference BLOB NOT NULL,"
    "claim_fingerprint BLOB NOT NULL,"
    "authority_approval_reference BLOB NOT NULL,"
    "authority_conformance_reference BLOB NOT NULL,"
    "authority_result_reference BLOB NOT NULL,"
    "consumption_reference BLOB NOT NULL,"
    "sqlite_journal_mode BLOB NOT NULL,"
    "sqlite_synchronous_level INTEGER NOT NULL,"
    "record_fingerprint BLOB NOT NULL,"
    "UNIQUE(authorization_authority_reference,authorization_evidence_snapshot_id,submission_attempt_reference,send_authorization_reference),"
    "UNIQUE(authorization_authority_reference,send_authorization_reference),"
    "UNIQUE(authority_result_reference),"
    "UNIQUE(consumption_reference),"
    "UNIQUE(record_fingerprint)) STRICT"
)
_META_STORED_DDL = (
    "CREATE TABLE kiwoom_order_authorization_meta("
    "schema_key BLOB NOT NULL PRIMARY KEY,schema_value BLOB NOT NULL) STRICT"
)
_CONSUMPTION_STORED_DDL = (
    "CREATE TABLE kiwoom_order_authorization_consumption("
    "backend_instance_reference BLOB NOT NULL,"
    "authorization_authority_reference BLOB NOT NULL,"
    "authorization_evidence_snapshot_id BLOB NOT NULL,"
    "submission_attempt_reference BLOB NOT NULL,"
    "send_authorization_reference BLOB NOT NULL,"
    "claim_fingerprint BLOB NOT NULL,"
    "authority_approval_reference BLOB NOT NULL,"
    "authority_conformance_reference BLOB NOT NULL,"
    "authority_result_reference BLOB NOT NULL,"
    "consumption_reference BLOB NOT NULL,"
    "sqlite_journal_mode BLOB NOT NULL,"
    "sqlite_synchronous_level INTEGER NOT NULL,"
    "record_fingerprint BLOB NOT NULL,"
    "UNIQUE(authorization_authority_reference,authorization_evidence_snapshot_id,submission_attempt_reference,send_authorization_reference),"
    "UNIQUE(authorization_authority_reference,send_authorization_reference),"
    "UNIQUE(authority_result_reference),"
    "UNIQUE(consumption_reference),"
    "UNIQUE(record_fingerprint)) STRICT"
)
_META_STORED_DDL_SHA256 = "55FDBAD5B3992B06F98D132FC881B7090E83E00E92CE20B5A05CD73B52F68AFE"
_CONSUMPTION_STORED_DDL_SHA256 = "52CE7F608809602658FAC025425BBBC6AB175586101898FB0AEA3C852C950FB8"

_META_VALUES = {
    "schema_id": _SCHEMA_ID,
    "transaction_profile_id": _TRANSACTION_PROFILE_ID,
    "durability_profile_id": _DURABILITY_PROFILE_ID,
}

_EXPECTED_AUTOINDEX_KEYS = {
    "sqlite_autoindex_kiwoom_order_authorization_meta_1": ("schema_key",),
    "sqlite_autoindex_kiwoom_order_authorization_consumption_1": (
        "authorization_authority_reference",
        "authorization_evidence_snapshot_id",
        "submission_attempt_reference",
        "send_authorization_reference",
    ),
    "sqlite_autoindex_kiwoom_order_authorization_consumption_2": (
        "authorization_authority_reference",
        "send_authorization_reference",
    ),
    "sqlite_autoindex_kiwoom_order_authorization_consumption_3": (
        "authority_result_reference",
    ),
    "sqlite_autoindex_kiwoom_order_authorization_consumption_4": (
        "consumption_reference",
    ),
    "sqlite_autoindex_kiwoom_order_authorization_consumption_5": (
        "record_fingerprint",
    ),
}
_META_AUTOINDEX = frozenset({"sqlite_autoindex_kiwoom_order_authorization_meta_1"})
_CONSUMPTION_AUTOINDEX = frozenset(
    name for name in _EXPECTED_AUTOINDEX_KEYS if "consumption" in name
)
_ALLOWED_AUTOINDEXES = frozenset(_EXPECTED_AUTOINDEX_KEYS)

_PROVIDER_BODY_KEYS = frozenset(
    {"dmst_stex_tp", "stk_cd", "ord_qty", "ord_uv", "trde_tp", "cond_uv"}
)
_LOWER_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
_RESULT_REFERENCE_RE = re.compile(r"^phase33-result-[0-9a-f]{64}$")
_CONSUMPTION_REFERENCE_RE = re.compile(r"^phase33-consume-[0-9a-f]{64}$")

_DECISION_CONSUMED = "AUTHORITY_REPORTED_CONSUMED"
_DECISION_BLOCKED = "AUTHORITY_REPORTED_BLOCKED"
_DECISION_INDETERMINATE = "INDETERMINATE"
_INDETERMINATE_AUTHORITY_REPORTED = "AUTHORITY_REPORTED_INDETERMINATE"

_VERIFIED = "LOCAL_DURABLE_CONSUMPTION_RECORD_VERIFIED"
_VERIFY_INDETERMINATE = "INDETERMINATE"
_VERIFY_REASONS = frozenset(
    {
        "LEDGER_READ_ERROR",
        "LEDGER_SCHEMA_MISMATCH",
        "SQLITE_DURABILITY_PROFILE_MISMATCH",
        "BACKEND_IDENTITY_MISMATCH",
        "LEDGER_RECORD_NOT_FOUND",
        "LEDGER_RECORD_BINDING_MISMATCH",
        "LEDGER_RECORD_FINGERPRINT_MISMATCH",
        "LEDGER_STATE_AMBIGUOUS",
    }
)

_ROW_INVALID = object()


def _raise(reason: str) -> None:
    raise WatchlistOrderAuthorizationDurableAuthorityError(reason)


def _is_exact_bool(value: object, expected: bool | None = None) -> bool:
    return type(value) is bool and (expected is None or value is expected)


def _is_config_reference(value: object) -> bool:
    if type(value) is not str:
        return False
    if not 1 <= len(value) <= 128:
        return False
    if value != value.strip() or not value:
        return False
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        return False
    try:
        value.encode("utf-8", "strict")
    except UnicodeEncodeError:
        return False
    return True


def _is_claim_member(value: object) -> bool:
    if type(value) is not str or not value or not value.strip():
        return False
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        return False
    try:
        value.encode("utf-8", "strict")
    except UnicodeEncodeError:
        return False
    return True


def _is_exact_opaque_reference(value: object) -> bool:
    return _is_config_reference(value)


def _is_binding_reference(value: object) -> bool:
    if type(value) is not str or not 1 <= len(value) <= 128 or not value.strip():
        return False
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        return False
    try:
        value.encode("utf-8", "strict")
    except UnicodeEncodeError:
        return False
    return True


def _is_lower_hex_64(value: object) -> bool:
    return type(value) is str and _LOWER_HEX_64.fullmatch(value) is not None


def _is_exact_tuple_of_claim_members(value: object, length: int) -> bool:
    return (
        type(value) is tuple
        and len(value) == length
        and all(_is_claim_member(item) for item in value)
    )


def _blob_literal(value: str) -> str:
    if type(value) is not str:
        raise ValueError("non-exact-str")
    raw = value.encode("utf-8", "strict")
    return "X'" + raw.hex().upper() + "'"


def _integer_literal(value: int) -> str:
    if type(value) is not int or isinstance(value, bool):
        raise ValueError("non-exact-int")
    if value < -9223372036854775808 or value > 9223372036854775807:
        raise ValueError("integer-out-of-range")
    text = str(value)
    if text.startswith("+"):
        raise ValueError("noncanonical-integer")
    return text


def _canonical_sha256(envelope: dict[str, object]) -> str:
    canonical = json.dumps(
        envelope,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _decode_blob(value: object) -> str:
    if type(value) is not bytes:
        raise ValueError("not-bytes")
    return value.decode("utf-8", "strict")


def _decode_nullable_blob(value: object) -> str | None:
    if value is None:
        return None
    return _decode_blob(value)


def _connection_open(connection: sqlite3.Connection) -> bool:
    try:
        connection.total_changes
    except sqlite3.Error:
        return False
    return True


def _file_backed_main(connection: sqlite3.Connection) -> bool:
    try:
        rows = connection.execute("PRAGMA database_list").fetchall()
    except sqlite3.Error:
        return False
    main_rows = []
    for row in rows:
        if type(row) is not tuple or len(row) != 3:
            return False
        seq, name, path = row
        if type(seq) is not int or isinstance(seq, bool):
            return False
        if type(name) is not str or type(path) is not str:
            return False
        if name == "main":
            main_rows.append(row)
    return len(main_rows) == 1 and bool(main_rows[0][2])


def _connection_surface_exact(
    connection: sqlite3.Connection,
    *,
    require_in_transaction: bool,
) -> bool:
    try:
        if connection.autocommit is not True:
            return False
        if connection.isolation_level is not None:
            return False
        if connection.row_factory is not None:
            return False
        if connection.text_factory is not str:
            return False
        if connection.in_transaction is not require_in_transaction:
            return False
        row = connection.execute("PRAGMA busy_timeout").fetchone()
    except sqlite3.Error:
        return False
    return (
        type(row) is tuple
        and len(row) == 1
        and type(row[0]) is int
        and not isinstance(row[0], bool)
        and row[0] == 0
    )


def _durability_exact(connection: sqlite3.Connection) -> bool:
    journal = connection.execute("PRAGMA main.journal_mode").fetchone()
    synchronous = connection.execute("PRAGMA main.synchronous").fetchone()
    return (
        type(journal) is tuple
        and len(journal) == 1
        and type(journal[0]) is str
        and journal[0] == _JOURNAL_MODE
        and type(synchronous) is tuple
        and len(synchronous) == 1
        and type(synchronous[0]) is int
        and not isinstance(synchronous[0], bool)
        and synchronous[0] == _SYNCHRONOUS_LEVEL
    )


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    literal = _blob_literal(table_name)
    sql = (
        "SELECT CAST(type AS BLOB),CAST(name AS BLOB),CAST(tbl_name AS BLOB),CAST(sql AS BLOB) "
        "FROM main.sqlite_schema WHERE CAST(name AS BLOB)=" + literal
    )
    rows = connection.execute(sql).fetchall()
    for row in rows:
        if type(row) is not tuple or len(row) != 4:
            return False
        try:
            row_type = _decode_blob(row[0])
            name = _decode_blob(row[1])
            table = _decode_blob(row[2])
        except (ValueError, UnicodeDecodeError):
            return False
        if row_type == "table" and name == table_name and table == table_name:
            return True
    return False


def _stored_ddl(connection: sqlite3.Connection, table_name: str) -> str | None:
    literal = _blob_literal(table_name)
    sql = (
        "SELECT CAST(sql AS BLOB) FROM main.sqlite_schema "
        "WHERE CAST(type AS BLOB)=X'7461626C65' AND CAST(name AS BLOB)=" + literal
    )
    rows = connection.execute(sql).fetchall()
    if len(rows) != 1 or type(rows[0]) is not tuple or len(rows[0]) != 1:
        return None
    try:
        return _decode_nullable_blob(rows[0][0])
    except (ValueError, UnicodeDecodeError):
        return None


def _table_list_exact(
    connection: sqlite3.Connection,
    table_name: str,
    *,
    ncol: int,
) -> bool:
    sql = "PRAGMA main.table_list('" + table_name + "')"
    rows = connection.execute(sql).fetchall()
    if len(rows) != 1:
        return False
    row = rows[0]
    return (
        type(row) is tuple
        and len(row) >= 6
        and row[0] == "main"
        and row[1] == table_name
        and row[2] == "table"
        and type(row[3]) is int
        and row[3] == ncol
        and type(row[4]) is int
        and row[4] == 0
        and type(row[5]) is int
        and row[5] == 1
    )


def _table_xinfo_exact(
    connection: sqlite3.Connection,
    table_name: str,
    expected: tuple[tuple[str, str, int, int], ...],
) -> bool:
    rows = connection.execute("PRAGMA main.table_xinfo('" + table_name + "')").fetchall()
    if len(rows) != len(expected):
        return False
    for ordinal, (row, contract) in enumerate(zip(rows, expected)):
        if type(row) is not tuple or len(row) != 7:
            return False
        cid, name, declared_type, notnull, default, pk, hidden = row
        exp_name, exp_type, exp_notnull, exp_pk = contract
        if (
            type(cid) is not int
            or cid != ordinal
            or type(name) is not str
            or name != exp_name
            or type(declared_type) is not str
            or declared_type != exp_type
            or type(notnull) is not int
            or notnull != exp_notnull
            or default is not None
            or type(pk) is not int
            or pk != exp_pk
            or type(hidden) is not int
            or hidden != 0
        ):
            return False
    return True


_META_XINFO = (
    ("schema_key", "BLOB", 1, 1),
    ("schema_value", "BLOB", 1, 0),
)
_CONSUMPTION_COLUMNS = (
    "backend_instance_reference",
    "authorization_authority_reference",
    "authorization_evidence_snapshot_id",
    "submission_attempt_reference",
    "send_authorization_reference",
    "claim_fingerprint",
    "authority_approval_reference",
    "authority_conformance_reference",
    "authority_result_reference",
    "consumption_reference",
    "sqlite_journal_mode",
    "sqlite_synchronous_level",
    "record_fingerprint",
)
_CONSUMPTION_XINFO = tuple(
    (name, "INTEGER" if name == "sqlite_synchronous_level" else "BLOB", 1, 0)
    for name in _CONSUMPTION_COLUMNS
)


def _indexes_exact(
    connection: sqlite3.Connection,
    table_name: str,
    expected_names: frozenset[str],
) -> bool:
    rows = connection.execute("PRAGMA main.index_list('" + table_name + "')").fetchall()
    if len(rows) != len(expected_names):
        return False
    actual_names: set[str] = set()
    for row in rows:
        if type(row) is not tuple or len(row) < 5:
            return False
        seq, name, unique, origin, partial = row[:5]
        if (
            type(seq) is not int
            or type(name) is not str
            or name not in expected_names
            or type(unique) is not int
            or unique != 1
            or origin not in {"u", "pk"}
            or type(partial) is not int
            or partial != 0
        ):
            return False
        if table_name == _META_TABLE and origin != "pk":
            return False
        if table_name == _CONSUMPTION_TABLE and origin != "u":
            return False
        actual_names.add(name)
    if actual_names != set(expected_names):
        return False

    for name in sorted(actual_names):
        if name not in _ALLOWED_AUTOINDEXES:
            return False
        escaped = name.replace("'", "''")
        xrows = connection.execute("PRAGMA main.index_xinfo('" + escaped + "')").fetchall()
        key_rows = []
        for row in xrows:
            if type(row) is not tuple or len(row) < 6:
                return False
            seqno, cid, column_name, desc, coll, key = row[:6]
            if type(key) is not int:
                return False
            if key == 1:
                if (
                    type(seqno) is not int
                    or type(cid) is not int
                    or cid < 0
                    or type(column_name) is not str
                    or type(desc) is not int
                    or desc != 0
                    or coll != "BINARY"
                ):
                    return False
                key_rows.append((seqno, column_name))
            elif key != 0:
                return False
        key_rows.sort()
        if tuple(column for _, column in key_rows) != _EXPECTED_AUTOINDEX_KEYS[name]:
            return False
    return True


def _foreign_keys_empty(connection: sqlite3.Connection, table_name: str) -> bool:
    return connection.execute("PRAGMA main.foreign_key_list('" + table_name + "')").fetchall() == []


def _no_disallowed_schema_objects(connection: sqlite3.Connection) -> bool:
    sql = (
        "SELECT CAST(type AS BLOB),CAST(name AS BLOB),CAST(tbl_name AS BLOB),CAST(sql AS BLOB) "
        "FROM main.sqlite_schema"
    )
    rows = connection.execute(sql).fetchall()
    target_tables = {_META_TABLE, _CONSUMPTION_TABLE}
    for row in rows:
        if type(row) is not tuple or len(row) != 4:
            return False
        try:
            row_type = _decode_blob(row[0])
            name = _decode_blob(row[1])
            table = _decode_blob(row[2])
            statement = _decode_nullable_blob(row[3])
        except (ValueError, UnicodeDecodeError):
            return False
        if row_type == "trigger" and table in target_tables:
            return False
        if row_type == "view" and name.startswith("kiwoom_order_authorization_"):
            return False
        if table in target_tables and row_type == "index":
            if name not in _ALLOWED_AUTOINDEXES or statement is not None:
                return False

    # TEMP triggers can legally target a main-schema table.  They must be
    # rejected too; TEMP shadow tables themselves remain allowed because all
    # Phase33 authority-critical access is explicitly main-qualified.
    temp_rows = connection.execute(
        "SELECT CAST(type AS BLOB),CAST(tbl_name AS BLOB) FROM temp.sqlite_schema"
    ).fetchall()
    for row in temp_rows:
        if type(row) is not tuple or len(row) != 2:
            return False
        try:
            row_type = _decode_blob(row[0])
            table = _decode_blob(row[1])
        except (ValueError, UnicodeDecodeError):
            return False
        if row_type == "trigger" and table in target_tables:
            return False
    return True


def _metadata_exact(connection: sqlite3.Connection) -> bool:
    rows = connection.execute(
        "SELECT CAST(schema_key AS BLOB),CAST(schema_value AS BLOB) "
        "FROM main.kiwoom_order_authorization_meta"
    ).fetchall()
    if len(rows) != 3:
        return False
    actual: dict[str, str] = {}
    for row in rows:
        if type(row) is not tuple or len(row) != 2:
            return False
        try:
            key = _decode_blob(row[0])
            value = _decode_blob(row[1])
        except (ValueError, UnicodeDecodeError):
            return False
        if key in actual:
            return False
        actual[key] = value
    return actual == _META_VALUES


def _single_table_exact(connection: sqlite3.Connection, table_name: str) -> bool:
    if table_name == _META_TABLE:
        stored = _stored_ddl(connection, table_name)
        if stored != _META_STORED_DDL:
            return False
        if len(stored.encode("utf-8")) != 116:
            return False
        if hashlib.sha256(stored.encode("utf-8")).hexdigest().upper() != _META_STORED_DDL_SHA256:
            return False
        return (
            _table_list_exact(connection, table_name, ncol=2)
            and _table_xinfo_exact(connection, table_name, _META_XINFO)
            and _indexes_exact(connection, table_name, _META_AUTOINDEX)
            and _foreign_keys_empty(connection, table_name)
        )
    if table_name == _CONSUMPTION_TABLE:
        stored = _stored_ddl(connection, table_name)
        if stored != _CONSUMPTION_STORED_DDL:
            return False
        if len(stored.encode("utf-8")) != 888:
            return False
        if hashlib.sha256(stored.encode("utf-8")).hexdigest().upper() != _CONSUMPTION_STORED_DDL_SHA256:
            return False
        return (
            _table_list_exact(connection, table_name, ncol=13)
            and _table_xinfo_exact(connection, table_name, _CONSUMPTION_XINFO)
            and _indexes_exact(connection, table_name, _CONSUMPTION_AUTOINDEX)
            and _foreign_keys_empty(connection, table_name)
        )
    return False


def _schema_exact(connection: sqlite3.Connection) -> bool:
    if not _table_exists(connection, _META_TABLE) or not _table_exists(connection, _CONSUMPTION_TABLE):
        return False
    return (
        _single_table_exact(connection, _META_TABLE)
        and _single_table_exact(connection, _CONSUMPTION_TABLE)
        and _metadata_exact(connection)
        and _no_disallowed_schema_objects(connection)
    )


def _partial_existing_schema_valid(connection: sqlite3.Connection) -> tuple[bool, bool]:
    meta_exists = _table_exists(connection, _META_TABLE)
    consumption_exists = _table_exists(connection, _CONSUMPTION_TABLE)
    if meta_exists and (not _single_table_exact(connection, _META_TABLE) or not _metadata_exact(connection)):
        _raise("LEDGER_SCHEMA_INVALID")
    if consumption_exists and not _single_table_exact(connection, _CONSUMPTION_TABLE):
        _raise("LEDGER_SCHEMA_INVALID")
    if (meta_exists or consumption_exists) and not _no_disallowed_schema_objects(connection):
        _raise("LEDGER_SCHEMA_INVALID")
    return meta_exists, consumption_exists


def _validate_connection_for_entry(connection: object) -> sqlite3.Connection:
    if type(connection) is not sqlite3.Connection:
        _raise("AUTHORITY_CONNECTION_INVALID")
    if not _connection_open(connection):
        _raise("AUTHORITY_CONNECTION_INVALID")
    if connection.row_factory is not None or connection.text_factory is not str:
        _raise("AUTHORITY_CONNECTION_TRANSACTION_MODE_INVALID")
    if not _file_backed_main(connection):
        _raise("AUTHORITY_CONNECTION_INVALID")
    try:
        active = connection.in_transaction
    except sqlite3.Error:
        _raise("AUTHORITY_CONNECTION_INVALID")
    if active is True:
        _raise("AUTHORITY_CONNECTION_TRANSACTION_ACTIVE")
    if not _connection_surface_exact(connection, require_in_transaction=False):
        _raise("AUTHORITY_CONNECTION_TRANSACTION_MODE_INVALID")
    return connection


def _require_durability(connection: sqlite3.Connection) -> None:
    try:
        valid = _durability_exact(connection)
    except sqlite3.Error:
        valid = False
    if not valid:
        _raise("SQLITE_DURABILITY_PROFILE_INVALID")


def _require_schema(connection: sqlite3.Connection) -> None:
    try:
        valid = _schema_exact(connection)
    except sqlite3.Error:
        valid = False
    if not valid:
        _raise("LEDGER_SCHEMA_INVALID")


def _cleanup_rollback_once(connection: sqlite3.Connection) -> None:
    try:
        if connection.in_transaction:
            try:
                connection.execute("ROLLBACK")
            except BaseException:
                pass
    except BaseException:
        pass


def initialize_demo_watchlist_order_authorization_durable_ledger(
    connection: sqlite3.Connection,
) -> None:
    connection = _validate_connection_for_entry(connection)
    _require_durability(connection)
    meta_exists, consumption_exists = _partial_existing_schema_valid(connection)

    began = False
    try:
        connection.execute("BEGIN IMMEDIATE")
        began = True
        if connection.in_transaction is not True:
            _raise("AUTHORITY_CONNECTION_TRANSACTION_MODE_INVALID")

        if not meta_exists:
            connection.execute(_META_CREATE_SQL)
            values_sql = ",".join(
                "(" + _blob_literal(key) + "," + _blob_literal(value) + ")"
                for key, value in (
                    ("schema_id", _SCHEMA_ID),
                    ("transaction_profile_id", _TRANSACTION_PROFILE_ID),
                    ("durability_profile_id", _DURABILITY_PROFILE_ID),
                )
            )
            connection.execute(
                "INSERT INTO main.kiwoom_order_authorization_meta(schema_key,schema_value) VALUES "
                + values_sql
            )
        if not consumption_exists:
            connection.execute(_CONSUMPTION_CREATE_SQL)

        if not _connection_surface_exact(connection, require_in_transaction=True):
            _raise("AUTHORITY_CONNECTION_TRANSACTION_MODE_INVALID")
        if not _durability_exact(connection):
            _raise("SQLITE_DURABILITY_PROFILE_INVALID")
        if not _schema_exact(connection):
            _raise("LEDGER_SCHEMA_INVALID")

        connection.execute("COMMIT")
        if connection.in_transaction:
            _raise("AUTHORITY_CONNECTION_TRANSACTION_MODE_INVALID")
    except sqlite3.Error:
        _cleanup_rollback_once(connection)
        raise
    except BaseException:
        _cleanup_rollback_once(connection)
        raise


def _record_fingerprint_values(
    *,
    backend_instance_reference: str,
    authorization_authority_reference: str,
    authorization_evidence_snapshot_id: str,
    submission_attempt_reference: str,
    send_authorization_reference: str,
    claim_fingerprint: str,
    authority_approval_reference: str,
    authority_conformance_reference: str,
    authority_result_reference: str,
    consumption_reference: str,
    sqlite_journal_mode: str,
    sqlite_synchronous_level: int,
) -> str:
    envelope = {
        "domain": "phase33-durable-record-v1",
        "schema_id": _SCHEMA_ID,
        "transaction_profile_id": _TRANSACTION_PROFILE_ID,
        "durability_profile_id": _DURABILITY_PROFILE_ID,
        "backend_instance_reference": backend_instance_reference,
        "authorization_authority_reference": authorization_authority_reference,
        "authorization_evidence_snapshot_id": authorization_evidence_snapshot_id,
        "submission_attempt_reference": submission_attempt_reference,
        "send_authorization_reference": send_authorization_reference,
        "claim_fingerprint": claim_fingerprint,
        "authority_approval_reference": authority_approval_reference,
        "authority_conformance_reference": authority_conformance_reference,
        "authority_result_reference": authority_result_reference,
        "consumption_reference": consumption_reference,
        "sqlite_journal_mode": sqlite_journal_mode,
        "sqlite_synchronous_level": sqlite_synchronous_level,
    }
    return _canonical_sha256(envelope)


def _authority_result_reference(
    *,
    backend_instance_reference: str,
    authorization_claim_identity: tuple[str, str, str, str],
    authorization_replay_guard: tuple[str, str],
    claim_fingerprint: str,
    authority_approval_reference: str,
    authority_conformance_reference: str,
) -> str:
    envelope = {
        "domain": "phase33-authority-result-v1",
        "schema_id": _SCHEMA_ID,
        "transaction_profile_id": _TRANSACTION_PROFILE_ID,
        "durability_profile_id": _DURABILITY_PROFILE_ID,
        "backend_instance_reference": backend_instance_reference,
        "authorization_claim_identity": authorization_claim_identity,
        "authorization_replay_guard": authorization_replay_guard,
        "claim_fingerprint": claim_fingerprint,
        "authority_approval_reference": authority_approval_reference,
        "authority_conformance_reference": authority_conformance_reference,
    }
    return "phase33-result-" + _canonical_sha256(envelope)


def _consumption_reference(
    *,
    backend_instance_reference: str,
    authorization_claim_identity: tuple[str, str, str, str],
    authorization_replay_guard: tuple[str, str],
    claim_fingerprint: str,
    authority_approval_reference: str,
    authority_conformance_reference: str,
    authority_result_reference: str,
) -> str:
    envelope = {
        "domain": "phase33-consumption-v1",
        "schema_id": _SCHEMA_ID,
        "transaction_profile_id": _TRANSACTION_PROFILE_ID,
        "durability_profile_id": _DURABILITY_PROFILE_ID,
        "backend_instance_reference": backend_instance_reference,
        "authorization_claim_identity": authorization_claim_identity,
        "authorization_replay_guard": authorization_replay_guard,
        "claim_fingerprint": claim_fingerprint,
        "authority_approval_reference": authority_approval_reference,
        "authority_conformance_reference": authority_conformance_reference,
        "authority_result_reference": authority_result_reference,
    }
    return "phase33-consume-" + _canonical_sha256(envelope)


def _phase32_result(
    *,
    authorization_claim_identity: tuple[str, str, str, str],
    authorization_replay_guard: tuple[str, str],
    claim_fingerprint: str,
    asserted_authority_approval_reference: str,
    asserted_authority_conformance_reference: str,
    authority_result_reference: str,
    decision: str,
    block_reason: str | None,
    indeterminate_reason: str | None,
    consumption_reference: str | None,
    authority_reported_authorization_consumption_committed: bool | None,
    authority_reported_replay_guard_consumption_committed: bool | None,
    commit_state_known: bool,
) -> KiwoomOrderAuthorizationAuthorityReportedResult:
    return KiwoomOrderAuthorizationAuthorityReportedResult(
        authorization_claim_identity=authorization_claim_identity,
        authorization_replay_guard=authorization_replay_guard,
        claim_fingerprint=claim_fingerprint,
        asserted_authority_approval_reference=asserted_authority_approval_reference,
        asserted_authority_conformance_reference=asserted_authority_conformance_reference,
        authority_result_reference=authority_result_reference,
        decision=decision,
        block_reason=block_reason,
        indeterminate_reason=indeterminate_reason,
        consumption_reference=consumption_reference,
        authority_reported_authorization_consumption_committed=authority_reported_authorization_consumption_committed,
        authority_reported_replay_guard_consumption_committed=authority_reported_replay_guard_consumption_committed,
        commit_state_known=commit_state_known,
    )


def _indeterminate_authority_result(
    *,
    authorization_claim_identity: tuple[str, str, str, str],
    authorization_replay_guard: tuple[str, str],
    claim_fingerprint: str,
    asserted_authority_approval_reference: str,
    asserted_authority_conformance_reference: str,
    authority_result_reference: str,
) -> KiwoomOrderAuthorizationAuthorityReportedResult:
    return _phase32_result(
        authorization_claim_identity=authorization_claim_identity,
        authorization_replay_guard=authorization_replay_guard,
        claim_fingerprint=claim_fingerprint,
        asserted_authority_approval_reference=asserted_authority_approval_reference,
        asserted_authority_conformance_reference=asserted_authority_conformance_reference,
        authority_result_reference=authority_result_reference,
        decision=_DECISION_INDETERMINATE,
        block_reason=None,
        indeterminate_reason=_INDETERMINATE_AUTHORITY_REPORTED,
        consumption_reference=None,
        authority_reported_authorization_consumption_committed=None,
        authority_reported_replay_guard_consumption_committed=None,
        commit_state_known=False,
    )


def _row_select_columns() -> str:
    parts = []
    for name in _CONSUMPTION_COLUMNS:
        if name == "sqlite_synchronous_level":
            parts.append("CAST(" + name + " AS INTEGER)")
        else:
            parts.append("CAST(" + name + " AS BLOB)")
    return ",".join(parts)


def _normalize_record_row(row: object) -> KiwoomOrderAuthorizationDurableLedgerRecord | object:
    if type(row) is not tuple or len(row) != 13:
        return _ROW_INVALID
    try:
        decoded = []
        for index, value in enumerate(row):
            if index == 11:
                if type(value) is not int or isinstance(value, bool):
                    return _ROW_INVALID
                decoded.append(value)
            else:
                decoded.append(_decode_blob(value))
    except (ValueError, UnicodeDecodeError):
        return _ROW_INVALID
    return KiwoomOrderAuthorizationDurableLedgerRecord(*decoded)


def _lookup_claim(
    connection: sqlite3.Connection,
    claim: tuple[str, str, str, str],
) -> KiwoomOrderAuthorizationDurableLedgerRecord | object | None:
    sql = (
        "SELECT " + _row_select_columns() + " FROM main.kiwoom_order_authorization_consumption WHERE "
        "authorization_authority_reference=" + _blob_literal(claim[0])
        + " AND authorization_evidence_snapshot_id=" + _blob_literal(claim[1])
        + " AND submission_attempt_reference=" + _blob_literal(claim[2])
        + " AND send_authorization_reference=" + _blob_literal(claim[3])
    )
    rows = connection.execute(sql).fetchall()
    if len(rows) == 0:
        return None
    if len(rows) != 1:
        return _ROW_INVALID
    return _normalize_record_row(rows[0])


def _lookup_replay(
    connection: sqlite3.Connection,
    replay: tuple[str, str],
) -> KiwoomOrderAuthorizationDurableLedgerRecord | object | None:
    sql = (
        "SELECT " + _row_select_columns() + " FROM main.kiwoom_order_authorization_consumption WHERE "
        "authorization_authority_reference=" + _blob_literal(replay[0])
        + " AND send_authorization_reference=" + _blob_literal(replay[1])
    )
    rows = connection.execute(sql).fetchall()
    if len(rows) == 0:
        return None
    if len(rows) != 1:
        return _ROW_INVALID
    return _normalize_record_row(rows[0])


def _lookup_result_reference(
    connection: sqlite3.Connection,
    value: str,
) -> KiwoomOrderAuthorizationDurableLedgerRecord | object | None:
    sql = (
        "SELECT " + _row_select_columns() + " FROM main.kiwoom_order_authorization_consumption WHERE "
        "authority_result_reference=" + _blob_literal(value)
    )
    rows = connection.execute(sql).fetchall()
    if len(rows) == 0:
        return None
    if len(rows) != 1:
        return _ROW_INVALID
    return _normalize_record_row(rows[0])


def _lookup_consumption_reference(
    connection: sqlite3.Connection,
    value: str,
) -> KiwoomOrderAuthorizationDurableLedgerRecord | object | None:
    sql = (
        "SELECT " + _row_select_columns() + " FROM main.kiwoom_order_authorization_consumption WHERE "
        "consumption_reference=" + _blob_literal(value)
    )
    rows = connection.execute(sql).fetchall()
    if len(rows) == 0:
        return None
    if len(rows) != 1:
        return _ROW_INVALID
    return _normalize_record_row(rows[0])


def _record_fingerprint_matches(record: KiwoomOrderAuthorizationDurableLedgerRecord) -> bool:
    expected = _record_fingerprint_values(
        backend_instance_reference=record.backend_instance_reference,
        authorization_authority_reference=record.authorization_authority_reference,
        authorization_evidence_snapshot_id=record.authorization_evidence_snapshot_id,
        submission_attempt_reference=record.submission_attempt_reference,
        send_authorization_reference=record.send_authorization_reference,
        claim_fingerprint=record.claim_fingerprint,
        authority_approval_reference=record.authority_approval_reference,
        authority_conformance_reference=record.authority_conformance_reference,
        authority_result_reference=record.authority_result_reference,
        consumption_reference=record.consumption_reference,
        sqlite_journal_mode=record.sqlite_journal_mode,
        sqlite_synchronous_level=record.sqlite_synchronous_level,
    )
    return record.record_fingerprint == expected


def _record_references_self_bind(record: KiwoomOrderAuthorizationDurableLedgerRecord) -> bool:
    claim = (
        record.authorization_authority_reference,
        record.authorization_evidence_snapshot_id,
        record.submission_attempt_reference,
        record.send_authorization_reference,
    )
    replay = (
        record.authorization_authority_reference,
        record.send_authorization_reference,
    )
    expected_result = _authority_result_reference(
        backend_instance_reference=record.backend_instance_reference,
        authorization_claim_identity=claim,
        authorization_replay_guard=replay,
        claim_fingerprint=record.claim_fingerprint,
        authority_approval_reference=record.authority_approval_reference,
        authority_conformance_reference=record.authority_conformance_reference,
    )
    if record.authority_result_reference != expected_result:
        return False
    expected_consumption = _consumption_reference(
        backend_instance_reference=record.backend_instance_reference,
        authorization_claim_identity=claim,
        authorization_replay_guard=replay,
        claim_fingerprint=record.claim_fingerprint,
        authority_approval_reference=record.authority_approval_reference,
        authority_conformance_reference=record.authority_conformance_reference,
        authority_result_reference=expected_result,
    )
    return record.consumption_reference == expected_consumption


def _record_self_integrity(record: KiwoomOrderAuthorizationDurableLedgerRecord) -> bool:
    return (
        _record_fingerprint_matches(record)
        and _record_references_self_bind(record)
        and record.sqlite_journal_mode == _JOURNAL_MODE
        and record.sqlite_synchronous_level == _SYNCHRONOUS_LEVEL
    )


def _commit_or_indeterminate(
    connection: sqlite3.Connection,
    *,
    claim: tuple[str, str, str, str],
    replay: tuple[str, str],
    claim_fingerprint: str,
    approval: str,
    conformance: str,
    result_reference: str,
) -> bool:
    try:
        connection.execute("COMMIT")
    except sqlite3.Error:
        _cleanup_rollback_once(connection)
        return False
    if connection.in_transaction:
        _cleanup_rollback_once(connection)
        return False
    return True


class KiwoomOrderAuthorizationSQLiteAuthority:
    def __init__(
        self,
        connection: sqlite3.Connection,
        config: KiwoomOrderAuthorizationDurableAuthorityConfig,
    ) -> None:
        self.connection = connection
        self.config = config

    def check_and_consume(
        self,
        *,
        authorization_claim_identity: tuple[str, str, str, str],
        authorization_replay_guard: tuple[str, str],
        claim_fingerprint: str,
        asserted_authority_approval_reference: str,
        asserted_authority_conformance_reference: str,
    ) -> KiwoomOrderAuthorizationAuthorityReportedResult:
        if type(self.config) is not KiwoomOrderAuthorizationDurableAuthorityConfig or not all(
            _is_config_reference(value)
            for value in (
                self.config.backend_instance_reference,
                self.config.authorization_authority_reference,
                self.config.authority_approval_reference,
                self.config.authority_conformance_reference,
            )
        ):
            _raise("AUTHORITY_CONFIG_INVALID")
        if not _is_exact_tuple_of_claim_members(authorization_claim_identity, 4):
            _raise("REFERENCE_OR_FINGERPRINT_INVALID")
        if not _is_exact_tuple_of_claim_members(authorization_replay_guard, 2):
            _raise("REFERENCE_OR_FINGERPRINT_INVALID")
        if not _is_lower_hex_64(claim_fingerprint):
            _raise("REFERENCE_OR_FINGERPRINT_INVALID")
        if authorization_replay_guard != (
            authorization_claim_identity[0],
            authorization_claim_identity[3],
        ):
            _raise("REFERENCE_OR_FINGERPRINT_INVALID")
        if (
            authorization_claim_identity[0] != self.config.authorization_authority_reference
            or asserted_authority_approval_reference != self.config.authority_approval_reference
            or asserted_authority_conformance_reference != self.config.authority_conformance_reference
            or not _is_config_reference(asserted_authority_approval_reference)
            or not _is_config_reference(asserted_authority_conformance_reference)
        ):
            _raise("REFERENCE_OR_FINGERPRINT_INVALID")
        try:
            for value in (
                *authorization_claim_identity,
                *authorization_replay_guard,
                claim_fingerprint,
                asserted_authority_approval_reference,
                asserted_authority_conformance_reference,
                self.config.backend_instance_reference,
            ):
                _blob_literal(value)
        except (UnicodeEncodeError, ValueError):
            _raise("REFERENCE_OR_FINGERPRINT_INVALID")

        connection = _validate_connection_for_entry(self.connection)
        _require_durability(connection)
        _require_schema(connection)

        result_reference = _authority_result_reference(
            backend_instance_reference=self.config.backend_instance_reference,
            authorization_claim_identity=authorization_claim_identity,
            authorization_replay_guard=authorization_replay_guard,
            claim_fingerprint=claim_fingerprint,
            authority_approval_reference=asserted_authority_approval_reference,
            authority_conformance_reference=asserted_authority_conformance_reference,
        )
        indeterminate = lambda: _indeterminate_authority_result(
            authorization_claim_identity=authorization_claim_identity,
            authorization_replay_guard=authorization_replay_guard,
            claim_fingerprint=claim_fingerprint,
            asserted_authority_approval_reference=asserted_authority_approval_reference,
            asserted_authority_conformance_reference=asserted_authority_conformance_reference,
            authority_result_reference=result_reference,
        )

        began = False
        try:
            try:
                connection.execute("BEGIN IMMEDIATE")
                began = True
            except sqlite3.Error:
                if connection.in_transaction:
                    _cleanup_rollback_once(connection)
                return indeterminate()

            if connection.in_transaction is not True:
                _cleanup_rollback_once(connection)
                return indeterminate()

            try:
                if not _connection_surface_exact(connection, require_in_transaction=True):
                    _cleanup_rollback_once(connection)
                    return indeterminate()
                if not _durability_exact(connection):
                    _cleanup_rollback_once(connection)
                    return indeterminate()
                if not _schema_exact(connection):
                    _cleanup_rollback_once(connection)
                    return indeterminate()

                claim_row = _lookup_claim(connection, authorization_claim_identity)
                replay_row = _lookup_replay(connection, authorization_replay_guard)
            except sqlite3.Error:
                _cleanup_rollback_once(connection)
                return indeterminate()

            if claim_row is _ROW_INVALID:
                _cleanup_rollback_once(connection)
                return indeterminate()
            if claim_row is not None:
                if not _record_self_integrity(claim_row) or claim_row.claim_fingerprint != claim_fingerprint:
                    _cleanup_rollback_once(connection)
                    return indeterminate()
                if not _commit_or_indeterminate(
                    connection,
                    claim=authorization_claim_identity,
                    replay=authorization_replay_guard,
                    claim_fingerprint=claim_fingerprint,
                    approval=asserted_authority_approval_reference,
                    conformance=asserted_authority_conformance_reference,
                    result_reference=result_reference,
                ):
                    return indeterminate()
                return _phase32_result(
                    authorization_claim_identity=authorization_claim_identity,
                    authorization_replay_guard=authorization_replay_guard,
                    claim_fingerprint=claim_fingerprint,
                    asserted_authority_approval_reference=asserted_authority_approval_reference,
                    asserted_authority_conformance_reference=asserted_authority_conformance_reference,
                    authority_result_reference=claim_row.authority_result_reference,
                    decision=_DECISION_BLOCKED,
                    block_reason="CLAIM_ALREADY_CONSUMED",
                    indeterminate_reason=None,
                    consumption_reference=None,
                    authority_reported_authorization_consumption_committed=False,
                    authority_reported_replay_guard_consumption_committed=False,
                    commit_state_known=True,
                )

            if replay_row is _ROW_INVALID:
                _cleanup_rollback_once(connection)
                return indeterminate()
            if replay_row is not None:
                if not _record_self_integrity(replay_row):
                    _cleanup_rollback_once(connection)
                    return indeterminate()
                if not _commit_or_indeterminate(
                    connection,
                    claim=authorization_claim_identity,
                    replay=authorization_replay_guard,
                    claim_fingerprint=claim_fingerprint,
                    approval=asserted_authority_approval_reference,
                    conformance=asserted_authority_conformance_reference,
                    result_reference=result_reference,
                ):
                    return indeterminate()
                return _phase32_result(
                    authorization_claim_identity=authorization_claim_identity,
                    authorization_replay_guard=authorization_replay_guard,
                    claim_fingerprint=claim_fingerprint,
                    asserted_authority_approval_reference=asserted_authority_approval_reference,
                    asserted_authority_conformance_reference=asserted_authority_conformance_reference,
                    authority_result_reference=replay_row.authority_result_reference,
                    decision=_DECISION_BLOCKED,
                    block_reason="REPLAY_GUARD_ALREADY_CONSUMED",
                    indeterminate_reason=None,
                    consumption_reference=None,
                    authority_reported_authorization_consumption_committed=False,
                    authority_reported_replay_guard_consumption_committed=False,
                    commit_state_known=True,
                )

            try:
                consumption_reference = _consumption_reference(
                    backend_instance_reference=self.config.backend_instance_reference,
                    authorization_claim_identity=authorization_claim_identity,
                    authorization_replay_guard=authorization_replay_guard,
                    claim_fingerprint=claim_fingerprint,
                    authority_approval_reference=asserted_authority_approval_reference,
                    authority_conformance_reference=asserted_authority_conformance_reference,
                    authority_result_reference=result_reference,
                )
                record_fingerprint = _record_fingerprint_values(
                    backend_instance_reference=self.config.backend_instance_reference,
                    authorization_authority_reference=authorization_claim_identity[0],
                    authorization_evidence_snapshot_id=authorization_claim_identity[1],
                    submission_attempt_reference=authorization_claim_identity[2],
                    send_authorization_reference=authorization_claim_identity[3],
                    claim_fingerprint=claim_fingerprint,
                    authority_approval_reference=asserted_authority_approval_reference,
                    authority_conformance_reference=asserted_authority_conformance_reference,
                    authority_result_reference=result_reference,
                    consumption_reference=consumption_reference,
                    sqlite_journal_mode=_JOURNAL_MODE,
                    sqlite_synchronous_level=_SYNCHRONOUS_LEVEL,
                )
                values = (
                    self.config.backend_instance_reference,
                    authorization_claim_identity[0],
                    authorization_claim_identity[1],
                    authorization_claim_identity[2],
                    authorization_claim_identity[3],
                    claim_fingerprint,
                    asserted_authority_approval_reference,
                    asserted_authority_conformance_reference,
                    result_reference,
                    consumption_reference,
                    _JOURNAL_MODE,
                    _integer_literal(_SYNCHRONOUS_LEVEL),
                    record_fingerprint,
                )
                rendered = []
                for index, value in enumerate(values):
                    if index == 11:
                        rendered.append(value)
                    else:
                        rendered.append(_blob_literal(value))
                insert_sql = (
                    "INSERT INTO main.kiwoom_order_authorization_consumption("
                    + ",".join(_CONSUMPTION_COLUMNS)
                    + ") VALUES("
                    + ",".join(rendered)
                    + ")"
                )
            except (UnicodeEncodeError, ValueError, TypeError):
                _cleanup_rollback_once(connection)
                return indeterminate()

            try:
                connection.execute(insert_sql)
            except sqlite3.Error:
                _cleanup_rollback_once(connection)
                return indeterminate()

            if not _commit_or_indeterminate(
                connection,
                claim=authorization_claim_identity,
                replay=authorization_replay_guard,
                claim_fingerprint=claim_fingerprint,
                approval=asserted_authority_approval_reference,
                conformance=asserted_authority_conformance_reference,
                result_reference=result_reference,
            ):
                return indeterminate()

            return _phase32_result(
                authorization_claim_identity=authorization_claim_identity,
                authorization_replay_guard=authorization_replay_guard,
                claim_fingerprint=claim_fingerprint,
                asserted_authority_approval_reference=asserted_authority_approval_reference,
                asserted_authority_conformance_reference=asserted_authority_conformance_reference,
                authority_result_reference=result_reference,
                decision=_DECISION_CONSUMED,
                block_reason=None,
                indeterminate_reason=None,
                consumption_reference=consumption_reference,
                authority_reported_authorization_consumption_committed=True,
                authority_reported_replay_guard_consumption_committed=True,
                commit_state_known=True,
            )
        except sqlite3.Error:
            _cleanup_rollback_once(connection)
            return indeterminate()
        except BaseException:
            _cleanup_rollback_once(connection)
            raise


def _phase31_structure_and_safety_valid(
    source_snapshot: WatchlistOrderAuthorizationConsumptionClaimSnapshot,
) -> bool:
    if type(source_snapshot.context) is not KiwoomOrderAuthorizationConsumptionClaimContext:
        return False
    if type(source_snapshot.authorization_claim_identity) is not tuple or len(source_snapshot.authorization_claim_identity) != 4:
        return False
    if type(source_snapshot.authorization_replay_guard) is not tuple or len(source_snapshot.authorization_replay_guard) != 2:
        return False
    if not all(type(item) is str for item in source_snapshot.authorization_claim_identity):
        return False
    if not all(type(item) is str for item in source_snapshot.authorization_replay_guard):
        return False
    if not _is_lower_hex_64(source_snapshot.claim_fingerprint):
        return False
    expected_flags = (
        (source_snapshot.claim_prepared, True),
        (source_snapshot.authorization_consumption_committed, False),
        (source_snapshot.post_permitted, False),
        (source_snapshot.automatic_retry_permitted, False),
        (source_snapshot.network_performed, False),
        (source_snapshot.order_submitted, False),
    )
    if not all(_is_exact_bool(value, expected) for value, expected in expected_flags):
        return False
    context = source_snapshot.context
    return (
        source_snapshot.authorization_claim_identity
        == (
            context.authorization_authority_reference,
            context.authorization_evidence_snapshot_id,
            context.submission_attempt_reference,
            context.send_authorization_reference,
        )
        and source_snapshot.authorization_replay_guard
        == (context.authorization_authority_reference, context.send_authorization_reference)
    )


def _phase30_binding_valid(
    source_snapshot: WatchlistOrderAuthorizationConsumptionClaimSnapshot,
) -> bool:
    phase30 = source_snapshot.source_snapshot
    if type(phase30) is not WatchlistOrderSendRequestSnapshot:
        return False
    if (
        phase30.environment != "demo"
        or phase30.side != "BUY"
        or phase30.exchange != "KRX"
        or phase30.api_id != "kt10000"
        or phase30.http_method != "POST"
        or phase30.api_path != "/api/dostk/ordr"
    ):
        return False
    body = phase30.body
    if not isinstance(body, Mapping):
        return False
    try:
        if set(body.keys()) != _PROVIDER_BODY_KEYS:
            return False
        if any(type(key) is not str for key in body.keys()):
            return False
        if any(type(value) is not str for value in body.values()):
            return False
    except (AttributeError, TypeError):
        return False
    if body["dmst_stex_tp"] != "KRX" or body["cond_uv"] != "":
        return False
    if body["trde_tp"] == "0":
        if body["ord_uv"] == "":
            return False
    elif body["trde_tp"] == "3":
        if body["ord_uv"] != "":
            return False
    else:
        return False
    if not _is_binding_reference(phase30.source_attempt_ref):
        return False
    if not _is_binding_reference(phase30.authorization_evidence_ref):
        return False
    if not _is_lower_hex_64(phase30.materialization_fingerprint):
        return False
    if not all(
        _is_exact_bool(value, False)
        for value in (
            phase30.transport_allowed,
            phase30.credential_accessed,
            phase30.network_performed,
            phase30.account_accessed,
            phase30.order_submitted,
        )
    ):
        return False
    context = source_snapshot.context
    if context.submission_attempt_reference != phase30.source_attempt_ref:
        return False
    if context.authorization_evidence_snapshot_id != phase30.authorization_evidence_ref:
        return False
    envelope = {
        "environment": phase30.environment,
        "side": phase30.side,
        "exchange": phase30.exchange,
        "api_id": phase30.api_id,
        "http_method": phase30.http_method,
        "api_path": phase30.api_path,
        "body": dict(phase30.body),
        "source_attempt_ref": phase30.source_attempt_ref,
        "authorization_evidence_ref": phase30.authorization_evidence_ref,
    }
    return phase30.materialization_fingerprint == _canonical_sha256(envelope)


def _phase31_claim_fingerprint_valid(
    source_snapshot: WatchlistOrderAuthorizationConsumptionClaimSnapshot,
) -> bool:
    envelope = {
        "materialization_fingerprint": source_snapshot.source_snapshot.materialization_fingerprint,
        "authorization_claim_identity": source_snapshot.authorization_claim_identity,
        "authorization_replay_guard": source_snapshot.authorization_replay_guard,
    }
    return source_snapshot.claim_fingerprint == _canonical_sha256(envelope)


def _phase32_evidence_fingerprint(source: WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot) -> str:
    envelope = {
        "claim_fingerprint": source.source_snapshot.claim_fingerprint,
        "asserted_authority_approval_reference": source.asserted_authority_approval_reference,
        "asserted_authority_conformance_reference": source.asserted_authority_conformance_reference,
        "decision": source.decision,
        "block_reason": source.block_reason,
        "indeterminate_reason": source.indeterminate_reason,
        "authority_result_reference": source.authority_result_reference,
        "consumption_reference": source.consumption_reference,
        "authority_reported_authorization_consumption_committed": source.authority_reported_authorization_consumption_committed,
        "authority_reported_replay_guard_consumption_committed": source.authority_reported_replay_guard_consumption_committed,
        "commit_state_known": source.commit_state_known,
        "consumption_evidence_candidate_ready": source.consumption_evidence_candidate_ready,
        "authority_trust_independently_verified": source.authority_trust_independently_verified,
        "automatic_retry_permitted": source.automatic_retry_permitted,
        "reconciliation_required": source.reconciliation_required,
        "authority_invocation_attempted": source.authority_invocation_attempted,
        "phase32_direct_credential_accessed": source.phase32_direct_credential_accessed,
        "phase32_direct_network_performed": source.phase32_direct_network_performed,
        "phase32_direct_account_accessed": source.phase32_direct_account_accessed,
        "phase32_direct_order_submitted": source.phase32_direct_order_submitted,
    }
    return _canonical_sha256(envelope)


def _phase32_consumed_candidate(source: WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot) -> bool:
    result = source.authority_result
    return (
        source.decision == _DECISION_CONSUMED
        and type(source.decision) is str
        and source.block_reason is None
        and source.indeterminate_reason is None
        and type(result) is KiwoomOrderAuthorizationAuthorityReportedResult
        and _is_exact_opaque_reference(source.authority_result_reference)
        and _is_exact_opaque_reference(source.consumption_reference)
        and _is_exact_bool(source.commit_state_known, True)
        and _is_exact_bool(source.authority_reported_authorization_consumption_committed, True)
        and _is_exact_bool(source.authority_reported_replay_guard_consumption_committed, True)
        and _is_exact_bool(source.consumption_evidence_candidate_ready, True)
        and _is_exact_bool(source.reconciliation_required, False)
        and _is_exact_bool(source.automatic_retry_permitted, False)
        and _is_exact_bool(source.authority_invocation_attempted, True)
        and _is_exact_bool(source.authority_trust_independently_verified, False)
        and _is_exact_bool(source.phase32_direct_credential_accessed, False)
        and _is_exact_bool(source.phase32_direct_network_performed, False)
        and _is_exact_bool(source.phase32_direct_account_accessed, False)
        and _is_exact_bool(source.phase32_direct_order_submitted, False)
    )


def _phase32_binding_valid(source: WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot) -> bool:
    phase31 = source.source_snapshot
    result = source.authority_result
    if type(phase31) is not WatchlistOrderAuthorizationConsumptionClaimSnapshot:
        return False
    if not _phase31_structure_and_safety_valid(phase31):
        return False
    if not _phase30_binding_valid(phase31):
        return False
    if not _phase31_claim_fingerprint_valid(phase31):
        return False
    if type(result) is not KiwoomOrderAuthorizationAuthorityReportedResult:
        return False
    if (
        not _is_exact_opaque_reference(source.asserted_authority_approval_reference)
        or not _is_exact_opaque_reference(source.asserted_authority_conformance_reference)
        or not _is_exact_opaque_reference(source.authority_result_reference)
        or not _is_exact_opaque_reference(source.consumption_reference)
    ):
        return False
    if (
        result.authorization_claim_identity != phase31.authorization_claim_identity
        or result.authorization_replay_guard != phase31.authorization_replay_guard
        or result.claim_fingerprint != phase31.claim_fingerprint
        or result.asserted_authority_approval_reference != source.asserted_authority_approval_reference
        or result.asserted_authority_conformance_reference != source.asserted_authority_conformance_reference
        or result.authority_result_reference != source.authority_result_reference
        or result.decision != source.decision
        or result.block_reason is not None
        or result.indeterminate_reason is not None
        or result.consumption_reference != source.consumption_reference
        or not _is_exact_bool(result.authority_reported_authorization_consumption_committed, True)
        or not _is_exact_bool(result.authority_reported_replay_guard_consumption_committed, True)
        or not _is_exact_bool(result.commit_state_known, True)
    ):
        return False
    if not _is_lower_hex_64(source.evidence_fingerprint):
        return False
    return source.evidence_fingerprint == _phase32_evidence_fingerprint(source)


def _verification_fingerprint(
    *,
    source_evidence_fingerprint: str,
    durable_record_fingerprint: str | None,
    backend_instance_reference: str,
    verification_decision: str,
    indeterminate_reason: str | None,
    concrete_sqlite_authority_identity_verified: bool,
    ledger_schema_verified: bool,
    sqlite_connection_surface_verified: bool,
    sqlite_durability_profile_verified: bool,
    durable_record_present: bool,
    exact_binding_verified: bool,
    durable_consumption_record_verified: bool,
    authority_approval_provenance_verified: bool,
    authority_conformance_provenance_verified: bool,
    provider_send_eligibility_authorized: bool,
    production_authority_use_authorized: bool,
    reconciliation_required: bool,
) -> str:
    envelope = {
        "domain": "phase33-local-durable-verification-v1",
        "source_evidence_fingerprint": source_evidence_fingerprint,
        "durable_record_fingerprint": durable_record_fingerprint,
        "backend_instance_reference": backend_instance_reference,
        "ledger_schema_reference": _LEDGER_SCHEMA_REFERENCE,
        "verification_decision": verification_decision,
        "indeterminate_reason": indeterminate_reason,
        "concrete_sqlite_authority_identity_verified": concrete_sqlite_authority_identity_verified,
        "ledger_schema_verified": ledger_schema_verified,
        "sqlite_connection_surface_verified": sqlite_connection_surface_verified,
        "sqlite_durability_profile_verified": sqlite_durability_profile_verified,
        "durable_record_present": durable_record_present,
        "exact_binding_verified": exact_binding_verified,
        "durable_consumption_record_verified": durable_consumption_record_verified,
        "authority_approval_provenance_verified": authority_approval_provenance_verified,
        "authority_conformance_provenance_verified": authority_conformance_provenance_verified,
        "provider_send_eligibility_authorized": provider_send_eligibility_authorized,
        "production_authority_use_authorized": production_authority_use_authorized,
        "reconciliation_required": reconciliation_required,
    }
    return _canonical_sha256(envelope)


def _verification_indeterminate(
    source: WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot,
    authority: KiwoomOrderAuthorizationSQLiteAuthority,
    reason: str,
) -> WatchlistOrderAuthorizationDurableVerificationSnapshot:
    if reason not in _VERIFY_REASONS:
        raise ValueError("invalid-verification-reason")
    values = dict(
        source_evidence_fingerprint=source.evidence_fingerprint,
        durable_record_fingerprint=None,
        backend_instance_reference=authority.config.backend_instance_reference,
        verification_decision=_VERIFY_INDETERMINATE,
        indeterminate_reason=reason,
        concrete_sqlite_authority_identity_verified=False,
        ledger_schema_verified=False,
        sqlite_connection_surface_verified=False,
        sqlite_durability_profile_verified=False,
        durable_record_present=False,
        exact_binding_verified=False,
        durable_consumption_record_verified=False,
        authority_approval_provenance_verified=False,
        authority_conformance_provenance_verified=False,
        provider_send_eligibility_authorized=False,
        production_authority_use_authorized=False,
        reconciliation_required=True,
    )
    return WatchlistOrderAuthorizationDurableVerificationSnapshot(
        source_snapshot=source,
        durable_record=None,
        backend_instance_reference=authority.config.backend_instance_reference,
        ledger_schema_reference=_LEDGER_SCHEMA_REFERENCE,
        verification_decision=_VERIFY_INDETERMINATE,
        indeterminate_reason=reason,
        concrete_sqlite_authority_identity_verified=False,
        ledger_schema_verified=False,
        sqlite_connection_surface_verified=False,
        sqlite_durability_profile_verified=False,
        durable_record_present=False,
        exact_binding_verified=False,
        durable_consumption_record_verified=False,
        authority_approval_provenance_verified=False,
        authority_conformance_provenance_verified=False,
        provider_send_eligibility_authorized=False,
        production_authority_use_authorized=False,
        reconciliation_required=True,
        verification_fingerprint=_verification_fingerprint(**values),
    )


def _verification_success(
    source: WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot,
    authority: KiwoomOrderAuthorizationSQLiteAuthority,
    record: KiwoomOrderAuthorizationDurableLedgerRecord,
) -> WatchlistOrderAuthorizationDurableVerificationSnapshot:
    values = dict(
        source_evidence_fingerprint=source.evidence_fingerprint,
        durable_record_fingerprint=record.record_fingerprint,
        backend_instance_reference=authority.config.backend_instance_reference,
        verification_decision=_VERIFIED,
        indeterminate_reason=None,
        concrete_sqlite_authority_identity_verified=True,
        ledger_schema_verified=True,
        sqlite_connection_surface_verified=True,
        sqlite_durability_profile_verified=True,
        durable_record_present=True,
        exact_binding_verified=True,
        durable_consumption_record_verified=True,
        authority_approval_provenance_verified=False,
        authority_conformance_provenance_verified=False,
        provider_send_eligibility_authorized=False,
        production_authority_use_authorized=False,
        reconciliation_required=False,
    )
    return WatchlistOrderAuthorizationDurableVerificationSnapshot(
        source_snapshot=source,
        durable_record=record,
        backend_instance_reference=authority.config.backend_instance_reference,
        ledger_schema_reference=_LEDGER_SCHEMA_REFERENCE,
        verification_decision=_VERIFIED,
        indeterminate_reason=None,
        concrete_sqlite_authority_identity_verified=True,
        ledger_schema_verified=True,
        sqlite_connection_surface_verified=True,
        sqlite_durability_profile_verified=True,
        durable_record_present=True,
        exact_binding_verified=True,
        durable_consumption_record_verified=True,
        authority_approval_provenance_verified=False,
        authority_conformance_provenance_verified=False,
        provider_send_eligibility_authorized=False,
        production_authority_use_authorized=False,
        reconciliation_required=False,
        verification_fingerprint=_verification_fingerprint(**values),
    )


def _remaining_record_binding_valid(
    source: WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot,
    authority: KiwoomOrderAuthorizationSQLiteAuthority,
    record: KiwoomOrderAuthorizationDurableLedgerRecord,
) -> bool:
    claim = source.source_snapshot.authorization_claim_identity
    return (
        record.authorization_authority_reference == claim[0]
        and record.authorization_evidence_snapshot_id == claim[1]
        and record.submission_attempt_reference == claim[2]
        and record.send_authorization_reference == claim[3]
        and record.claim_fingerprint == source.source_snapshot.claim_fingerprint
        and record.authority_approval_reference == source.asserted_authority_approval_reference
        and record.authority_conformance_reference == source.asserted_authority_conformance_reference
        and record.authority_result_reference == source.authority_result_reference
        and record.consumption_reference == source.consumption_reference
        and record.authorization_authority_reference == authority.config.authorization_authority_reference
        and record.authority_approval_reference == authority.config.authority_approval_reference
        and record.authority_conformance_reference == authority.config.authority_conformance_reference
        and record.sqlite_journal_mode == _JOURNAL_MODE
        and record.sqlite_synchronous_level == _SYNCHRONOUS_LEVEL
    )


def verify_demo_watchlist_order_authorization_durable_consumption(
    source_snapshot: WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot,
    authority: KiwoomOrderAuthorizationSQLiteAuthority,
) -> WatchlistOrderAuthorizationDurableVerificationSnapshot:
    if type(source_snapshot) is not WatchlistOrderAuthorizationAdapterResultEvidenceSnapshot:
        _raise("SOURCE_SNAPSHOT_TYPE_INVALID")
    if not _phase32_consumed_candidate(source_snapshot):
        _raise("SOURCE_SNAPSHOT_NOT_CONSUMED_CANDIDATE")
    if not _phase32_binding_valid(source_snapshot):
        _raise("SOURCE_SNAPSHOT_BINDING_INVALID")
    if type(authority) is not KiwoomOrderAuthorizationSQLiteAuthority:
        _raise("AUTHORITY_BACKEND_TYPE_INVALID")
    if type(authority.config) is not KiwoomOrderAuthorizationDurableAuthorityConfig or not all(
        _is_config_reference(value)
        for value in (
            authority.config.backend_instance_reference,
            authority.config.authorization_authority_reference,
            authority.config.authority_approval_reference,
            authority.config.authority_conformance_reference,
        )
    ):
        _raise("AUTHORITY_CONFIG_INVALID")
    connection = _validate_connection_for_entry(authority.connection)
    for value in (
        source_snapshot.evidence_fingerprint,
        source_snapshot.authority_result_reference,
        source_snapshot.consumption_reference,
    ):
        try:
            _blob_literal(value)
        except (UnicodeEncodeError, ValueError):
            _raise("REFERENCE_OR_FINGERPRINT_INVALID")
    if not _is_lower_hex_64(source_snapshot.evidence_fingerprint):
        _raise("REFERENCE_OR_FINGERPRINT_INVALID")
    if _RESULT_REFERENCE_RE.fullmatch(source_snapshot.authority_result_reference) is None:
        _raise("REFERENCE_OR_FINGERPRINT_INVALID")
    if _CONSUMPTION_REFERENCE_RE.fullmatch(source_snapshot.consumption_reference) is None:
        _raise("REFERENCE_OR_FINGERPRINT_INVALID")

    began = False
    reason: str | None = None
    record: KiwoomOrderAuthorizationDurableLedgerRecord | None = None
    try:
        try:
            connection.execute("BEGIN")
            began = True
        except sqlite3.Error:
            if connection.in_transaction:
                _cleanup_rollback_once(connection)
            return _verification_indeterminate(source_snapshot, authority, "LEDGER_READ_ERROR")

        if connection.in_transaction is not True:
            _cleanup_rollback_once(connection)
            return _verification_indeterminate(source_snapshot, authority, "LEDGER_READ_ERROR")

        try:
            if not _connection_surface_exact(connection, require_in_transaction=True):
                reason = "LEDGER_READ_ERROR"
            elif not _schema_exact(connection):
                reason = "LEDGER_SCHEMA_MISMATCH"
            elif not _durability_exact(connection):
                reason = "SQLITE_DURABILITY_PROFILE_MISMATCH"
            else:
                by_result = _lookup_result_reference(connection, source_snapshot.authority_result_reference)
                by_consumption = _lookup_consumption_reference(connection, source_snapshot.consumption_reference)
                if by_result is _ROW_INVALID or by_consumption is _ROW_INVALID:
                    reason = "LEDGER_RECORD_BINDING_MISMATCH"
                elif by_result is None and by_consumption is None:
                    reason = "LEDGER_RECORD_NOT_FOUND"
                elif (by_result is None) != (by_consumption is None):
                    reason = "LEDGER_RECORD_BINDING_MISMATCH"
                elif by_result != by_consumption:
                    reason = "LEDGER_STATE_AMBIGUOUS"
                else:
                    record = by_result
                    if type(record) is not KiwoomOrderAuthorizationDurableLedgerRecord:
                        reason = "LEDGER_RECORD_BINDING_MISMATCH"
                    elif not _record_fingerprint_matches(record):
                        reason = "LEDGER_RECORD_FINGERPRINT_MISMATCH"
                    elif not _record_references_self_bind(record):
                        reason = "LEDGER_RECORD_BINDING_MISMATCH"
                    elif record.backend_instance_reference != authority.config.backend_instance_reference:
                        reason = "BACKEND_IDENTITY_MISMATCH"
                    elif not _remaining_record_binding_valid(source_snapshot, authority, record):
                        reason = "LEDGER_RECORD_BINDING_MISMATCH"
        except sqlite3.Error:
            _cleanup_rollback_once(connection)
            return _verification_indeterminate(source_snapshot, authority, "LEDGER_READ_ERROR")

        try:
            connection.execute("COMMIT")
        except sqlite3.Error:
            _cleanup_rollback_once(connection)
            return _verification_indeterminate(source_snapshot, authority, "LEDGER_READ_ERROR")
        if connection.in_transaction:
            _cleanup_rollback_once(connection)
            return _verification_indeterminate(source_snapshot, authority, "LEDGER_READ_ERROR")

        if reason is not None:
            return _verification_indeterminate(source_snapshot, authority, reason)
        if record is None:
            return _verification_indeterminate(source_snapshot, authority, "LEDGER_RECORD_NOT_FOUND")
        return _verification_success(source_snapshot, authority, record)
    except sqlite3.Error:
        _cleanup_rollback_once(connection)
        return _verification_indeterminate(source_snapshot, authority, "LEDGER_READ_ERROR")
    except BaseException:
        _cleanup_rollback_once(connection)
        raise
