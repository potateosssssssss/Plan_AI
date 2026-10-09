from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Goal, Task, User
from schemas import GoalCreate, GoalOut, GoalRegenerate, TaskOut, TaskUpdate
from services.ai_planner import generate_plan

router = APIRouter(prefix="/goals", tags=["goals"])


# ─── 辅助函数 ───


def _get_user_goal(goal_id: int, user: User, db: Session) -> Goal:
    """按 ID 查找目标，并验证归属当前用户，否则抛 404 或 403。"""
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if goal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="目标不存在",
        )
    if goal.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问该目标",
        )
    return goal


def _update_goal_completed_if_all_done(goal: Goal, db: Session) -> None:
    """如果目标下的所有任务都是 done，则将目标状态设为 completed。"""
    remaining = (
        db.query(Task)
        .filter(Task.goal_id == goal.id, Task.status != "done")
        .count()
    )
    if remaining == 0:
        goal.status = "completed"
        db.flush()


# ─── 端点 ───


@router.post("/", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
def create_goal(
    goal_in: GoalCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建新目标，调用 AI 拆解为任务步骤并存入数据库。"""
    # 调用 AI 获取任务规划
    plan = generate_plan(goal_in.title)

    # 创建目标
    goal = Goal(title=goal_in.title, user_id=user.id)
    db.add(goal)
    db.flush()  # 获取 goal.id

    # 创建任务
    tasks: list[Task] = []
    for item in plan:
        task = Task(
            goal_id=goal.id,
            step_order=item["step"],
            title=item["task"],
            priority=item["priority"],
            estimated_minutes=item["estimated_minutes"],
            why_explanation=item.get("why"),
        )
        db.add(task)
        tasks.append(task)

    db.commit()
    db.refresh(goal)
    return goal


@router.get("/", response_model=list[GoalOut])
def list_goals(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(20, ge=1, le=100, description="每页条数"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """分页查询当前用户的 active 目标列表。"""
    goals = (
        db.query(Goal)
        .filter(Goal.user_id == user.id, Goal.status == "active")
        .offset(skip)
        .limit(limit)
        .all()
    )
    return goals


@router.get("/{goal_id}", response_model=GoalOut)
def get_goal(
    goal_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取单个目标的详细信息（含所有任务）。"""
    goal = _get_user_goal(goal_id, user, db)
    return goal


@router.get("/{goal_id}/next")
def get_next_task(
    goal_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取目标的下一个未完成任务（按 step_order 排序）。"""
    goal = _get_user_goal(goal_id, user, db)

    task = (
        db.query(Task)
        .filter(Task.goal_id == goal.id, Task.status != "done")
        .order_by(Task.step_order)
        .first()
    )

    if task is None:
        return {"message": "全部完成"}

    return TaskOut.model_validate(task)


@router.put("/{goal_id}/tasks/{task_id}", response_model=TaskOut)
def update_task(
    goal_id: int,
    task_id: int,
    task_in: TaskUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新任务的执行状态；若全部完成则自动关闭目标。"""
    goal = _get_user_goal(goal_id, user, db)

    task = db.query(Task).filter(Task.id == task_id, Task.goal_id == goal.id).first()
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在",
        )

    # 仅当有值时才更新
    if task_in.status is not None:
        task.status = task_in.status

    db.flush()
    _update_goal_completed_if_all_done(goal, db)
    db.commit()
    db.refresh(task)
    return task


@router.post("/{goal_id}/regenerate", response_model=GoalOut)
def regenerate_goal(
    goal_id: int,
    regen_in: GoalRegenerate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """根据 AI 重新规划目标，删除旧任务并插入新任务。"""
    goal = _get_user_goal(goal_id, user, db)

    # 调用 AI 重新规划
    plan = generate_plan(goal.title, feedback=regen_in.feedback)

    # 删除旧任务
    db.query(Task).filter(Task.goal_id == goal.id).delete()

    # 插入新任务
    for item in plan:
        task = Task(
            goal_id=goal.id,
            step_order=item["step"],
            title=item["task"],
            priority=item["priority"],
            estimated_minutes=item["estimated_minutes"],
            why_explanation=item.get("why"),
        )
        db.add(task)

    # 重置目标状态为 active
    goal.status = "active"
    db.commit()
    db.refresh(goal)
    return goal
