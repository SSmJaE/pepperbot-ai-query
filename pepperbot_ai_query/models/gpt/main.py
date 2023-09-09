from typing import Dict, List

from httpx import AsyncClient
from pepperbot import logger

from pepperbot_ai_query.config import AIQueryConfig


async def gpt_proxy_by_token(messages: List[Dict], openai_token: str, proxy_token: str) -> str:
    async with AsyncClient(timeout=60) as client:
        response = await client.post(
            "http://45.63.82.234/gpt",
            json={
                "proxy_token": proxy_token,
                "openai_token": openai_token,
                "path": "v1/chat/completions",
                "data": {
                    "model": "gpt-3.5-turbo",
                    "max_tokens": 500,
                    "messages": messages,
                },
            },
        )

        completion = response.json()["data"]["choices"][0]["message"]["content"]

        return completion


async def handle_gpt_query(config: AIQueryConfig, context: dict):
    if config.openai_token and config.proxy_token:
        logger.info("将使用代理，进行GPT查询")

        completion = await gpt_proxy_by_token(
            context["history"],
            config.openai_token,
            config.proxy_token,
        )

    elif config.proxy_call:
        logger.info("通过自己实现的方法，进行GPT查询")
        completion = await config.proxy_call(context["history"])

    else:
        error_message = "未设置查询方式，无法进行GPT查询"
        logger.error(error_message)

        raise ValueError(error_message)

    return completion
