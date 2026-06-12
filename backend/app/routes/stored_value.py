from flask import Blueprint, request

from ..database import get_connection, rows_to_dicts

stored_value_bp = Blueprint("stored_value", __name__)


@stored_value_bp.get("/account/<plate_number>", strict_slashes=False)
def get_account(plate_number):
    with get_connection() as conn:
        account = conn.execute(
            "SELECT * FROM stored_value_accounts WHERE plate_number = ?",
            (plate_number,),
        ).fetchone()
    if not account:
        return {"message": "储值账户不存在"}, 404
    return dict(account)


@stored_value_bp.get("/accounts", strict_slashes=False)
def list_accounts():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM stored_value_accounts ORDER BY id DESC"
        ).fetchall()
    return {"items": rows_to_dicts(rows)}


@stored_value_bp.post("/recharge", strict_slashes=False)
def recharge():
    data = request.get_json() or {}
    plate_number = data.get("plate_number")
    amount = data.get("amount")
    remark = data.get("remark", "储值充值")

    if not plate_number or not amount:
        return {"message": "车牌号和充值金额不能为空"}, 400
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return {"message": "充值金额不合法"}, 400
    if amount <= 0:
        return {"message": "充值金额必须大于0"}, 400

    with get_connection() as conn:
        account = conn.execute(
            "SELECT * FROM stored_value_accounts WHERE plate_number = ?",
            (plate_number,),
        ).fetchone()

        if not account:
            cur = conn.execute(
                """
                INSERT INTO stored_value_accounts
                    (plate_number, balance, created_at, updated_at)
                VALUES (?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))
                """,
                (plate_number, 0),
            )
            account = conn.execute(
                "SELECT * FROM stored_value_accounts WHERE id = ?", (cur.lastrowid,)
            ).fetchone()

        new_balance = round(account["balance"] + amount, 2)
        conn.execute(
            """
            UPDATE stored_value_accounts
            SET balance = ?, updated_at = datetime('now', 'localtime')
            WHERE id = ?
            """,
            (new_balance, account["id"]),
        )

        conn.execute(
            """
            INSERT INTO stored_value_transactions
                (account_id, plate_number, type, amount, balance_after, remark, created_at)
            VALUES (?, ?, 'recharge', ?, ?, ?, datetime('now', 'localtime'))
            """,
            (account["id"], plate_number, amount, new_balance, remark),
        )

        updated_account = conn.execute(
            "SELECT * FROM stored_value_accounts WHERE id = ?", (account["id"],)
        ).fetchone()

    return dict(updated_account), 200


@stored_value_bp.get("/transactions", strict_slashes=False)
def list_transactions():
    plate_number = request.args.get("plate_number")
    with get_connection() as conn:
        if plate_number:
            rows = conn.execute(
                "SELECT * FROM stored_value_transactions WHERE plate_number = ? ORDER BY id DESC",
                (plate_number,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM stored_value_transactions ORDER BY id DESC LIMIT 200"
            ).fetchall()
    return {"items": rows_to_dicts(rows)}
