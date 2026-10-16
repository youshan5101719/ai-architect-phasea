import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from openai import OpenAI
from pydantic import BaseModel, Field

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


app = FastAPI(
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
        "将请求体中的 **user_message** 发给远端 Chat Completions 接口（模型 **gpt-5**），"
        "并返回助手回复文本，格式为 `{\"content\": \"...\"}`。"
    ),
    response_description="成功：JSON 对象，字段 content 为助手回复。",
)
def chat(request: ChatRequest) -> ChatResponse:
    client = get_chat_client()
    try:
        completion = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": request.user_message}],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"调用 Chat Completions API 失败：{exc}",
        ) from exc

    message = completion.choices[0].message.content
    if message is None:
        raise HTTPException(status_code=502, detail="模型未返回文本内容。")

    return ChatResponse(content=message)
