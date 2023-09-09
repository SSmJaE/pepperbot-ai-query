
<h1 align="center">PepperBot AI Query</h1>

<p align="center">
一个基于PepperBot，可以保留上下文的LLM群聊机器人实现
</p>

## 支持的模型

- ChatGPT
  - 3.5
  - 4.0
- [ ] Bing
- [ ] 文心一言
- [ ] 文字生成图片
- [ ] 赋予LLM联网能力
  - [ ] langChain等

## 功能

- 自带管理指令，可以直接通过私聊设置超级用户，无需硬编码
  - 可以直接通过命令，从聊天窗口获取所有配置
- 可以动态为每个用户，设置每个模型的调度次数

## 如何使用？

先保证你能正常的运行起来PepperBot + go-cqhttp(如果针对QQ的话)，具体见PepperBot的文档

然后，通过包管理器安装本项目

```bash
pip install pepperbot-ai-query
```

或者

```bash
pdm add pepperbot-ai-query
```

在你的入口文件中，添加如下代码

```python

from pepperbot.extensions.command import as_command

from pepperbot_ai_query import (
    AIQuery,
    AIQueryConfig,
    AIQueryManage,
    AIUsage,
    EnsureNotQuerying,
    IsActive,
    reset_user_count,
)
```

可以直接设置config
具体如何设置，见`config.py`

proxy_token是为了避免代理被滥用，需要是PepperBot群员才能调用

自己实现proxy_call的话，可以不用设置token

```python
async def query_gpt(messages:list[str]):
    """ 自己实现调用GPT API的方法 """
    return completion

config = AIQueryConfig(
    specified_times={
        ("onebot", "group", "819441084", "gpt-3.5"): 10,
        ("onebot", "group", "625979029", "gpt-3.5"): True,
        ("onebot", "private", "1269266841", "gpt-3.5"): True,
        ("onebot", "private", "1229542349", "gpt-3.5"): True,
        ("onebot", "private", "746701235", "gpt-3.5"): True,
    },
    default_times_per_model={
        "gpt-3.5": 5,
    },
)
```

如果有比较敏感的信息，比如token，可以通过环境变量，不保留明文
默认需要带前缀，比如

需要在`根目录`新建一个`.env`文件

```env
pepperbot_ai_query_proxy_token="jsklfjklajfklds"
```

也可以直接通过环境变量设置，大小写是无所谓的

```bash
export pepperbot_ai_query_proxy_token="jsklfjklajfklds"
```

然后，在这些指令的配置中，都需要指明使用的config

- `AIQuery`，负责实际的交互能力
- `AIUsage`，用户可以查看模型调用情况
- `AIQueryManage`，给管理员使用，可以设置超级用户

```python
ai_query_command = as_command(
    need_prefix=True,
    prefixes=["/"],
    aliases=["gpt", "ai"],
    include_class_name=False,
    require_at=False,
    timeout=90,
    priority=400,
    config=config,
    concurrency=False,
    propagation_group="gpt",
    interactive_strategy="any_source_same_user",
)(AIQuery)

ai_usage_command = as_command(
    need_prefix=True,
    prefixes=["/"],
    aliases=["ai-usage"],
    include_class_name=False,
    require_at=False,
    timeout=10,
    # priority=400,
    config=config,
    propagation_group="gpt",
)(AIUsage)

ai_manage_command = as_command(
    need_prefix=True,
    prefixes=["/"],
    aliases=["ai-manage"],
    include_class_name=False,
    require_at=False,
    timeout=10,
    # priority=400,
    config=config,
    propagation_group="gpt",
)(AIQueryManage)

bot.apply_routes(
    [
        BotRoute(
            handlers=(EnsureNotQuerying, IsActive),
            commands=[ai_query_command, ai_usage_command],
            groups={
                "onebot": [
                    "...",
                ],
                "telegram": "*",
            },
            friends={
                "onebot": [
                    "...",
                ],
                "telegram": "*",
            },
        ),
    ]
)

```

## 权限管理

`/ai-manage`

- list
- set
- delete
- load
- dump
