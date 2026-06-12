from datetime import datetime

from flask import Blueprint, request

from ..database import get_connection, rows_to_dicts
from ..services.billing import calculate_fee

parking_bp = Blueprint("parking", __name__)


@parking_bp.get("/orders")
def list_orders():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM parking_orders ORDER BY id DESC LIMIT 100").fetchall()
    return {"items": rows_to_dicts(rows)}


@parking_bp.post("/entry")
def create_entry():
    data = request.get_json() or {}
    plate_number = data.get("plate_number")
    space_code = data.get("space_code")
    if not plate_number or not space_code:
        return {"message": "车牌号和车位号不能为空"}, 400

    with get_connection() as conn:
        space = conn.execute("SELECT * FROM spaces WHERE code = ?", (space_code,)).fetchone()
        if not space:
            return {"message": "车位不存在"}, 404
        if space["status"] not in {"free", "reserved"}:
            return {"message": "车位当前不可入场"}, 409

        entry_time = data.get("entry_time") or datetime.now().isoformat(timespec="minutes")
        cur = conn.execute(
            """
            INSERT INTO parking_orders (plate_number, space_code, entry_time, status)
            VALUES (?, ?, ?, 'parking')
            """,
            (plate_number, space_code, entry_time),
        )
        conn.execute(
            """
            UPDATE spaces
            SET status = 'occupied', plate_number = ?, updated_at = datetime('now', 'localtime')
            WHERE code = ?
            """,
            (plate_number, space_code),
        )
        row = conn.execute("SELECT * FROM parking_orders WHERE id = ?", (cur.lastrowid,)).fetchone()

    return dict(row), 201


@parking_bp.post("/calculate")
def calculate():
    data = request.get_json() or {}
    if not data.get("entry_time") or not data.get("exit_time"):
        return {"message": "入场时间和离场时间不能为空"}, 400
    return calculate_fee(data["entry_time"], data["exit_time"])


@parking_bp.post("/exit/<int:order_id>")
def close_order(order_id):
    data = request.get_json() or {}
    exit_time = data.get("exit_time") or datetime.now().isoformat(timespec="minutes")
    use_stored_value = data.get("use_stored_value", True)

    with get_connection() as conn:
        order = conn.execute("SELECT * FROM parking_orders WHERE id = ?", (order_id,)).fetchone()
        if not order:
            return {"message": "停车订单不存在"}, 404
        if order["status"] == "paid":
            return {"message": "订单已结算"}, 409

        bill = calculate_fee(order["entry_time"], exit_time)
        original_amount = bill["amount"]
        amount = original_amount
        stored_value_deducted = 0
        remaining_balance = None

        if use_stored_value and amount > 0:
            account = conn.execute(
                "SELECT * FROM stored_value_accounts WHERE plate_number = ?",
                (order["plate_number"],),
            ).fetchone()
            if account and account["balance"] > 0:
                stored_value_deducted = min(account["balance"], amount)
                amount = round(amount - stored_value_deducted, 2)
                remaining_balance = round(account["balance"] - stored_value_deducted, 2)
                conn.execute(
                    """
                    UPDATE stored_value_accounts
                    SET balance = ?, updated_at = datetime('now', 'localtime')
                    WHERE id = ?
                    """,
                    (remaining_balance, account["id"]),
                )
                conn.execute(
                    """
                    INSERT INTO stored_value_transactions
                        (account_id, plate_number, type, amount, balance_after, related_order_id, remark, created_at)
                    VALUES (?, ?, 'consume', ?, ?, ?, ?, datetime('now', 'localtime'))
                    """,
                    (
                        account["id"],
                        order["plate_number"],
                        stored_value_deducted,
                        remaining_balance,
                        order_id,
                        "临停费用自动抵扣",
                    ),
                )

        conn.execute(
            """
            UPDATE parking_orders
            SET exit_time = ?, duration_hours = ?, original_amount = ?, stored_value_deducted = ?, amount = ?, status = 'paid'
            WHERE id = ?
            """,
            (exit_time, bill["duration_hours"], original_amount, stored_value_deducted, amount, order_id),
        )
        conn.execute(
            """
            UPDATE spaces
            SET status = 'free', plate_number = NULL, updated_at = datetime('now', 'localtime')
            WHERE code = ?
            """,
            (order["space_code"],),
        )
        row = conn.execute("SELECT * FROM parking_orders WHERE id = ?", (order_id,)).fetchone()

    result = dict(row)
    result["remaining_balance"] = remaining_balance
    return result
