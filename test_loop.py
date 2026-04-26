import asyncio
from concurrent.futures import ThreadPoolExecutor

def sync_func():
    try:
        loop = asyncio.get_event_loop()
        print(f"Is running: {loop.is_running()}")
    except Exception as e:
        print(f"Error: {type(e).__name__} - {e}")

async def main():
    with ThreadPoolExecutor() as pool:
        await asyncio.get_running_loop().run_in_executor(pool, sync_func)

asyncio.run(main())
