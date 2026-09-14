import asyncio
import asyncpg

DB_URL = "postgresql://commerceflow:commerceflow_secret@localhost:5433/commerceflow_db"

async def main():
    conn = await asyncpg.connect(DB_URL)

    tables = await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
    )

    print(f"\n{'TABLE':<42} {'ROWS':>8}")
    print("-" * 52)
    for t in tables:
        name = t["tablename"]
        try:
            count = await conn.fetchval(f'SELECT count(*) FROM "{name}"')
        except Exception:
            count = "?"
        print(f"  {name:<40} {count:>8}")

    print(f"\nTotal tables: {len(tables)}")
    await conn.close()

asyncio.run(main())
