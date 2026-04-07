import aiohttp
import asyncio
from config import AI_API_KEY


async def enhance_image_with_ai(file_url, prompt):
    url = "https://api.replicate.com/v1/predictions"

    headers = {
        "Authorization": f"Token {AI_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "version": "db21e45e0c3e6b2e3b6f1f0e0d8e6b3d",
        "input": {
            "image": file_url,
            "prompt": prompt
        }
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as resp:
            result = await resp.json()
            get_url = result["urls"]["get"]

            while True:
                async with session.get(get_url, headers=headers) as r:
                    res = await r.json()

                    if res["status"] == "succeeded":
                        return res["output"]

                    if res["status"] == "failed":
                        return None

                await asyncio.sleep(2)