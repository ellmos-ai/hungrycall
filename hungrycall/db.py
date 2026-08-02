"""SQLite database layer for HungryCall web interface."""

import json
import sqlite3
import os
import time
import uuid
from typing import Dict, Any, List, Optional

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


def init_db(db_path_override: Optional[str] = None) -> None:
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

    conn.commit()
    conn.close()


def create_order_record(
    order_id: str,
    mode: str,
    customer_name: str,
    food_prompt: str,
    max_budget_eur: Optional[float] = None,
    delivery_address: Optional[str] = None,
    reservation_date: Optional[str] = None,
    reservation_time: Optional[str] = None,
    party_size: Optional[int] = None,
    pickup_time: Optional[str] = None,
    location_info: Optional[str] = None,
    dry_run: bool = True,
    order_chain: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
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


def _row_order(row: sqlite3.Row) -> Dict[str, Any]:
    chain_raw = row["order_chain_json"] if "order_chain_json" in row.keys() else None
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


def get_order_record(order_id: str) -> Optional[Dict[str, Any]]:
    init_db()
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()
    return _row_order(row) if row else None


def list_order_records() -> List[Dict[str, Any]]:
    init_db()
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    conn.close()
    return [_row_order(row) for row in rows]


def save_tags(tags: List[str]) -> None:
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


def list_tags() -> List[str]:
    init_db()
    conn = get_db_connection()
    rows = conn.execute("SELECT name FROM tags ORDER BY name COLLATE NOCASE").fetchall()
    conn.close()
    return [row["name"] for row in rows]


def save_order_template(name: str, order_chain: Dict[str, Any]) -> Dict[str, Any]:
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


def list_order_templates() -> List[Dict[str, Any]]:
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


def get_order_template(template_id: str) -> Optional[Dict[str, Any]]:
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
    total_price_eur: Optional[float],
    eta_minutes: Optional[int],
    post_summary: str,
    raw_transcript_text: Optional[str],
    structured_result: Dict[str, Any]
) -> Dict[str, Any]:
    """Save final successful cascade result to SQLite."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    created_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    result_json = json.dumps(structured_result)

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


def list_saved_results() -> List[Dict[str, Any]]:
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
