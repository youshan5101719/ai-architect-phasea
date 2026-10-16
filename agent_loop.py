import json
from typing import Any

from openai import OpenAI

from agent_logging import agent_trace
from web_search_tool import WEB_SEARCH_TOOL_DEFINITION, web_search

MAX_TURNS = 3


def _tool_log_name(function_name: str) -> str:
    if function_name == "web_search":
        return "search"
    return function_name


def _execute_tool(function_name: str, arguments_json: str) -> str:
    if function_name != "web_search":
        return json.dumps(
            {"error": f"Unknown tool: {function_name}"},
            ensure_ascii=False,
        )

    try:
        args = json.loads(arguments_json)
    except json.JSONDecodeError as exc:
        return json.dumps(
            {"error": f"Invalid tool arguments JSON: {exc}"},
            ensure_ascii=False,
        )

    query = args.get("query")
    if not query or not str(query).strip():
        return json.dumps({"error": "Missing required argument: query"}, ensure_ascii=False)

    try:
        result = web_search(str(query).strip())
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


def _format_log_preview(text: str, limit: int = 800) -> str:
    compact = text.replace("\n", " ").strip()
    if len(compact) <= limit:
        return compact
    return compact[:limit] + "..."


def run_agent_chat(
    client: OpenAI,
    *,
    model: str,
    user_message: str,
    max_turns: int = MAX_TURNS,
) -> str:
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]
    agent_trace(f"[Agent] Starting loop (max_turns={max_turns})")

    for turn in range(1, max_turns + 1):
        agent_trace(f"[Agent] Turn {turn}/{max_turns}")
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=[WEB_SEARCH_TOOL_DEFINITION],
            tool_choice="auto",
        )

        if not completion.choices:
            raise RuntimeError("模型未返回任何候选回复。")

        choice = completion.choices[0]
        message = choice.message
        tool_calls = message.tool_calls or []

        if not tool_calls:
            final = message.content or ""
            agent_trace(f"[Agent] Final Answer: '{_format_log_preview(final)}'")
            return final

        messages.append(message.model_dump(exclude_none=True))

        for call in tool_calls:
            fn_name = call.function.name
            agent_trace(f"[Agent] Decided to call tool: '{_tool_log_name(fn_name)}'")
            tool_output = _execute_tool(fn_name, call.function.arguments)
            agent_trace(f"[System] Tool Output: '{_format_log_preview(tool_output)}'")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": tool_output,
                }
            )

    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=[WEB_SEARCH_TOOL_DEFINITION],
        tool_choice="none",
    )
    if not completion.choices:
        raise RuntimeError("模型未返回最终回复。")

    final = completion.choices[0].message.content or ""
    agent_trace(f"[Agent] Final Answer: '{_format_log_preview(final)}'")
    return final
