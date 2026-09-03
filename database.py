import aiosqlite
from config import DB_PATH, VOICE_POINT_PER_SECOND


async def init_db():
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                voice_seconds INTEGER NOT NULL DEFAULT 0,
                message_count INTEGER NOT NULL DEFAULT 0,
                points INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS shop_roles (
                guild_id INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                price INTEGER NOT NULL,
                category TEXT NOT NULL DEFAULT '기타',
                PRIMARY KEY (guild_id, role_id)
            )
        """)
        # 기존 DB(카테고리 컬럼 없던 버전)를 위한 마이그레이션
        try:
            await conn.execute("ALTER TABLE shop_roles ADD COLUMN category TEXT NOT NULL DEFAULT '기타'")
            await conn.commit()
        except Exception:
            pass
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS reaction_roles (
                message_id INTEGER NOT NULL,
                emoji TEXT NOT NULL,
                role_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                PRIMARY KEY (message_id, emoji)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id INTEGER PRIMARY KEY,
                unverified_role INTEGER,
                newface_role INTEGER,
                base_role INTEGER,
                male_role INTEGER,
                female_role INTEGER,
                teen_role INTEGER,
                twenties_role INTEGER,
                thirties_role INTEGER,
                fourties_role INTEGER,
                log_channel INTEGER
            )
        """)
        await conn.commit()


async def _ensure_user(conn, guild_id, user_id):
    await conn.execute(
        "INSERT OR IGNORE INTO users (guild_id, user_id) VALUES (?, ?)",
        (guild_id, user_id)
    )


async def get_user(guild_id, user_id):
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        await _ensure_user(conn, guild_id, user_id)
        await conn.commit()
        cursor = await conn.execute(
            "SELECT * FROM users WHERE guild_id=? AND user_id=?",
            (guild_id, user_id)
        )
        row = await cursor.fetchone()
        return dict(row)


async def add_voice_time(guild_id, user_id, seconds):
    if seconds <= 0:
        return
    point_delta = int(seconds * VOICE_POINT_PER_SECOND)
    async with aiosqlite.connect(DB_PATH) as conn:
        await _ensure_user(conn, guild_id, user_id)
        await conn.execute(
            "UPDATE users SET voice_seconds = voice_seconds + ?, points = points + ? "
            "WHERE guild_id=? AND user_id=?",
            (seconds, point_delta, guild_id, user_id)
        )
        await conn.commit()


async def add_message(guild_id, user_id):
    async with aiosqlite.connect(DB_PATH) as conn:
        await _ensure_user(conn, guild_id, user_id)
        await conn.execute(
            "UPDATE users SET message_count = message_count + 1, points = points + 1 "
            "WHERE guild_id=? AND user_id=?",
            (guild_id, user_id)
        )
        await conn.commit()


async def add_points(guild_id, user_id, delta):
    async with aiosqlite.connect(DB_PATH) as conn:
        await _ensure_user(conn, guild_id, user_id)
        await conn.commit()
        cursor = await conn.execute(
            "SELECT points FROM users WHERE guild_id=? AND user_id=?",
            (guild_id, user_id)
        )
        row = await cursor.fetchone()
        current = row[0] if row else 0
        new_value = max(0, current + delta)
        await conn.execute(
            "UPDATE users SET points=? WHERE guild_id=? AND user_id=?",
            (new_value, guild_id, user_id)
        )
        await conn.commit()


async def get_all_users(guild_id):
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT * FROM users WHERE guild_id=?", (guild_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_voice_rank(guild_id, user_id):
    async with aiosqlite.connect(DB_PATH) as conn:
        await _ensure_user(conn, guild_id, user_id)
        await conn.commit()
        cursor = await conn.execute(
            "SELECT user_id FROM users WHERE guild_id=? ORDER BY voice_seconds DESC",
            (guild_id,)
        )
        rows = await cursor.fetchall()
        ids = [r[0] for r in rows]
        rank = ids.index(user_id) + 1 if user_id in ids else len(ids) + 1
        return rank, len(ids)


