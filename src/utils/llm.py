"""
LLM API 调用封装 —— 单一模型、结构化 JSON 输出、指数退避重试。

用法:
    from src.utils.llm import get_client, classify_batch
    client = get_client()
    results = classify_batch(client, posts, system_prompt, output_schema)
"""

import json
import os
import time
import uuid
from typing import Any

# ====== 配置 ======
# 模型通过环境变量选择：QWEN_API_KEY 或 DEEPSEEK_API_KEY
# 谁有 Key 就用谁，不要求两人都配

DEFAULT_MODEL = os.environ.get("LLM_MODEL", "qwen-plus")


def get_client(model: str | None = None):
    """返回 OpenAI 兼容客户端。根据环境变量自动选择 Qwen 或 DeepSeek。"""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("请先安装 openai: pip install openai")

    model = model or DEFAULT_MODEL

    if "qwen" in model.lower():
        api_key = os.environ.get("QWEN_API_KEY", "")
        base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    elif "deepseek" in model.lower():
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        base_url = "https://api.deepseek.com/v1"
    else:
        api_key = os.environ.get("OPENAI_API_KEY", "")
        base_url = os.environ.get("OPENAI_BASE_URL", "")

    if not api_key:
        raise ValueError(
            "未设置 API Key。请设置环境变量:\n"
            "  export QWEN_API_KEY='sk-xxx'   # 阿里云百炼\n"
            "  export DEEPSEEK_API_KEY='sk-xxx'  # DeepSeek"
        )

    return OpenAI(api_key=api_key, base_url=base_url), model


def call_llm(
    client,
    model: str,
    prompt: str,
    system_prompt: str,
    temperature: float = 0.0,
    max_tokens: int = 2048,
    max_retries: int = 3,
    response_format: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    调用 LLM，返回 (raw_text, usage_dict)。
    温度固定为 0，保证可复现。
    指数退避重试：1s → 2s → 4s。
    """

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    # 如果模型支持 JSON 模式，开启 structured output
    if response_format:
        kwargs["response_format"] = response_format

    last_error = None
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(**kwargs)
            text = resp.choices[0].message.content or ""
            usage = {
                "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
                "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
                "model": resp.model,
            }
            return text, usage
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"  [LLM] 重试 {attempt+1}/{max_retries}: {e}，{wait}s 后重试...")
                time.sleep(wait)
            else:
                raise RuntimeError(
                    f"LLM 调用失败（已重试 {max_retries} 次）: {last_error}"
                ) from last_error

    raise RuntimeError(f"LLM 调用失败: {last_error}")


def extract_json(text: str) -> dict[str, Any]:
    """从 LLM 返回值中提取 JSON 对象。兼容 markdown 代码块包裹。"""
    text = text.strip()
    # 去除 ```json ... ``` 包裹
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[-1].strip() == "```":
            text = "\n".join(lines[1:-1])
        else:
            text = "\n".join(lines[1:])

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试匹配第一个 { 到最后一个 }
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        return json.loads(text[start:end])

    raise ValueError(f"无法从 LLM 输出中提取 JSON: {text[:300]}...")


def generate_run_id() -> str:
    """生成唯一 pipeline_run_id。"""
    return f"run-{uuid.uuid4().hex[:12]}"
