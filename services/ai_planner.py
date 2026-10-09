import json
import re
from typing import Any

from openai import OpenAI

from config import settings

# ── AI 客户端（兼容 DeepSeek / OpenAI） ──
# 如果换回 OpenAI，只需把 base_url 去掉，或改为 https://api.openai.com/v1
client = OpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url="https://api.deepseek.com",
)

# ── System Prompt ──
_SYSTEM_PROMPT = """你是一个目标拆解助手。用户会给你一个目标，你需要将其拆解为 8~12 个具体可执行的任务步骤。

请严格按照以下 JSON 格式返回，不要包含任何其他文字、解释或 markdown 代码块标记：

{
  "plan": [
    {
      "step": 1,
      "task": "任务描述",
      "priority": "high",
      "estimated_minutes": 30,
      "why": "为什么要做这个步骤"
    }
  ]
}

要求：
- priority 必须是 "high"、"medium" 或 "low" 之一
- estimated_minutes 是正整数，表示预估分钟数
- 每个步骤的 why 字段说明该步骤对实现目标的必要性
- 总耗时建议控制在 2~8 小时之间"""

# ── 单个任务字段的默认值 ──
_DEFAULT_PRIORITY = "medium"
_DEFAULT_ESTIMATED_MINUTES = 30
_REQUIRED_FIELDS = {"step", "task", "priority", "estimated_minutes", "why"}


def _build_messages(goal_title: str, feedback: str | None = None) -> list[dict[str, str]]:
    """构造发送给 AI 的消息列表。"""
    user_content = f"请将以下目标拆解为具体任务步骤：\n\n{goal_title}"

    if feedback:
        user_content += f"\n\n请注意以下反馈，重新调整任务拆解：\n{feedback}"

    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def _extract_json(text: str) -> str:
    """从 AI 返回文本中提取 JSON 字符串（去除可能的 markdown 代码块标记）。"""
    # 尝试匹配 ```json ... ``` 代码块
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # 否则直接当作纯 JSON 处理
    return text.strip()


def _validate_and_fix_task(task: dict[str, Any], step_index: int) -> dict[str, Any]:
    """校验单个任务字段，缺失时补充默认值。"""
    missing = _REQUIRED_FIELDS - set(task.keys())
    if missing:
        print(f"[WARN] 第 {step_index + 1} 个任务缺少字段: {missing}，将补充默认值")

    return {
        "step": task.get("step", step_index + 1),
        "task": task.get("task", ""),
        "priority": task.get("priority", _DEFAULT_PRIORITY),
        "estimated_minutes": task.get("estimated_minutes", _DEFAULT_ESTIMATED_MINUTES),
        "why": task.get("why", ""),
    }


def _parse_plan(response_text: str) -> list[dict[str, Any]]:
    """解析 AI 返回文本，提取并校验任务列表。"""
    json_str = _extract_json(response_text)
    data: dict[str, Any] = json.loads(json_str)

    plan: list[dict[str, Any]] = data.get("plan", [])
    if not plan:
        raise ValueError("解析成功，但 plan 数组为空或不存在")

    return [_validate_and_fix_task(task, i) for i, task in enumerate(plan)]


def generate_plan(goal_title: str, feedback: str | None = None) -> list[dict[str, Any]]:
    """调用 AI 将目标拆解为 8~12 个具体任务。

    参数:
        goal_title: 用户输入的目标标题。
        feedback:   可选的用户反馈，用于重新调整任务拆解。

    返回:
        任务列表，每个任务包含 step / task / priority / estimated_minutes / why。

    异常:
        RuntimeError: API 调用或 JSON 解析连续失败时抛出。
    """
    messages = _build_messages(goal_title, feedback)
    last_error: Exception | None = None

    # 最多尝试 2 次（首次 + 1 次重试）
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                temperature=0.3,          # 较低温度，输出更稳定
                # response_format={"type": "json_object"},  # 如果模型支持可取消注释
            )
            content: str = response.choices[0].message.content
            return _parse_plan(content)

        except (json.JSONDecodeError, ValueError, KeyError, TypeError) as e:
            last_error = e
            print(f"[WARN] 第 {attempt + 1} 次尝试解析失败: {e}")
            # 重试时把错误信息告诉 AI，让它修正
            messages.append({"role": "assistant", "content": content})  # type: ignore[possibly-undefined]  # noqa: F821
            messages.append({
                "role": "user",
                "content": f"你返回的数据解析失败，错误信息：{e}。请确保返回严格的 JSON，不要包含额外文字。",
            })
        except Exception as e:
            last_error = e
            print(f"[WARN] 第 {attempt + 1} 次 API 调用失败: {e}")
            # 网络类错误不需要修正消息，直接重试请求
            if attempt == 0:
                continue
            break

    raise RuntimeError(f"AI 规划生成失败，已重试 1 次仍不成功: {last_error}")
