"""SQLite database layer for HungryCall web interface."""

import json
import os
import sqlite3
import time
import uuid
from typing import Any

from hungrycall.huckepack_storage import open_connection

DEFAULT_DB_PATH = "hungrycall.db"


def db_path() -> str:
    """Resolve the database path at call time.

    Read on every call, never frozen at import time: a module-level constant
    would ignore any HUNGRYCALL_DB_PATH set after the import — which silently
    sends every write to the default file instead of the configured one.
    """
    return os.environ.get("HUNGRYCALL_DB_PATH", DEFAULT_DB_PATH)


def get_db_connection() -> sqlite3.Connection:
    """Get sqlite3 connection with Row factory.

    Which database that is depends on the server mode: the file above, or the
    in-memory copy the browser sent along. See ``huckepack_storage``.
    """
    conn = open_connection(db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path_override: str | None = None) -> None:
    """Initialize database tables for orders and saved results."""
    target_path = db_path_override or db_path()
    conn = open_connection(target_path)
    cursor = conn.cursor()

    # Create orders table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            mode TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            food_prompt TEXT NOT NULL,
            max_budget_eur REAL,
            delivery_address TEXT,
            reservation_date TEXT,
            reservation_time TEXT,
            party_size INTEGER,
            pickup_time TEXT,
            location_info TEXT,
            dry_run INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'CREATED',
            created_at TEXT NOT NULL
        );
    """)
    order_columns = {
        row[1] for row in cursor.execute("PRAGMA table_info(orders)").fetchall()
    }
    if "order_chain_json" not in order_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN order_chain_json TEXT")

    # Create saved_results table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_results (
            id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            mode TEXT NOT NULL,
            restaurant_id TEXT NOT NULL,
            restaurant_name TEXT NOT NULL,
            masked_phone TEXT NOT NULL,
            callback_number TEXT NOT NULL,
            total_price_eur REAL,
            eta_minutes INTEGER,
            post_summary TEXT NOT NULL,
            raw_transcript_text TEXT,
            result_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders (id)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_templates (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            order_chain_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            name TEXT PRIMARY KEY,
            created_at TEXT NOT NULL
        );
    """)
    # Every dialled attempt keeps its masked transcript: the successful one is
    # the customer's order receipt, the rejected ones explain why the cascade
    # moved on. Before this table the record lived only in process memory and
    # died with the SSE stream (field trial 2026-08-11: two live conversations,
    # zero retrievable evidence). run_id makes the provider call findable again.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS call_attempts (
            id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            restaurant_id TEXT NOT NULL,
            restaurant_name TEXT NOT NULL,
            run_id TEXT,
            status TEXT,
            passed INTEGER NOT NULL DEFAULT 0,
            rejection_reason TEXT,
            post_summary TEXT,
            transcript TEXT,
            live INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
    """)

    conn.commit()
    conn.close()


def create_order_record(
    order_id: str,
    mode: str,
    customer_name: str,
    food_prompt: str,
    max_budget_eur: float | None = None,
    delivery_address: str | None = None,
    reservation_date: str | None = None,
    reservation_time: str | None = None,
    party_size: int | None = None,
    pickup_time: str | None = None,
    location_info: str | None = None,
    dry_run: bool = True,
    order_chain: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Insert a new order record into SQLite."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    created_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    cursor.execute("""
        INSERT INTO orders (
            id, mode, customer_name, food_prompt, max_budget_eur,
            delivery_address, reservation_date, reservation_time, party_size,
            pickup_time, location_info, dry_run, status, created_at, order_chain_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'CREATED', ?, ?)
    """, (
        order_id, mode, customer_name, food_prompt, max_budget_eur,
        delivery_address, reservation_date, reservation_time, party_size,
        pickup_time, location_info, 1 if dry_run else 0, created_at,
        json.dumps(order_chain, ensure_ascii=False) if order_chain else None,
    ))

    conn.commit()
    conn.close()

    return {
        "id": order_id,
        "mode": mode,
        "customer_name": customer_name,
        "food_prompt": food_prompt,
        "max_budget_eur": max_budget_eur,
        "delivery_address": delivery_address,
        "order_chain": order_chain,
        "created_at": created_at
    }


def record_call_attempt(
    order_id: str,
    restaurant_id: str,
    restaurant_name: str,
    run_id: str | None,
    status: str | None,
    passed: bool,
    rejection_reason: str | None,
    post_summary: str | None,
    transcript: str | None,
    live: bool,
) -> dict[str, Any]:
    """Persist one dialled attempt with its masked transcript.

    Idempotent on (order_id, run_id) when a run_id is present -- both call
    clients always set one (call_client.py), so this covers every real call.
    Field-trial finding 2026-08-22 (E6): two identical rows were observed for
    the same live call (same run_id); the reconciliation route into the
    cascade stream that caused that is not itself pinned down, but the
    persistence layer is the one place a duplicate can be stopped for good
    regardless of how it got here. Re-persisting a run_id already on file
    updates that row instead of inserting a second, duplicate receipt for a
    call that only happened once in the real world.
    """
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    created_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    if run_id:
        cursor.execute(
            "SELECT id, created_at FROM call_attempts WHERE order_id = ? AND run_id = ?",
            (order_id, run_id),
        )
        existing = cursor.fetchone()
        if existing is not None:
            cursor.execute("""
                UPDATE call_attempts
                SET restaurant_id = ?, restaurant_name = ?, status = ?, passed = ?,
                    rejection_reason = ?, post_summary = ?, transcript = ?, live = ?
                WHERE id = ?
            """, (
                restaurant_id, restaurant_name, status, 1 if passed else 0,
                rejection_reason, post_summary, transcript, 1 if live else 0,
                existing["id"],
            ))
            conn.commit()
            conn.close()
            return {
                "id": existing["id"], "order_id": order_id,
                "created_at": existing["created_at"],
            }

    attempt_id = f"att_{uuid.uuid4().hex[:10]}"
    cursor.execute("""
        INSERT INTO call_attempts (
            id, order_id, restaurant_id, restaurant_name, run_id, status,
            passed, rejection_reason, post_summary, transcript, live, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        attempt_id, order_id, restaurant_id, restaurant_name, run_id, status,
        1 if passed else 0, rejection_reason, post_summary, transcript,
        1 if live else 0, created_at,
    ))
    conn.commit()
    conn.close()
    return {"id": attempt_id, "order_id": order_id, "created_at": created_at}


