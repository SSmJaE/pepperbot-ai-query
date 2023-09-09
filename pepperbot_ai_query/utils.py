from re import A
from typing import Optional, Tuple
from devtools import debug
from pepperbot import logger
from pepperbot.core.message.chain import MessageChain
from pepperbot.core.message.segment import At, Text
from pepperbot.extensions.command.sender import CommandSender

from pepperbot_ai_query.config import (
    AIQueryConfig,
    T_ModelName,
    generate_empty_model_count,
)
from pepperbot_ai_query.orm import ManageInfo, UsageInfo


async def get_usage_info(chain: MessageChain):
    """跨消息来源锁定"""

    query_keys = dict(
        protocol=chain.protocol,
        user_id=chain.user_id,
    )

    usage_info, created = await UsageInfo.objects.get_or_create(
        **query_keys,
        _defaults={
            **query_keys,
            "count": generate_empty_model_count(),
        },
    )

    return usage_info


async def get_manage_info(sender: CommandSender):
    manage_info = None

    if sender.mode == "group":
        manage_info = await ManageInfo.objects.get_or_none(
            protocol=sender.protocol,
            conversation_type="group",
            source_id=sender.source_id,
        )

        if not manage_info:
            manage_info = await ManageInfo.objects.get_or_none(
                protocol=sender.protocol,
                conversation_type="private",
                source_id=sender.user_id,
            )

    elif sender.mode == "private":
        manage_info = await ManageInfo.objects.get_or_none(
            protocol=sender.protocol,
            conversation_type="private",
            source_id=sender.user_id,
        )

    return manage_info


def get_times(
    usage_info: UsageInfo,
    manage_info: Optional[ManageInfo],
    sender: CommandSender,
    config: AIQueryConfig,
    model_name: T_ModelName,
) -> Tuple[bool, Optional[bool], int]:
    """

    return:
        continue_flag: 是否继续
        unlimited = True, forbidden = False , 其他 = None
        max_times: 最大次数
    """

    continue_flag = False

    if manage_info:  # 如果在special_times中设置过，会生成ManageInfo，这里判断
        if manage_info.forbidden:
            return False, False, 0

        if manage_info.unlimited:
            logger.info("超级用户或超级群组，无次数限制")

            return True, True, 0

        max_times = manage_info.times.get(model_name, 0)

    else:  # 未手动设置过，使用默认设置
        usage_info.permission.setdefault("active", False)
        usage_info.permission.setdefault("cross_source", False)

        # 默认次数
        max_times = config.default_times_per_model.get(model_name, 0)

        # 活跃奖励
        if usage_info.permission["active"]:
            max_times += 5

            # 非常活跃奖励
            if usage_info.permission["cross_source"]:
                max_times += 5

    current_times = usage_info.count.get(model_name, 0)

    if current_times >= max_times:
        continue_flag = False
    else:
        continue_flag = True

    return continue_flag, None, max_times


async def admin_only(chain: MessageChain, sender: CommandSender):
    """仅管理员可用"""

    if sender.user_id == "1234567890":
        return True

    await sender.send_message(
        At(chain.user_id),
        Text("仅管理员可用"),
    )

    return False


async def reset_user_count():
    """重置每天调用次数"""

    await UsageInfo.objects.update(each=True, count=generate_empty_model_count())
