import aiohttp
import asyncio

async def test_connection():
    url = "https://api.telegram.org/bot8103083020:AAFsuQEYE8V55eD0Plb-b9Qd_-HVniwVVBQ/getMe"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                print(f"Status: {response.status}")
                print(await response.text())
    except Exception as e:
        print(f"Connection error: {e}")

asyncio.run(test_connection())