async def get_chat_rank(guild_id, user_id):
    async with aiosqlite.connect(DB_PATH) as conn:
        await _ensure_user(conn, guild_id, user_id)
        await conn.commit()
        cursor = await conn.execute(
            "SELECT user_id FROM users WHERE guild_id=? ORDER BY message_count DESC",
            (guild_id,)
        )
        rows = await cursor.fetchall()
        ids = [r[0] for r in rows]
        rank = ids.index(user_id) + 1 if user_id in ids else len(ids) + 1
        return rank, len(ids)


async def get_top_voice(guild_id, limit=10):
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT * FROM users WHERE guild_id=? ORDER BY voice_seconds DESC LIMIT ?",
            (guild_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_top_chat(guild_id, limit=10):
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT * FROM users WHERE guild_id=? ORDER BY message_count DESC LIMIT ?",
            (guild_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def upsert_shop_role(guild_id, role_id, price, category="기타"):
    category = category.strip() if category and category.strip() else "기타"
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "INSERT INTO shop_roles (guild_id, role_id, price, category) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(guild_id, role_id) DO UPDATE SET price=excluded.price, category=excluded.category",
            (guild_id, role_id, price, category)
        )
        await conn.commit()


async def get_shop_roles(guild_id):
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT * FROM shop_roles WHERE guild_id=?", (guild_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_shop_categories(guild_id):
    """(카테고리명, 개수) 목록을 카테고리명 순으로 반환"""
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.execute(
            "SELECT category, COUNT(*) FROM shop_roles WHERE guild_id=? GROUP BY category ORDER BY category",
            (guild_id,)
        )
        rows = await cursor.fetchall()
        return [(r[0], r[1]) for r in rows]


async def get_shop_roles_by_category(guild_id, category):
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT * FROM shop_roles WHERE guild_id=? AND category=? ORDER BY price",
            (guild_id, category)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def delete_all_shop_roles(guild_id):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("DELETE FROM shop_roles WHERE guild_id=?", (guild_id,))
        await conn.commit()


async def get_shop_price(guild_id, role_id):
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.execute(
            "SELECT price FROM shop_roles WHERE guild_id=? AND role_id=?",
            (guild_id, role_id)
        )
        row = await cursor.fetchone()
        return row[0] if row else None


async def add_reaction_role(message_id, emoji, role_id, guild_id):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "INSERT INTO reaction_roles (message_id, emoji, role_id, guild_id) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(message_id, emoji) DO UPDATE SET role_id=excluded.role_id",
            (message_id, emoji, role_id, guild_id)
        )
        await conn.commit()


async def get_reaction_role(message_id, emoji):
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT * FROM reaction_roles WHERE message_id=? AND emoji=?",
            (message_id, emoji)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_guild_config(guild_id):
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT * FROM guild_config WHERE guild_id=?", (guild_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def upsert_guild_config(guild_id, **kwargs):
    current = await get_guild_config(guild_id) or {}
    fields = [
        "unverified_role", "newface_role", "base_role", "male_role", "female_role",
        "teen_role", "twenties_role", "thirties_role", "fourties_role", "log_channel"
    ]
    merged = {}
    for f in fields:
        new_val = kwargs.get(f)
        merged[f] = new_val if new_val is not None else current.get(f)

    async with aiosqlite.connect(DB_PATH) as conn:
        columns = ", ".join(fields)
        placeholders = ", ".join(["?"] * len(fields))
        updates = ", ".join([f"{f}=excluded.{f}" for f in fields])
        await conn.execute(
            f"""INSERT INTO guild_config (guild_id, {columns})
                VALUES (?, {placeholders})
                ON CONFLICT(guild_id) DO UPDATE SET {updates}""",
            [guild_id] + [merged[f] for f in fields]
        )
        await conn.commit()
