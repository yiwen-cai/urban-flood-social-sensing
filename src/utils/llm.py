"""
LLM API 调用封装 —— 全组共用，统一处理重试和错误。

用法:
    from src.utils.llm import call_llm
    result = call_llm("请分析以下文本的情感...", model="deepseek-chat")
"""

import json
import os
import time
from typing import Any


# ====== 配置 API Key（通过环境变量设置） ======
# export DEEPSEEK_API_KEY="your-key"
# export QWEN_API_KEY="your-key"

DEFAULT_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")

# DeepSeek API 配置（兼容 OpenAI 格式）
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

# 阿里云百炼 Qwen API 配置
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


def _get_client(model: str):
    """根据模型名返回对应的 OpenAI 客户端。"""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("请先安装 openai: pip install openai")

    if "deepseek" in model.lower():
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        base_url = DEEPSEEK_BASE_URL
    elif "qwen" in model.lower():
        api_key = os.environ.get("QWEN_API_KEY", "")
        base_url = QWEN_BASE_URL
    else:
        # 兼容其他 OpenAI 格式的 API
        api_key = os.environ.get("OPENAI_API_KEY", "")
        base_url = os.environ.get("OPENAI_BASE_URL", "")

    if not api_key:
        raise ValueError(
            f"未设置 API Key。请设置环境变量，如: export DEEPSEEK_API_KEY='sk-xxx'"
        )

    return OpenAI(api_key=api_key, base_url=base_url)


def call_llm(
    prompt: str,
    model: str | None = None,
    system_prompt: str = "你是一个专业的中文文本分析助手。",
    temperature: float = 0.3,
    max_tokens: int = 2048,
    max_retries: int = 3,
) -> str:
    """调用 LLM，返回文本结果。自带重试机制。"""

    model = model or DEFAULT_MODEL
    client = _get_client(model)

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""

        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"[LLM] 调用失败 (尝试 {attempt+1}/{max_retries}): {e}，{wait}s 后重试...")
                time.sleep(wait)
            else:
                raise RuntimeError(f"LLM 调用失败（已重试 {max_retries} 次）: {e}")


def call_llm_json(
    prompt: str,
    model: str | None = None,
    system_prompt: str = "你是一个专业的中文文本分析助手。请只返回 JSON 格式的结果。",
    temperature: float = 0.1,
    max_retries: int = 3,
) -> dict[str, Any]:
    """调用 LLM 并强制返回 JSON 对象。"""
    raw = call_llm(
        prompt=prompt,
        model=model,
        system_prompt=system_prompt,
        temperature=temperature,
        max_retries=max_retries,
    )

    # 尝试提取 JSON（LLM 可能在 JSON 前后加了说明文字）
    raw = raw.strip()
    if raw.startswith("```"):
        # 去掉 markdown 代码块标记
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else raw[lines.index("") + 1 if "" in lines else 0:]

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # 尝试匹配第一个 { 到最后一个 }
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end])
        raise RuntimeError(f"LLM 返回内容无法解析为 JSON: {raw[:200]}...")
