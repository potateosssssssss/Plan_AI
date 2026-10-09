from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    """用户表"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # 一个用户可以有多个目标
    goals = relationship("Goal", back_populates="user", cascade="all, delete-orphan")


class Goal(Base):
    """目标表"""

    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    status = Column(String(20), default="active", nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    # 关联关系
    user = relationship("User", back_populates="goals")
    tasks = relationship("Task", back_populates="goal", cascade="all, delete-orphan")


class Task(Base):
    """任务步骤表"""

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=False)
    step_order = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    priority = Column(String(20), nullable=False)          # 例如 high / medium / low
    estimated_minutes = Column(Integer, nullable=False)    # 预估完成分钟数
    why_explanation = Column(Text, nullable=True)          # 为什么做这个步骤
    status = Column(String(20), default="not_started", nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    # 关联关系
    goal = relationship("Goal", back_populates="tasks")

    # 同一个目标下，步骤序号不能重复
    __table_args__ = (
        UniqueConstraint("goal_id", "step_order", name="uq_goal_step_order"),
    )
