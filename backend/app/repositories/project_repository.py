import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectRepository:
    """Repository handling persistence operations for Projects."""

    @staticmethod
    def create(db: Session, project_in: ProjectCreate) -> Project:
        project = Project(
            name=project_in.name,
            description=project_in.description,
            repository_url=project_in.repository_url,
            default_branch=project_in.default_branch,
            environment=project_in.environment,
            status=project_in.status,
        )
        db.add(project)
        db.flush()
        return project

    @staticmethod
    def get_by_id(db: Session, project_id: uuid.UUID) -> Optional[Project]:
        statement = select(Project).where(Project.id == project_id)
        return db.scalar(statement)

    @staticmethod
    def get_by_name(db: Session, name: str) -> Optional[Project]:
        statement = select(Project).where(Project.name == name)
        return db.scalar(statement)

    @staticmethod
    def list(db: Session, skip: int = 0, limit: int = 100) -> List[Project]:
        statement = select(Project).offset(skip).limit(limit).order_by(Project.name)
        return list(db.scalars(statement).all())

    @staticmethod
    def update(db: Session, project: Project, project_in: ProjectUpdate) -> Project:
        update_data = project_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)
        db.flush()
        return project

    @staticmethod
    def delete(db: Session, project: Project) -> None:
        db.delete(project)
        db.flush()

