import aiosqlite
import json
from datetime import datetime, date
from config import DB_PATH

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                language TEXT DEFAULT 'uz',
                is_premium INTEGER DEFAULT 0,
                premium_until TEXT,
                daily_count INTEGER DEFAULT 0,
                last_reset TEXT,
                is_blocked INTEGER DEFAULT 0,
                join_date TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount TEXT,
                method TEXT,
                status TEXT DEFAULT 'pending',
                proof_file_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                confirmed_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT,
                channel_username TEXT,
                channel_name TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS promocodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                type TEXT,
                discount INTEGER DEFAULT 0,
                days INTEGER DEFAULT 30,
                max_uses INTEGER DEFAULT 100,
                used_count INTEGER DEFAULT 0,
                expires_at TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS promo_uses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                promo_id INTEGER,
                used_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                total_requests INTEGER DEFAULT 0,
                new_users INTEGER DEFAULT 0,
                revenue INTEGER DEFAULT 0
            )
        """)

        # Default settings
        defaults = {
            "feature_chat": "1",
            "feature_image": "1",
            "feature_search": "0",
            "feature_premium": "1",
            "feature_registration": "1",
            "bot_active": "1",
            "daily_limit": "10",
            "premium_price": "19900",
            "stars_price": "100",
            "premium_days": "30",
            "payment_card": "",
            "payment_card_owner": "",
            "require_channel": "0",
        }
        for key, value in defaults.items():
            await db.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )
        await db.commit()

async def get_setting(key: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key=?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else ""

async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def create_user(user_id: int, username: str, full_name: str, language: str = "uz"):
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR IGNORE INTO users 
               (user_id, username, full_name, language, last_reset, join_date)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, username, full_name, language, today, datetime.now().isoformat())
        )
        await db.commit()
    # Update stats
    await update_daily_stats(new_user=True)

async def update_user_language(user_id: int, language: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET language=? WHERE user_id=?", (language, user_id))
        await db.commit()

async def increment_daily_count(user_id: int):
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        user = await get_user(user_id)
        if user and user["last_reset"] != today:
            await db.execute(
                "UPDATE users SET daily_count=1, last_reset=? WHERE user_id=?",
                (today, user_id)
            )
        else:
            await db.execute(
                "UPDATE users SET daily_count=daily_count+1 WHERE user_id=?",
                (user_id,)
            )
        await db.commit()
    await update_daily_stats(request=True)

async def get_daily_count(user_id: int) -> int:
    today = date.today().isoformat()
    user = await get_user(user_id)
    if not user:
        return 0
    if user["last_reset"] != today:
        return 0
    return user["daily_count"]

async def set_premium(user_id: int, days: int):
    from datetime import timedelta
    until = (datetime.now() + timedelta(days=days)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_premium=1, premium_until=? WHERE user_id=?",
            (until, user_id)
        )
        await db.commit()

async def remove_premium(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_premium=0, premium_until=NULL WHERE user_id=?",
            (user_id,)
        )
        await db.commit()

async def block_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_blocked=1 WHERE user_id=?", (user_id,))
        await db.commit()

async def unblock_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_blocked=0 WHERE user_id=?", (user_id,))
        await db.commit()

async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE is_blocked=0") as cursor:
            return await cursor.fetchall()

async def get_premium_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE is_premium=1") as cursor:
            return await cursor.fetchall()

async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        today = date.today().isoformat()
        async with db.execute("SELECT COUNT(*) as total FROM users") as c:
            total = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) as cnt FROM users WHERE is_premium=1") as c:
            premium = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) as cnt FROM users WHERE is_blocked=1") as c:
            blocked = (await c.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) as cnt FROM users WHERE date(join_date)=?", (today,)
        ) as c:
            today_new = (await c.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) as cnt FROM users WHERE last_reset=?", (today,)
        ) as c:
            active_today = (await c.fetchone())[0]
        async with db.execute(
            "SELECT SUM(daily_count) FROM users WHERE last_reset=?", (today,)
        ) as c:
            today_requests = (await c.fetchone())[0] or 0
        async with db.execute(
            "SELECT COUNT(*) FROM payments WHERE status='confirmed' AND date(created_at)=?", (today,)
        ) as c:
            today_payments = (await c.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM payments WHERE status='pending'"
        ) as c:
            pending_payments = (await c.fetchone())[0]
        return {
            "total": total,
            "premium": premium,
            "blocked": blocked,
            "today_new": today_new,
            "active_today": active_today,
            "today_requests": today_requests,
            "today_payments": today_payments,
            "pending_payments": pending_payments,
        }

async def add_payment(user_id: int, amount: str, method: str, proof_file_id: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO payments (user_id, amount, method, proof_file_id) VALUES (?, ?, ?, ?)",
            (user_id, amount, method, proof_file_id)
        )
        await db.commit()
        async with db.execute("SELECT last_insert_rowid()") as c:
            return (await c.fetchone())[0]

async def confirm_payment(payment_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE payments SET status='confirmed', confirmed_at=? WHERE id=?",
            (datetime.now().isoformat(), payment_id)
        )
        await db.commit()

async def reject_payment(payment_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE payments SET status='rejected' WHERE id=?", (payment_id,))
        await db.commit()

async def get_pending_payments():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT p.*, u.username, u.full_name FROM payments p JOIN users u ON p.user_id=u.user_id WHERE p.status='pending'"
        ) as cursor:
            return await cursor.fetchall()

async def add_channel(channel_id: str, username: str, name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO channels (channel_id, channel_username, channel_name) VALUES (?, ?, ?)",
            (channel_id, username, name)
        )
        await db.commit()

async def get_channels():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM channels WHERE is_active=1") as cursor:
            return await cursor.fetchall()

async def remove_channel(channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM channels WHERE id=?", (channel_id,))
        await db.commit()

async def create_promo(code: str, promo_type: str, discount: int, days: int,
                       max_uses: int, expires_at: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO promocodes (code, type, discount, days, max_uses, expires_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (code, promo_type, discount, days, max_uses, expires_at)
        )
        await db.commit()

async def use_promo(user_id: int, code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM promocodes WHERE code=? AND is_active=1", (code.upper(),)
        ) as c:
            promo = await c.fetchone()
        if not promo:
            return None, "not_found"

        today = datetime.now().isoformat()
        if promo["expires_at"] and promo["expires_at"] < today:
            return None, "expired"

        if promo["used_count"] >= promo["max_uses"]:
            return None, "limit"

        async with db.execute(
            "SELECT id FROM promo_uses WHERE user_id=? AND promo_id=?",
            (user_id, promo["id"])
        ) as c:
            already = await c.fetchone()
        if already:
            return None, "already_used"

        await db.execute(
            "UPDATE promocodes SET used_count=used_count+1 WHERE id=?", (promo["id"],)
        )
        await db.execute(
            "INSERT INTO promo_uses (user_id, promo_id) VALUES (?, ?)",
            (user_id, promo["id"])
        )
        await db.commit()
        return dict(promo), "ok"

async def get_promos():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM promocodes ORDER BY created_at DESC") as cursor:
            return await cursor.fetchall()

async def deactivate_promo(promo_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE promocodes SET is_active=0 WHERE id=?", (promo_id,))
        await db.commit()

async def update_daily_stats(new_user=False, request=False, revenue=0):
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id FROM stats WHERE date=?", (today,)) as c:
            row = await c.fetchone()
        if not row:
            await db.execute("INSERT INTO stats (date) VALUES (?)", (today,))
        if new_user:
            await db.execute("UPDATE stats SET new_users=new_users+1 WHERE date=?", (today,))
        if request:
            await db.execute(
                "UPDATE stats SET total_requests=total_requests+1 WHERE date=?", (today,)
            )
        if revenue:
            await db.execute(
                "UPDATE stats SET revenue=revenue+? WHERE date=?", (revenue, today)
            )
        await db.commit()

async def get_weekly_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM stats ORDER BY date DESC LIMIT 7"
        ) as cursor:
            return await cursor.fetchall()
