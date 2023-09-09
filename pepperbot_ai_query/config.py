from typing import Any, Callable, Coroutine, Dict, List, Literal, Optional, Tuple, Union

from pepperbot.types import T_BotProtocol, T_ConversationType
from pydantic import BaseSettings

T_ModelName = Literal["gpt-3.5", "wenxin", "stable-diffusion", "llama2"]


class ModelNames:
    gpt_3_5: T_ModelName = "gpt-3.5"
    wenxin: T_ModelName = "wenxin"
    stable_diffusion: T_ModelName = "stable-diffusion"
    llama2: T_ModelName = "llama2"


def generate_empty_model_count() -> Dict[T_ModelName, int]:
    return {
        ModelNames.gpt_3_5: 0,
        ModelNames.wenxin: 0,
        ModelNames.stable_diffusion: 0,
        ModelNames.llama2: 0,
    }


class AIQueryConfig(BaseSettings):
    class Config:
        env_file = ".env"  # 必须手动指定
        env_file_encoding = "utf-8"
        env_prefix = "pepperbot_ai_query_"
        env_nested_delimiter = "__"

        arbitrary_types_allowed = True  # 针对specified_times

    proxy_call: Optional[Callable[[List[Dict]], Coroutine[Any, Any, str]]] = None
    """ 如何调用GPT，输入messages，返回当前的completion """

    openai_token: Optional[str] = None
    """ openai的token 
    
    直接提供token + proxy_token，或者自己实现proxy_call，二选一
    """
    proxy_token: Optional[str] = None
    """ 如果使用群内的GPT代理，需要提供token，证明是PepperBot群员，避免滥用 """

    default_times_per_model: Dict[str, int] = {
        ModelNames.gpt_3_5: 5,
        ModelNames.wenxin: 5,
        ModelNames.stable_diffusion: 5,
        ModelNames.llama2: 5,
    }
    """ 每天每个用户最多调用次数，通过设置interactive_strategy跨群锁定用户 
    
    如果未在specified_times中设置，则使用此值
    """
    specified_times: Dict[
        Tuple[
            T_BotProtocol,
            T_ConversationType,
            str,
            T_ModelName,
        ],
        Union[int, None, bool],
    ] = {}
    """ 
    {
        (protocol, conversation_type, source_id, model) : 每天每个消息来源最多调用次数，None禁用，True无限制
        protocol: 协议，如onebot
        conversation_type: 会话类型，如group, private
        source_id: 会话id，如群号，QQ号
    }
    """


# gpt_example_setting = AISetting()
