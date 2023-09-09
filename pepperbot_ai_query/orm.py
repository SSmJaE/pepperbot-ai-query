from typing import Any, Dict, cast

import ormar
from pepperbot.store.orm import database, metadata
from sanic import Forbidden

from pepperbot_ai_query.config import ModelNames, T_ModelName


class UsageInfo(ormar.Model):
    class Meta:
        tablename = "usage_info"
        database = database
        metadata = metadata

    id: int = cast(int, ormar.Integer(primary_key=True))
    count: Dict[T_ModelName, int] = cast(dict, ormar.JSON(default=dict))
    """ 每天调用次数，会清零重置；key为model，value为次数 """
    history_count: Dict[T_ModelName, int] = cast(dict, ormar.JSON(default=dict))
    """ 历史调用次数，不清零；key为model，value为次数 """
    querying: bool = cast(bool, ormar.Boolean(default=False))

    # 这里不需要conversation_type，因为想跨消息来源锁定
    protocol: str = cast(str, ormar.String(max_length=20))
    user_id: str = cast(str, ormar.String(max_length=20))
    """ 用户账号，暂时不处理跨应用(QQ、微信、TG)的情况 """

    current_model: T_ModelName = cast(
        T_ModelName, ormar.String(max_length=30, default=ModelNames.gpt_3_5)
    )

    history_messages_text: list = cast(list, ormar.JSON(default=list))
    """ 用来判断是否发送了不一致的消息，判断活跃度
     (conversation_type, source_id, message)
      
        """

    permission: dict = cast(dict, ormar.JSON(default=dict))
    """ 用来判断是否有对应权限，key为model，value为bool 
    
    可以用来判断活跃度
    """


class ManageInfo(ormar.Model):
    """这些信息，是手动设定的，不应该动态修改"""

    class Meta:
        tablename = "manage_info"
        database = database
        metadata = metadata

    id: int = cast(int, ormar.Integer(primary_key=True))

    protocol: str = cast(str, ormar.String(max_length=20))
    conversation_type: str = cast(str, ormar.String(max_length=20))
    """ user或者group """
    source_id: str = cast(str, ormar.String(max_length=20))
    """ 可以是群号、QQ号 """

    unlimited: bool = cast(bool, ormar.Boolean(default=False))
    forbidden: bool = cast(bool, ormar.Boolean(default=False))
    times: Dict[T_ModelName, int] = cast(dict, ormar.JSON(default=dict))
    """ 允许的调用次数；key为model，value为次数 """
