from flask import Blueprint, request

from ..database import get_connection, rows_to_dicts

monthly_cards_bp = Blueprint("monthly_cards", __name__)


def _attach_balance(conn, cards):
    plates = [c["plate_number"] for c in cards]
    if not plates:
        return cards
    placeholders = ",".join("?" * len(plates))
    accounts = conn.execute(
        f"SELECT * FROM stored_value_accounts WHERE plate_number IN ({placeholders})",
        plates,
    ).fetchall()
    account_map = {a["plate_number"]: a for a in accounts}
    for card in cards:
        acct = account_map.get(card["plate_number"])
        card["balance"] = acct["balance"] if acct else 0
        card["account_opened"] = acct is not None
    return cards


@monthly_cards_bp.get("/", strict_slashes=False)
def list_cards():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM monthly_cards ORDER BY id DESC").fetchall()
        cards = rows_to_dicts(rows)
        cards = _attach_balance(conn, cards)
    return {"items": cards}


@monthly_cards_bp.post("/", strict_slashes=False)
def create_card():
    data = request.get_json() or {}
    required = ["holder_name", "phone", "plate_number", "start_date", "end_date", "fee"]
    if any(not data.get(field) for field in required):
        return {"message": "月卡信息不完整"}, 400

    initial_balance = float(data.get("initial_balance", 0) or 0)

    try:
        with get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO monthly_cards
                    (holder_name, phone, plate_number, start_date, end_date, fee, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["holder_name"],
                    data["phone"],
                    data["plate_number"],
                    data["start_date"],
                    data["end_date"],
                    float(data["fee"]),
                    data.get("status", "active"),
                ),
            )
            row = conn.execute("SELECT * FROM monthly_cards WHERE id = ?", (cur.lastrowid,)).fetchone()

            existing = conn.execute(
                "SELECT * FROM stored_value_accounts WHERE plate_number = ?",
                (data["plate_number"],),
            ).fetchone()
            if existing:
                account_id = existing["id"]
                if initial_balance > 0:
                    new_balance = round(existing["balance"] + initial_balance, 2)
                    conn.execute(
                        """
                        UPDATE stored_value_accounts
                        SET balance = ?, updated_at = datetime('now', 'localtime')
                        WHERE id = ?
                        """,
                        (new_balance, existing["id"]),
                    )
                    conn.execute(
                        """
                        INSERT INTO stored_value_transactions
                            (account_id, plate_number, type, amount, balance_after, remark, created_at)
                        VALUES (?, ?, 'recharge', ?, ?, ?, datetime('now', 'localtime'))
                        """,
                        (account_id, data["plate_number"], initial_balance, new_balance, "办卡时储值"),
                    )
            else:
                acc_cur = conn.execute(
                    """
                    INSERT INTO stored_value_accounts
                        (plate_number, balance, created_at, updated_at)
                    VALUES (?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))
                    """,
                    (data["plate_number"], initial_balance),
                )
                account_id = acc_cur.lastrowid
                if initial_balance > 0:
                    conn.execute(
                        """
                        INSERT INTO stored_value_transactions
                            (account_id, plate_number, type, amount, balance_after, remark, created_at)
                        VALUES (?, ?, 'recharge', ?, ?, ?, datetime('now', 'localtime'))
                        """,
                        (account_id, data["plate_number"], initial_balance, initial_balance, "办卡时储值"),
                    )
    except Exception as exc:
        if "UNIQUE" in str(exc):
            return {"message": "该车牌已办理月卡"}, 409
        raise

    result = dict(row)
    result["balance"] = initial_balance
    result["account_opened"] = True
    return result, 201


@monthly_cards_bp.patch("/<int:card_id>")
def update_card(card_id):
    data = request.get_json() or {}
    status = data.get("status")
    if status not in {"active", "expired", "paused"}:
        return {"message": "月卡状态不合法"}, 400

    with get_connection() as conn:
        conn.execute("UPDATE monthly_cards SET status = ? WHERE id = ?", (status, card_id))
        row = conn.execute("SELECT * FROM monthly_cards WHERE id = ?", (card_id,)).fetchone()

    if not row:
        return {"message": "月卡不存在"}, 404
    return dict(row)
