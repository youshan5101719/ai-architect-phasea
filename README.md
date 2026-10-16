# AI Architect — Phase A

FastAPI 入门项目：问候接口与 OpenAI 兼容的 Chat Completions 代理。

## 本地运行

```bash
pip install -r requirements.txt
cp .env.example .env   # 填入 SUPER_MIND_API_KEY
uvicorn main:app --reload
```

- 文档：http://127.0.0.1:8000/docs
- `GET /` — 问候语
- `POST /chat` — 转发到 `gpt-5`（需配置 `.env`）

## 环境变量

| 变量 | 说明 |
|------|------|
| `SUPER_MIND_API_KEY` | Chat API 密钥（勿提交 `.env`） |
