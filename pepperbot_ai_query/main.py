from typing import Any, Dict, Optional, cast

from devtools import debug

from pepperbot import logger
from pepperbot.adapters.onebot.api import OnebotV11GroupBot, OnebotV11PrivateBot
from pepperbot.adapters.telegram.api import TelegramPrivateBot
from pepperbot.core.message.chain import MessageChain
from pepperbot.core.message.segment import At, Text
from pepperbot.exceptions import StopPropagation
from pepperbot.extensions.command import sub_command
from pepperbot.extensions.command.sender import CommandSender
from pepperbot.store.command import CLIOption
from pepperbot.store.event import PropagationConfig
from pepperbot.types import T_StopPropagation
from textwrap import dedent

from pepperbot_ai_query import manage
from pepperbot_ai_query.config import (
    AIQueryConfig,
    ModelNames,
    generate_empty_model_count,
)
from pepperbot_ai_query.models.gpt.main import handle_gpt_query
from pepperbot_ai_query.orm import ManageInfo, UsageInfo
from pepperbot_ai_query.utils import get_manage_info, get_times, get_usage_info


class AISubCommands:
    @sub_command()
    async def usage(self, sender: CommandSender):
        await sender.send_message(
            At(sender.user_id),
            Text("GPT使用情况"),
        )

        return None

    @sub_command()
    async def model(self, sender: CommandSender):
        await sender.send_message(
            At(sender.user_id),
            Text("模型情况"),
        )

        return None


# usage:Optional[bool] = CLIOption(default=False), # TODO pepperbot尚未实现store true(针对bool)，这里还是需要参数
class AIQuery:
    async def initial(
        self,
        sender: CommandSender,
        chain: MessageChain,
        config: Any,  # TODO
        context: dict,
        stop_propagation: T_StopPropagation,
        usage: Optional[bool] = CLIOption(default=False),
        model: Optional[str] = CLIOption(default=ModelNames.gpt_3_5),
    ):
        config = cast(AIQueryConfig, config)

        # debug(usage)

        usage_info = await get_usage_info(chain)
        manage_info = await get_manage_info(sender)

        continue_flag, unlimited_flag, maximum = get_times(
            usage_info, manage_info, sender, config, usage_info.current_model
        )

        if unlimited_flag == False:
            await sender.send_message(
                At(sender.user_id),
                Text("已被禁用"),
            )
            return None

        if not continue_flag:
            await sender.send_message(
                # At(sender.user_id),
                Text("今天已经超过最大调用次数了，明天再来吧\n"),
                Text("水群5次，解锁5次\n"),
                Text("在两个不同群中发言，解锁5次\n"),
            )
            return None

        usage_info.querying = True
        await usage_info.update()

        context.setdefault("history", [])

        # logger.info(chain.pure_text)
        without_prefix = chain.pure_text.replace("/ai", "").strip()
        context["history"].append({"role": "user", "content": without_prefix})

        # debug(config.proxy_call)
        # debug(bool(config.proxy_call))

        # raise Exception("test error")

        # match (usage_info.current_model):
        #     case ModelNames.gpt_3_5:
        #         handler = handle_gpt_query

        #     case ModelNames.wenxin:
        #         handler = handle_gpt_query

        #     case _:
        #         raise Exception("选择了未知模型")

        if usage_info.current_model == ModelNames.gpt_3_5:
            handler = handle_gpt_query

        else:
            raise Exception("选择了未知模型")

        completion = await handler(config, context)

        usage_info.querying = False
        usage_info.count.setdefault(usage_info.current_model, 0)
        usage_info.count[usage_info.current_model] += 1
        usage_info.history_count.setdefault(usage_info.current_model, 0)
        usage_info.history_count[usage_info.current_model] += 1
        await usage_info.update()

        context["history"].append({"role": "assistant", "content": completion})

        await sender.send_message(
            At(chain.user_id),
            Text(completion),
        )

        # 不再运行后续的handler，针对的就是IsActive
        stop_propagation()

        return self.initial

    async def exit(self, context: Dict):
        context["action"] = "用户主动退出会话"

    async def timeout(self, context: Dict):
        context["action"] = "用户超时未响应，自动退出会话"

    async def catch(self, context: Dict, exception: Exception):
        context["action"] = f"发生异常，自动退出会话 {exception}"

    async def cleanup(self, sender: CommandSender, context: Dict, chain: MessageChain):
        usage_info = await get_usage_info(chain)

        usage_info.querying = False
        await usage_info.update()

        action = context.get("action", "会话结束")

        await sender.send_message(
            At(sender.user_id),
            Text(
                f"{action}\n"
                + "解答完成，欢迎再来😀\n"
                + "基于PepperBot，https://github.com/SSmJaE/PepperBot\n"
                # + "该机器人指令已开源，可以直接下载使用，https://github.com/SSmJaE/pepperbot-ai-query"
            ),
        )


