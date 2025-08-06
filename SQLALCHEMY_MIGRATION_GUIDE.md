# SQLAlchemy 2.0 Migration Guide for Kwik Users

> **Note**: This is a living document that will be updated throughout the migration process and eventually integrated into the Kwik web documentation.

## Overview

This guide helps users of the Kwik framework migrate their applications from SQLAlchemy 1.4 to the modernized SQLAlchemy 2.0 version of Kwik. The migration represents a **major version upgrade** with significant breaking changes.

## Breaking Changes Summary

### 🔴 High Impact Changes (Required Updates)

#### 1. Model Inheritance Changes
**Before (SQLAlchemy 1.4)**:
```python
from kwik.database.base import Base
from sqlalchemy import Column, Integer, String

class MyModel(Base):
    __tablename__ = "my_models"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
```

**After (SQLAlchemy 2.0)**:
```python
from typing import Optional
from kwik.database.base import Base
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

class MyModel(Base):
    __tablename__ = "my_models"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    optional_field: Mapped[Optional[str]] = mapped_column(String)
```

#### 2. Direct Query API Usage
**Before (SQLAlchemy 1.4)**:
```python
# If you were using Kwik's session directly
from kwik.database import get_session

session = get_session()
users = session.query(MyModel).filter(MyModel.name == "test").all()
```

**After (SQLAlchemy 2.0)**:
```python
from sqlalchemy import select
from kwik.database import get_session

session = get_session()
stmt = select(MyModel).where(MyModel.name == "test")
users = session.execute(stmt).scalars().all()
```

#### 3. Relationship Definitions
**Before (SQLAlchemy 1.4)**:
```python
from sqlalchemy.orm import relationship

class User(Base):
    roles = relationship("Role", secondary="users_roles", back_populates="users")
```

**After (SQLAlchemy 2.0)**:
```python
from typing import List
from sqlalchemy.orm import Mapped, relationship

class User(Base):
    roles: Mapped[List["Role"]] = relationship(secondary="users_roles", back_populates="users")
```

**Note**: Kwik's built-in models now use this pattern. If you extend them, ensure consistency.

### 🟡 Medium Impact Changes (Import Updates)

#### Base Class Import Changes
**Before**:
```python
from sqlalchemy.ext.declarative import declarative_base
```

**After**:
```python
from sqlalchemy.orm import declarative_base
```

### 🟢 Low Impact Changes (Automatic)

#### Engine Configuration
Engine and session configuration changes are handled internally by Kwik. No user action required.

## Migration Steps

### Step 1: Update Your Models

1. **Add Type Annotations**
   ```python
   # Before
   from sqlalchemy import Column, Integer, String, Boolean
   
   id = Column(Integer, primary_key=True)
   name = Column(String, nullable=False)
   is_active = Column(Boolean, default=True)
   
   # After  
   from typing import Optional
   from sqlalchemy import String, Boolean
   from sqlalchemy.orm import Mapped, mapped_column
   
   id: Mapped[int] = mapped_column(primary_key=True)
   name: Mapped[str] = mapped_column(String)
   is_active: Mapped[bool] = mapped_column(Boolean, default=True)
   ```

2. **Handle Nullable Fields**
   ```python
   # Use Optional for nullable fields
   optional_field: Mapped[Optional[str]] = mapped_column(String)
   
   # Foreign keys are typically Optional
   user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
   ```

3. **Update Mixins Usage**
   - Remove any `__allow_unmapped__ = True` from your models
   - Kwik's mixins now use proper `Mapped[]` annotations
   ```python
   from kwik.database.mixins import RecordInfoMixin
   
   class MyModel(Base, RecordInfoMixin):
       # RecordInfoMixin now provides properly typed fields
       pass
   ```

### Step 2: Update Query Patterns

