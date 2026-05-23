from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
migrate = Migrate()

from datetime import datetime
from sqlalchemy import event
from sqlalchemy.orm import Query

class SoftDeleteMixin:
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        db.session.add(self)

@event.listens_for(Query, "before_compile", retval=True)
def no_deleted(query):
    for desc in query.column_descriptions:
        if desc['type'] is None:
            continue
        entity = desc['type']
        if hasattr(entity, 'is_deleted'):
            if not query._execution_options.get('include_deleted', False):
                query = query.filter(entity.is_deleted == False)
    return query

