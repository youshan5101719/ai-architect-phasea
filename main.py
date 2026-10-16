import os
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from openai import OpenAI
from pydantic import BaseModel, Field

from agent_logging import agent_trace, setup_agent_logging, trace_file_path
from agent_loop import run_agent_chat
from web_search_tool import WEB_SEARCH_TOOL_DEFINITION

load_dotenv()

CHAT_BASE_URL = "https://space.ai-builders.com/backend/v1"
CHAT_MODEL = "gpt-5"


def get_chat_client() -> OpenAI:
    api_key = os.getenv("SUPER_MIND_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="未配置 SUPER_MIND_API_KEY，请在项目根目录的 .env 文件中设置。",
        )
    return OpenAI(api_key=api_key, base_url=CHAT_BASE_URL)


class ChatRequest(BaseModel):
    user_message: str = Field(..., description="发送给模型的用户消息。")


class ChatResponse(BaseModel):
    content: str = Field(..., description="助手回复的文本内容。")


class ToolProbeRequest(BaseModel):
    user_message: str = Field(
        default="Who won the Super Bowl?",
        description="用户问题；用于探测模型是否会发起 web_search 工具调用。",
    )


class ToolProbeResponse(BaseModel):
    finish_reason: str | None = Field(
        None, description="模型结束原因，例如 tool_calls 或 stop。"
    )
    content: str | None = Field(None, description="若无工具调用时的文本回复。")
    tool_calls: list[dict[str, Any]] = Field(
        default_factory=list,
        description="模型返回的工具调用列表（OpenAI tool_calls 结构）。",
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_agent_logging()
    agent_trace(
        "[System] Agent logging enabled — POST /chat logs appear in THIS terminal "
        f"(backup file: {trace_file_path()})"
    )
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Hello API 入门示例",
    description="""
## 这个页面是干什么的？

这是 **Swagger UI**（也叫 OpenAPI 文档页）。你可以在这里**不用写代码**就试一遍每个接口是否正常。

---

## 新手操作步骤（必读）

1. **找到接口**：在下方列表里找到 **`GET /`**（获取问候消息）。
2. **展开**：点击这一行左侧的箭头，或点击整行，展开详情。
3. **进入试用模式**：点击右侧 **「Try it out」**（试试看）。  
   - 若界面是英文，按钮含义同上：Try it out = 允许你改参数并发送请求。
4. **填写参数**：在 **input** 输入框里填入你想出现在问候语里的文字，例如 `World`、`小明`。
   - 不填则使用默认值 `World`。
5. **发送请求**：点击 **「Execute」**（执行）。
6. **看结果**：向下滚动到 **Responses**（响应）区域：
   - **Code 200** 表示成功；
   - **Response body** 里是服务器返回的 JSON，例如 `{"message": "Hello, 小明"}`。

---

## 不用这个页面怎么访问？

在浏览器地址栏直接访问（把 `<input>` 换成你的文字）：

`http://127.0.0.1:8000/?input=<input>`

例如：`http://127.0.0.1:8000/?input=FastAPI`

---

## 另一种文档样式

若更喜欢「说明书」式排版，可打开：**[/redoc](/redoc)**（ReDoc 文档页，只读，不能点 Execute 试接口）。
""",
    version="0.1.0",
    openapi_tags=[
        {
            "name": "问候",
            "description": "返回 JSON 格式的问候语，适合作为 FastAPI 第一个接口练习。",
        },
        {
            "name": "对话",
            "description": "调用 OpenAI 兼容的 Chat Completions API（模型 gpt-5）。",
        },
        {
            "name": "工具",
            "description": "Web 搜索工具定义与 LLM 工具调用探测。",
        },
    ],
    swagger_ui_parameters={
        "docExpansion": "list",
        "defaultModelsExpandDepth": 1,
        "tryItOutEnabled": False,
    },
)


@app.get(
    "/",
    tags=["问候"],
    summary="获取问候消息",
    description="""
根据查询参数 **input** 返回 JSON：

```json
{"message": "Hello, <input>"}
```

**示例**

| input 参数值 | 返回的 message |
|-------------|----------------|
| （不填，默认 World） | Hello, World |
| 小明 | Hello, 小明 |
| FastAPI | Hello, FastAPI |
""",
    response_description="成功：JSON 对象，字段 message 为问候字符串。",
)
def hello(
    input: str = Query(
        default="World",
        title="问候内容",
        description=(
            "会原样出现在 message 里，格式为「Hello, 」加上本参数。"
            "例如填 World 得到 Hello, World；填你的名字即可个性化问候。"
        ),
        examples=["World", "小明", "FastAPI"],
    ),
) -> dict[str, str]:
    return {"message": f"Hello, {input}"}


@app.post(
    "/chat",
    tags=["对话"],
    summary="Chat Completions 对话",
    description=(
        "Agent 对话：模型可调用 **web_search**，最多 **3** 轮工具循环，"
        "最终将助手文本以 `{\"content\": \"...\"}` 返回。控制台会输出 Agent 决策与工具结果日志。"
    ),
    response_description="成功：JSON 对象，字段 content 为助手回复。",
)
def chat(request: ChatRequest) -> ChatResponse:
    agent_trace(f"[Agent] POST /chat user_message={request.user_message!r}")
    client = get_chat_client()
    try:
        content = run_agent_chat(
            client,
            model=CHAT_MODEL,
            user_message=request.user_message,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Agent 对话失败：{exc}",
        ) from exc

    if not content.strip():
        raise HTTPException(status_code=502, detail="模型未返回文本内容。")

    return ChatResponse(content=content)


def _serialize_tool_calls(message: Any) -> list[dict[str, Any]]:
    raw_calls = getattr(message, "tool_calls", None) or []
    serialized: list[dict[str, Any]] = []
    for call in raw_calls:
        serialized.append(
            {
                "id": call.id,
                "type": call.type,
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                },
            }
        )
    return serialized


@app.post(
    "/chat/tool-probe",
    tags=["工具"],
    summary="探测 LLM 是否会发起 web_search 工具调用",
    description=(
        "向模型注册 **web_search** 工具 schema，发送 **user_message**，"
        "仅返回模型侧的 tool_calls（不调用 web_search、不跑 agent 循环）。"
    ),
    response_description="包含 tool_calls 与 finish_reason 的 JSON。",
)
def chat_tool_probe(request: ToolProbeRequest) -> ToolProbeResponse:
    client = get_chat_client()
    try:
        completion = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": request.user_message}],
            tools=[WEB_SEARCH_TOOL_DEFINITION],
            tool_choice="auto",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"调用 Chat Completions API 失败：{exc}",
        ) from exc

    if not completion.choices:
        raise HTTPException(status_code=502, detail="模型未返回任何候选回复。")

    choice = completion.choices[0]
    message = choice.message
    tool_calls = _serialize_tool_calls(message)

    return ToolProbeResponse(
        finish_reason=choice.finish_reason,
        content=message.content,
        tool_calls=tool_calls,
    )
