from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


# ─────────────────── 用户 ───────────────────


class UserCreate(BaseModel):
    """用户注册请求体"""

    username: str
    password: str


class UserResponse(BaseModel):
    """用户信息响应体，配置 from_attributes 以支持从 ORM 对象转换"""

    id: int
    username: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────── 认证 ───────────────────


class Token(BaseModel):
    """JWT Token 响应体"""

    access_token: str
    token_type: str


# ─────────────────── 目标 ───────────────────


class GoalCreate(BaseModel):
    """创建目标的请求体"""

    title: str


class GoalRegenerate(BaseModel):
    """重新规划目标的请求体（可选附带反馈信息）"""

    feedback: str | None = None


# ─────────────────── 任务 ───────────────────


class TaskOut(BaseModel):
    """任务输出模型"""

    id: int
    goal_id: int
    step_order: int
    title: str
    priority: str
    estimated_minutes: int
    why_explanation: str | None
    status: str

    model_config = ConfigDict(from_attributes=True)


class TaskUpdate(BaseModel):
    """更新任务状态的请求体，status 只能取三个枚举值之一"""

    status: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is None:
            return v
        allowed = {"not_started", "in_progress", "done"}
        if v not in allowed:
            raise ValueError(f"status 必须是 {allowed} 中的一个，但收到了：{v}")
        return v


class GoalOut(BaseModel):
    """目标及其关联任务的完整输出模型"""

    id: int
    title: str
    status: str
    created_at: datetime
    updated_at: datetime
    tasks: list[TaskOut]

    model_config = ConfigDict(from_attributes=True)
