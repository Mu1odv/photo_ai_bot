import aiohttp
import asyncio
from aiogram import Bot
from config import AI_API_KEY, BOT_TOKEN, TEST_MODE


async def build_telegram_file_url(bot: Bot, file_id: str) -> str:
    file = await bot.get_file(file_id)
    return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"


def _normalize_output(output):
    if isinstance(output, list):
        return output[-1] if output else None
    return output


async def enhance_image_with_ai(file_url, prompt, test_mode=None):
    if test_mode is None:
        test_mode = TEST_MODE
    if test_mode or not AI_API_KEY:
        await asyncio.sleep(0.5)
        return file_url

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
            if resp.status >= 400:
                return None
            result = await resp.json()
            get_url = result.get("urls", {}).get("get")
            if not get_url:
                return None

            while True:
                async with session.get(get_url, headers=headers) as r:
                    if r.status >= 400:
                        return None
                    res = await r.json()

                    if res.get("status") == "succeeded":
                        return _normalize_output(res.get("output"))

                    if res.get("status") == "failed":
                        return None

                await asyncio.sleep(2)


async def generate_video_from_photos(photo_urls, prompt, test_mode=None):
    if test_mode is None:
        test_mode = TEST_MODE
    if test_mode or not AI_API_KEY:
        await asyncio.sleep(0.5)
        return None

    # TODO: Replace with a real video model integration.
    return None