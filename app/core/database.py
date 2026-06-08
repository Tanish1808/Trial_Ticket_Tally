from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
migrate = Migrate()

from datetime import datetime, timezone
from sqlalchemy import event
from sqlalchemy.orm import Query

class SoftDeleteMixin:
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.add(self)

from sqlalchemy.orm import with_loader_criteria

@event.listens_for(db.Session, "do_orm_execute")
def _do_orm_execute(orm_execute_state):
    if not orm_execute_state.execution_options.get("include_deleted", False):
        orm_execute_state.statement = orm_execute_state.statement.options(
            with_loader_criteria(
                SoftDeleteMixin,
                lambda cls: cls.is_deleted == False,
                include_aliases=True,
                propagate_to_loaders=True
            )
        )

