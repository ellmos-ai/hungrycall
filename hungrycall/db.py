"""SQLite database layer for HungryCall web interface."""

import json
import sqlite3
import os
import time
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
    dry_run: bool = True
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
            pickup_time, location_info, dry_run, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'CREATED', ?)
    """, (
        order_id, mode, customer_name, food_prompt, max_budget_eur,
        delivery_address, reservation_date, reservation_time, party_size,
        pickup_time, location_info, 1 if dry_run else 0, created_at
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
        "created_at": created_at
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
