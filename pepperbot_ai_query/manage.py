import json
from typing import Any, Dict, Optional, cast

from pepperbot import logger
from pepperbot.core.message.chain import MessageChain
from pepperbot.core.message.segment import At, Text
from pepperbot.extensions.command import CLIArgument, CLIOption, sub_command
from pepperbot.extensions.command.sender import CommandSender
from pydantic import parse_raw_as

from pepperbot_ai_query.config import (
    AIQueryConfig,
    ModelNames,
    T_ModelName,
    generate_empty_model_count,
)
from pepperbot_ai_query.orm import ManageInfo

from typing import Any, Callable, Coroutine, Dict, List, Literal, Optional, Tuple, Union

from pepperbot.types import T_BotProtocol, T_ConversationType


class AIQueryManage:
    async def initial(self, sender: CommandSender):
        await sender.send_message(Text("欢迎使用AI管理命令"))

    @sub_command(name="list")
    async def list_items(self, sender: CommandSender):
        rows = ""

        items = await ManageInfo.objects.all()
        for item in items:
            rows += f"{item.protocol} {item.conversation_type} {item.source_id} {item.times} {item.unlimited} {item.forbidden}\n"

        await sender.send_message(Text(rows if rows else "没有任何记录"))

    @sub_command(name="set")
    async def set_privilege(
        self,
        sender: CommandSender,
        protocol: Optional[str] = CLIOption(default="onebot"),
        conversation_type: str = CLIArgument(),
        source_id: str = CLIArgument(),
        times: Optional[int] = CLIOption(),
        forbidden: Optional[bool] = CLIOption(),
        model: Optional[str] = CLIOption(default=ModelNames.gpt_3_5),
    ):
        if conversation_type not in ("private", "group"):
            await sender.send_message(Text("conversation_type 只能为 user 或 group"))

            return None

        if model not in ("gpt-3.5", "wenxin"):
            await sender.send_message(Text("model 只能为 gpt-3.5 或 wenxin"))

            return None

        query_keys = dict(
            protocol=protocol,
            conversation_type=conversation_type,
            source_id=source_id,
        )

        times_per_model = generate_empty_model_count()
        if times is not None:
            times_per_model[model] = times

        default_keys: Dict = {**query_keys}

        if forbidden is not None:
            default_keys["forbidden"] = True

        else:
            if times is None:
                default_keys["unlimited"] = True
            else:
                default_keys["times"] = times_per_model

        manage_info, created = await ManageInfo.objects.get_or_create(
            **query_keys,
            _defaults=default_keys,
        )

        if not created:
            await manage_info.update(**default_keys)

        await sender.send_message(Text(f"设置成功 {manage_info}"))

    @sub_command()
    async def delete(
        self,
        sender: CommandSender,
        protocol: Optional[str] = CLIOption(default="onebot"),
        conversation_type: str = CLIArgument(),
        source_id: str = CLIArgument(),
    ):
        if conversation_type not in ("private", "group"):
            await sender.send_message(Text("mode 只能为 private 或 group"))

            return None

        query_keys = dict(
            protocol=protocol,
            conversation_type=conversation_type,
            source_id=source_id,
        )

        manage_info = await ManageInfo.objects.get(**query_keys)

        await manage_info.delete()

        await sender.send_message(Text(f"删除成功 {manage_info}"))

    @sub_command()
    async def load(
        self,
        sender: CommandSender,
        chain: MessageChain,
        prefix: str,
        alias: str,
        config: Any,
        from_config: Optional[Any] = CLIOption(),  # TODO 无法识别
    ):
        # , json_result: str = CLIArgument()

        config = cast(AIQueryConfig, config)

        logger.info(from_config)

        # logger.info(chain.pure_text)
        # logger.info(prefix)
        # logger.info(alias)

        # if from_config is not None or from_config is not False:
        if from_config:
            result = config.specified_times

        else:
            # TODO 如何优雅的获取不带参数的命令的剩余部分
            json_result = chain.pure_text.replace(f"{prefix}{alias} load", "").strip()

            # result = json.loads(json_result)

            result = parse_raw_as(
                Dict[
                    Tuple[
                        T_BotProtocol,
                        T_ConversationType,
                        str,
                        T_ModelName,
                    ],
                    Union[int, None, Literal[True]],
                ],
                json_result,
            )

        for key, times in result.items():
            protocol, conversation_type, source_id, model = key

            manage_info, created = await ManageInfo.objects.get_or_create(
                protocol=protocol,
                conversation_type=conversation_type,
                source_id=source_id,
            )

            old_times = manage_info.times
            new_times = old_times.copy()
            if isinstance(times, int):
                new_times[model] = times

            # 冲突了就覆盖
            await manage_info.update(
                times=new_times,
                unlimited=times is True,
                forbidden=times is None,
            )

        await sender.send_message(Text(f"导入成功, {len(result)} 条记录"))

    @sub_command()
    async def dump(self, sender: CommandSender):
        items = await ManageInfo.objects.all()

        result = []
        for item in items:
            result.append(item.dict())

        await sender.send_message(
            Text(json.dumps(result, ensure_ascii=False, indent=4)),
        )

    async def catch(self, sender: CommandSender, exception: Exception):
        await sender.send_message(
            At(sender.user_id),
            Text(f"发生异常 {exception}"),
        )