class AIUsage:
    async def initial(
        self,
        sender: CommandSender,
        chain: MessageChain,
        config: Any,
        stop_propagation: T_StopPropagation,
    ):
        stop_propagation()

        usage_info = await get_usage_info(chain)
        manage_info = await get_manage_info(sender)

        model_usage = ""
        for model_name, used in usage_info.count.items():
            continue_flag, unlimited_flag, maximum = get_times(
                usage_info, manage_info, sender, config, model_name
            )
            if unlimited_flag == False:
                model_usage = "已被禁用"
                break

            model_usage += f"    - {model_name}: {used}/{'无限制' if unlimited_flag==True else maximum}\n"

        await sender.send_message(
            At(sender.user_id),
            Text(
                dedent(
                    f"""\
                    当前账号：{chain.user_id}
                    所在群组：{chain.source_id}
                    使用情况：(已用/上限)
                    """
                )
                + model_usage  # 会破坏缩进
            ),
        )

        return None

    # @sub_command()
    # async def model(self, sender: CommandSender):
    #     await sender.send_message(
    #         At(sender.user_id),
    #         Text("模型情况"),
    #     )

    #     return None


class EnsureNotQuerying:
    config = PropagationConfig(
        priority=10000,
        concurrency=False,
        propagation_group="gpt",
    )

    # TODO 匹配大类事件，比如所有message
    async def onebot_group_message(self, bot: OnebotV11GroupBot, chain: MessageChain):
        usage_info = await get_usage_info(chain)

        if usage_info.querying:
            await bot.group_message(
                At(chain.user_id),
                Text("正在查询中，不要连续发送消息"),
            )

            raise StopPropagation()

    async def onebot_friend_message(
        self, bot: OnebotV11PrivateBot, chain: MessageChain
    ):
        usage_info = await get_usage_info(chain)

        if usage_info.querying:
            await bot.private_message(
                Text("正在查询中，不要连续发送消息"),
            )

            raise StopPropagation()

    async def onebot_temporary_message(
        self, bot: OnebotV11PrivateBot, chain: MessageChain
    ):
        usage_info = await get_usage_info(chain)

        if usage_info.querying:
            await bot.private_message(
                Text("正在查询中，不要连续发送消息"),
            )

            raise StopPropagation()

    async def telegram_private_message(
        self, bot: TelegramPrivateBot, chain: MessageChain
    ):
        usage_info = await get_usage_info(chain)

        if usage_info.querying:
            await bot.private_message(
                Text("正在查询中，不要连续发送消息"),
            )

            raise StopPropagation()


class IsActive:
    config = PropagationConfig(
        priority=10,
        concurrency=True,
        propagation_group="gpt",
    )

    async def onebot_group_message(self, bot: OnebotV11GroupBot, chain: MessageChain):
        usage_info = await get_usage_info(chain)

        usage_info.permission.setdefault("active", False)
        usage_info.permission.setdefault("cross_source", False)

        if not usage_info.permission["active"]:
            count = len(usage_info.history_messages_text)

            usage_info.history_messages_text.append(
                (chain.mode, chain.source_id, chain.pure_text)
            )

            if count < 5:
                await usage_info.update()
                return

            # 去除第一条
            usage_info.history_messages_text.pop(0)

            text_only = [text for (t, s, text) in usage_info.history_messages_text]

            # 不重复的5条，重复的不算
            redundancy = False

            for text in text_only:
                redundancy_count = text_only.count(text)
                if redundancy_count > 1:
                    redundancy = True

            if not redundancy:
                usage_info.permission["active"] = True
                await bot.group_message(At(chain.user_id), Text("满足活跃度要求，解锁额外5次"))

            await usage_info.update()

        if (
            usage_info.permission["active"]
            and not usage_info.permission["cross_source"]
        ):
            group_ids = set()

            for conversation_type, source_id, text in usage_info.history_messages_text:
                if conversation_type == "group":
                    group_ids.add(source_id)

            if len(group_ids) >= 2:
                usage_info.permission["cross_source"] = True
                await bot.group_message(At(chain.user_id), Text("在两个不同群中发言，解锁额外5次"))

                await usage_info.update()


# @as_command()
# class GPTUserInfo:
#     """单独搞出来，是为了不进入会话

#     也不触发rate limit
#     """

#     async def initial(self, sender: CommandSender):
#         await sender.send_message(
#             At(sender.user_id),
#             Text("欢迎使用GPT查询系统"),
#         )

#     @sub_command()
#     async def info(self, sender: CommandSender):
#         await sender.send_message(
#             At(sender.user_id),
#             Text("GPT信息"),
#         )

#         return None