def list_call_attempts(order_id: str) -> list[dict[str, Any]]:
    """All dialled attempts of one order, oldest first."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM call_attempts WHERE order_id = ? ORDER BY created_at, id",
        (order_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def _row_order(row: sqlite3.Row) -> dict[str, Any]:
    chain_raw = row["order_chain_json"] if "order_chain_json" in row.keys() else None  # noqa: SIM118
    try:
        chain = json.loads(chain_raw) if chain_raw else None
    except json.JSONDecodeError:
        chain = None
    return {
        "id": row["id"],
        "mode": row["mode"],
        "customer_name": row["customer_name"],
        "food_prompt": row["food_prompt"],
        "max_budget_eur": row["max_budget_eur"],
        "delivery_address": row["delivery_address"],
        "reservation_date": row["reservation_date"],
        "reservation_time": row["reservation_time"],
        "party_size": row["party_size"],
        "pickup_time": row["pickup_time"],
        "location_info": row["location_info"],
        "dry_run": bool(row["dry_run"]),
        "status": row["status"],
        "created_at": row["created_at"],
        "order_chain": chain,
    }


def get_order_record(order_id: str) -> dict[str, Any] | None:
    init_db()
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()
    return _row_order(row) if row else None


def list_order_records() -> list[dict[str, Any]]:
    init_db()
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    conn.close()
    return [_row_order(row) for row in rows]


def list_orders_without_a_kept_result() -> list[dict[str, Any]]:
    """Orders that were actually dialled (at least one call_attempts row)
    but never reached status='COMPLETED' -- i.e. every candidate was
    rejected, or the run is still in progress. Each with its own attempts,
    oldest first, so the full conversation of every dialled candidate is
    available (E12, Nutzer-Design Endabnahme 2026-08-22: "Abgelehnte/
    fehlgeschlagene Bestellungen" -- exactly the evidence a disputed call
    like Anruf 1's needs, and it already lived in call_attempts; this is
    only the read side of it).

    status is never explicitly set to a "failed" value anywhere in this
    codebase (only ever advanced to COMPLETED, in save_cascade_result) --
    so "not completed but dialled" is the same test used here as anywhere
    else that needs to tell a finished cascade from a rejected one.
    """
    init_db()
    conn = get_db_connection()
    order_rows = conn.execute("""
        SELECT o.* FROM orders o
        WHERE o.status != 'COMPLETED'
          AND EXISTS (SELECT 1 FROM call_attempts c WHERE c.order_id = o.id)
        ORDER BY o.created_at DESC
    """).fetchall()
    result = []
    for order_row in order_rows:
        order = _row_order(order_row)
        attempt_rows = conn.execute(
            "SELECT * FROM call_attempts WHERE order_id = ? ORDER BY created_at, id",
            (order["id"],),
        ).fetchall()
        result.append({
            "order": order,
            "attempts": [dict(row) for row in attempt_rows],
        })
    conn.close()
    return result


def save_tags(tags: list[str]) -> None:
    init_db()
    conn = get_db_connection()
    created_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    for raw in tags:
        name = str(raw).strip()
        if name:
            conn.execute(
                "INSERT OR IGNORE INTO tags (name, created_at) VALUES (?, ?)",
                (name, created_at),
            )
    conn.commit()
    conn.close()


def list_tags() -> list[str]:
    init_db()
    conn = get_db_connection()
    rows = conn.execute("SELECT name FROM tags ORDER BY name COLLATE NOCASE").fetchall()
    conn.close()
    return [row["name"] for row in rows]


def save_order_template(name: str, order_chain: dict[str, Any]) -> dict[str, Any]:
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("template name is required")
    init_db()
    conn = get_db_connection()
    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    template_id = f"tpl_{uuid.uuid4().hex[:8]}"
    conn.execute("""
        INSERT INTO order_templates (id, name, order_chain_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            order_chain_json = excluded.order_chain_json,
            updated_at = excluded.updated_at
    """, (template_id, clean_name, json.dumps(order_chain, ensure_ascii=False), now, now))
    conn.commit()
    row = conn.execute(
        "SELECT * FROM order_templates WHERE name = ?", (clean_name,)
    ).fetchone()
    conn.close()
    return {
        "id": row["id"], "name": row["name"],
        "order_chain": json.loads(row["order_chain_json"]),
        "created_at": row["created_at"], "updated_at": row["updated_at"],
    }


def list_order_templates() -> list[dict[str, Any]]:
    init_db()
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM order_templates ORDER BY name COLLATE NOCASE"
    ).fetchall()
    conn.close()
    return [{
        "id": row["id"], "name": row["name"],
        "order_chain": json.loads(row["order_chain_json"]),
        "created_at": row["created_at"], "updated_at": row["updated_at"],
    } for row in rows]


def get_order_template(template_id: str) -> dict[str, Any] | None:
    init_db()
    conn = get_db_connection()
    row = conn.execute(
        "SELECT * FROM order_templates WHERE id = ?", (template_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row["id"], "name": row["name"],
        "order_chain": json.loads(row["order_chain_json"]),
        "created_at": row["created_at"], "updated_at": row["updated_at"],
    }


def save_cascade_result(
    result_id: str,
    order_id: str,
    mode: str,
    restaurant_id: str,
    restaurant_name: str,
    masked_phone: str,
    callback_number: str,
    total_price_eur: float | None,
    eta_minutes: int | None,
    post_summary: str,
    raw_transcript_text: str | None,
    structured_result: dict[str, Any]
) -> dict[str, Any]:
    """Save final successful cascade result to SQLite.

    Idempotent on order_id (E11, Endabnahme-Befund 2026-08-22): a cascade
    now saves itself automatically the moment it is accepted, and the
    "Ergebnis speichern" button on the result card stays reachable too --
    without this, a user who clicks it anyway (or a reconnect that replays
    the outcome event) would file a second, duplicate row for an order that
    only succeeded once. id is not the primary key here, so a plain second
    INSERT would not even collide on its own -- order_id has to be checked
    explicitly. Same idiom as record_call_attempt's (order_id, run_id)
    idempotency above, for the same reason (E6).
    """
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    created_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    result_json = json.dumps(structured_result)

    cursor.execute("SELECT id, created_at FROM saved_results WHERE order_id = ?", (order_id,))
    existing = cursor.fetchone()
    if existing is not None:
        cursor.execute("""
            UPDATE saved_results
            SET mode = ?, restaurant_id = ?, restaurant_name = ?, masked_phone = ?,
                callback_number = ?, total_price_eur = ?, eta_minutes = ?,
                post_summary = ?, raw_transcript_text = ?, result_json = ?
            WHERE id = ?
        """, (
            mode, restaurant_id, restaurant_name, masked_phone,
            callback_number, total_price_eur, eta_minutes,
            post_summary, raw_transcript_text, result_json,
            existing["id"],
        ))
        cursor.execute("UPDATE orders SET status = 'COMPLETED' WHERE id = ?", (order_id,))
        conn.commit()
        conn.close()
        return {
            "id": existing["id"],
            "order_id": order_id,
            "restaurant_name": restaurant_name,
            "callback_number": callback_number,
            "created_at": existing["created_at"],
        }

    cursor.execute("""
        INSERT INTO saved_results (
            id, order_id, mode, restaurant_id, restaurant_name,
            masked_phone, callback_number, total_price_eur, eta_minutes,
            post_summary, raw_transcript_text, result_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        result_id, order_id, mode, restaurant_id, restaurant_name,
        masked_phone, callback_number, total_price_eur, eta_minutes,
        post_summary, raw_transcript_text, result_json, created_at
    ))

    # Update order status to COMPLETED
    cursor.execute("UPDATE orders SET status = 'COMPLETED' WHERE id = ?", (order_id,))

    conn.commit()
    conn.close()

    return {
        "id": result_id,
        "order_id": order_id,
        "restaurant_name": restaurant_name,
        "callback_number": callback_number,
        "created_at": created_at
    }


def list_saved_results() -> list[dict[str, Any]]:
    """Retrieve all saved results ordered by date descending."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT r.*, o.customer_name, o.food_prompt, o.delivery_address
        FROM saved_results r
        JOIN orders o ON r.order_id = o.id
        ORDER BY r.created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        results.append({
            "id": r["id"],
            "order_id": r["order_id"],
            "mode": r["mode"],
            "restaurant_name": r["restaurant_name"],
            "masked_phone": r["masked_phone"],
            "callback_number": r["callback_number"],
            "total_price_eur": r["total_price_eur"],
            "eta_minutes": r["eta_minutes"],
            "post_summary": r["post_summary"],
            "raw_transcript_text": r["raw_transcript_text"],
            "customer_name": r["customer_name"],
            "food_prompt": r["food_prompt"],
            "created_at": r["created_at"]
        })
    return results
