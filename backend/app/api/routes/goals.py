import uuid
from datetime import date

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models import Goal
from app.schemas.engagement import GoalIn, GoalOut, GoalProgress, GoalUpdate
from app.services import achievements
from app.services import goals as service

router = APIRouter(prefix="/goals", tags=["goals"])


def _out(db, goal: Goal) -> GoalOut:
    progress = service.evaluate(db, goal)
    return GoalOut.model_validate(
        {**{c: getattr(goal, c) for c in GoalOut.model_fields if c != "progress"}, "progress": GoalProgress(**progress)}
    )


def _owned(db, user, goal_id: uuid.UUID) -> Goal:
    goal = db.get(Goal, goal_id)
    if goal is None or goal.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Goal not found")
    return goal


@router.get("", response_model=list[GoalOut])
def list_goals(user: CurrentUser, db: DbSession) -> list[GoalOut]:
    goals = db.scalars(select(Goal).where(Goal.user_id == user.id).order_by(Goal.created_at.desc())).all()
    out = [_out(db, g) for g in goals]
    db.commit()  # persist any status transitions (achieved / missed)
    achievements.check_and_award(db, user)
    return out


@router.post("", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
def create_goal(payload: GoalIn, user: CurrentUser, db: DbSession) -> GoalOut:
    baseline = payload.baseline_monthly_kg
    if baseline is None:
        baseline = service.default_baseline(db, user, payload.category)
    if baseline <= 0:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "No tracked emissions in the last 30 days for this scope — log activities or provide a baseline.",
        )
    goal = Goal(
        user_id=user.id,
        title=payload.title,
        category=payload.category,
        baseline_monthly_kg=round(baseline, 2),
        target_reduction_pct=payload.target_reduction_pct,
        start_date=payload.start_date or date.today(),
        deadline=payload.deadline,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    achievements.check_and_award(db, user)
    return _out(db, goal)


@router.get("/{goal_id}", response_model=GoalOut)
def get_goal(goal_id: uuid.UUID, user: CurrentUser, db: DbSession) -> GoalOut:
    return _out(db, _owned(db, user, goal_id))


@router.patch("/{goal_id}", response_model=GoalOut)
def update_goal(goal_id: uuid.UUID, payload: GoalUpdate, user: CurrentUser, db: DbSession) -> GoalOut:
    goal = _owned(db, user, goal_id)
    changes = payload.model_dump(exclude_unset=True)
    if "deadline" in changes and changes["deadline"] <= goal.start_date:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Deadline must be after the start date.")
    for k, v in changes.items():
        setattr(goal, k, v)
    db.commit()
    db.refresh(goal)
    return _out(db, goal)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(goal_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Response:
    db.delete(_owned(db, user, goal_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