If your application directly uses SQLAlchemy queries (not through Kwik's CRUD), update them:

**Query Transformation**:
```python
# OLD
results = session.query(Model).filter(Model.field == value).all()

# NEW  
stmt = select(Model).where(Model.field == value)
results = session.execute(stmt).scalars().all()
```

**Single Result**:
```python
# OLD
result = session.query(Model).filter(Model.id == 1).first()

# NEW
stmt = select(Model).where(Model.id == 1) 
result = session.execute(stmt).scalar_one_or_none()
```

### Step 3: Update Alembic Migrations (If Applicable)

If you have custom Alembic migrations that reference models:

```python
# Update any direct model references to use new patterns
# This primarily affects complex migrations with data transformations
```

## Common Issues and Solutions

### Issue 1: Type Annotation Errors

**Error**:
```
AttributeError: 'Mapped' object has no attribute 'property'
```

**Solution**:
Ensure you're using `mapped_column()` for column definitions and `relationship()` for relationships.

### Issue 2: Missing Optional Import

**Error**:
```
NameError: name 'Optional' is not defined
```

**Solution**:
Add `from typing import Optional` for nullable fields:
```python
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column

# For nullable fields
optional_field: Mapped[Optional[str]] = mapped_column(String)
```

### Issue 3: Import Errors

**Error**:
```
ImportError: cannot import name 'declarative_base' from 'sqlalchemy.ext.declarative'
```

**Solution**:
Update import to use `from sqlalchemy.orm import declarative_base`.

### Issue 4: Query Result Errors

**Error**:
```
AttributeError: 'Result' object has no attribute 'first'
```

**Solution**:
Use the new result methods:
- `.scalar_one_or_none()` instead of `.first()`
- `.scalars().all()` instead of `.all()`

## Performance Considerations

### Expected Improvements
- Faster query compilation due to caching
- Better memory usage with modern result objects
- Improved type checking and IDE support

### Potential Issues
- Initial migration may show temporary performance dips during adaptation
- More strict typing may reveal previously hidden issues

## Testing Your Migration

### Validation Checklist
- [x] All models compile without errors ✓
- [x] Existing tests pass without modification ✓ (131/131)
- [x] Database queries return expected results ✓
- [x] Relationships work correctly ✓
- [x] `Mapped[]` annotations implemented throughout ✓
- [ ] Type checking passes (if using mypy)
- [ ] Performance benchmarking completed
- [ ] Custom CRUD operations tested

### Test Commands
```bash
# Run your test suite
pytest

# Check types (if using mypy)
mypy your_app/

# Validate database operations
python -c "from your_app import models; print('Models imported successfully')"
```

## Rollback Strategy

If you encounter critical issues:

1. **Revert to Previous Kwik Version**
   ```bash
   pip install kwik<2.0.0  # Use last 1.4-compatible version
   ```

2. **Restore Model Definitions**
   - Revert model files to use `Column` syntax
   - Remove type annotations if they cause issues

3. **Update Dependencies**
   ```bash
   pip install sqlalchemy<2.0.0
   ```

## Getting Help

### Common Resources
- [SQLAlchemy 2.0 Official Documentation](https://docs.sqlalchemy.org/en/20/)
- [Kwik GitHub Issues](https://github.com/dmezzogori/kwik/issues)
- [Kwik Documentation](https://dmezzogori.github.io/kwik/)

### Migration Support
If you encounter issues during migration:

1. Check this guide for common solutions
2. Review the official SQLAlchemy 2.0 migration docs
3. Open an issue on the Kwik GitHub repository
4. Include your model definitions and error messages

## Advanced Topics

### Custom CRUD Operations
If you've extended Kwik's CRUD classes, review the new patterns:

```python
# Modern CRUD pattern example
from sqlalchemy import select
from kwik.crud.auto_crud import AutoCRUD

class CustomCRUD(AutoCRUD):
    def custom_query(self):
        stmt = select(self.model).where(...)
        return self.db.execute(stmt).scalars().all()
```

### Complex Relationships
For advanced relationship patterns, see the updated examples in the main documentation.

---

**Document Status**: COMPREHENSIVE  
**Last Updated**: 2025-01-08  
**Kwik Version**: 2.0.0 (Migration Complete)  
**SQLAlchemy Version**: 2.0.42  

> This document will be updated as the migration progresses. Check back for the latest information and examples.