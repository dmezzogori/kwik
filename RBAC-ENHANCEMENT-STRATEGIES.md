# RBAC Enhancement Strategies for Kwik Framework

## Executive Summary

Kwik currently implements a traditional Role-Based Access Control (RBAC) system with Users, Roles, and Permissions in a many-to-many relationship structure. While effective for basic authorization, this system lacks the granularity needed for modern applications requiring attribute-based access control (ABAC).

This document proposes three distinct enhancement strategies to extend Kwik's RBAC capabilities:

1. **Resource-Scoped Permissions** - Simple extension for resource-specific access
2. **Policy-Based Access Control** - Flexible policy engine for complex business rules  
3. **Hybrid RBAC-ABAC** - Balanced approach combining role-based and attribute-based access

Each strategy addresses different complexity levels and use cases, from simple project management scenarios to enterprise-grade authorization systems.

## Current RBAC System Analysis

### Architecture Overview

Kwik's current RBAC implementation consists of:

**Database Models:**
- `User` - User accounts with basic authentication
- `Role` - Named permission groups  
- `Permission` - Atomic authorization units
- `UserRole` - Many-to-many user-role associations
- `RolePermission` - Many-to-many role-permission associations

**Permission System:**
- String-based permission names (e.g., "users_management_read")
- Simple permission checking via `has_permission()` decorator
- Permission inheritance through role membership
- Superuser bypass mechanism

### Current Capabilities

**Strengths:**
- Simple, well-understood RBAC model
- Clean separation of users, roles, and permissions
- Efficient permission checking with database joins
- Built-in audit trail through `RecordInfoMixin`

**Limitations:**
- No resource-specific access control
- Cannot express attribute-based conditions
- No support for dynamic or contextual permissions
- Limited expressiveness for complex business rules

### Example Current Usage

```python
# Current permission checking
@router.get("/users/", dependencies=(has_permission(Permissions.users_management_read),))
def read_users(pagination: Pagination):
    return users.get_multi(**pagination)

# Current permission validation
def has_permissions(user_id: int, permissions: Sequence[str]) -> bool:
    r = (
        db.query(Permission)
        .join(RolePermission, Role, UserRole)
        .join(User, User.id == UserRole.user_id)
        .filter(Permission.name.in_(permissions), User.id == user_id)
        .distinct()
    )
    return r.count() == len(permissions)
```

## Strategy 1: Resource-Scoped Permissions

### Overview

Extend the existing RBAC system by adding resource-specific permission assignments. This approach maintains the familiar role-based model while enabling granular access control for specific resource instances.

### Technical Implementation

#### Database Schema Changes

```sql
-- New table for resource-specific permissions
CREATE TABLE resource_permissions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    permission_id INTEGER REFERENCES permissions(id),
    resource_type VARCHAR(50) NOT NULL,  -- e.g., 'project', 'document', 'task'
    resource_id INTEGER NOT NULL,        -- ID of the specific resource
    granted_by INTEGER REFERENCES users(id),
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    UNIQUE(user_id, permission_id, resource_type, resource_id)
);

-- Index for efficient querying
CREATE INDEX idx_resource_permissions_lookup 
ON resource_permissions(user_id, resource_type, resource_id, is_active);
```

#### Model Extensions

```python
class ResourcePermission(Base, RecordInfoMixin):
    """Resource-specific permission assignments."""
    
    __tablename__ = "resource_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permissions.id"), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(Integer, nullable=False)
    granted_by = Column(Integer, ForeignKey("users.id"))
    granted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    user = relationship("User", foreign_keys=[user_id])
    permission = relationship("Permission")
    granter = relationship("User", foreign_keys=[granted_by])
```

#### Enhanced Permission Checking

```python
def has_resource_permission(
    user_id: int, 
    permission: str, 
    resource_type: str, 
    resource_id: int
) -> bool:
    """Check if user has permission for specific resource."""
    
    # Check global role-based permissions first
    if has_permissions(user_id=user_id, permissions=[permission]):
        return True
    
    # Check resource-specific permissions
    result = (
        db.query(ResourcePermission)
        .join(Permission)
        .filter(
            ResourcePermission.user_id == user_id,
            ResourcePermission.resource_type == resource_type,
            ResourcePermission.resource_id == resource_id,
            ResourcePermission.is_active == True,
            Permission.name == permission,
            or_(
                ResourcePermission.expires_at.is_(None),
                ResourcePermission.expires_at > datetime.utcnow()
            )
        )
        .first()
    )
    
    return result is not None

# Enhanced dependency function
def has_resource_permission_dep(permission: str, resource_type: str):
    """FastAPI dependency for resource-specific permission checking."""
    
    def check_resource_permission(
        resource_id: int,
        current_user: User = Depends(get_current_user)
    ):
        if not has_resource_permission(
            user_id=current_user.id,
            permission=permission,
            resource_type=resource_type,
            resource_id=resource_id
        ):
            raise Forbidden
    
    return Depends(check_resource_permission)
```

#### Usage Examples

```python
# Project management example
@router.get(
    "/projects/{project_id}",
    dependencies=[has_resource_permission_dep("project.read", "project")]
)
def get_project(project_id: int):
    return get_project_by_id(project_id)

# Grant project-specific access
def assign_project_manager(user_id: int, project_id: int):
    """Assign user as manager of specific project."""
    
    permissions_to_grant = [
        "project.read",
        "project.update", 
        "project.manage_members"
    ]
    
    for perm_name in permissions_to_grant:
        permission = db.query(Permission).filter(Permission.name == perm_name).first()
        if permission:
            resource_perm = ResourcePermission(
                user_id=user_id,
                permission_id=permission.id,
                resource_type="project",
                resource_id=project_id,
                granted_by=current_user.id
            )
            db.add(resource_perm)
    
    db.commit()
```

### Pros and Cons

**Advantages:**
- Minimal disruption to existing codebase
- Familiar mental model for developers
- Efficient database queries with proper indexing
- Full backward compatibility
- Clear audit trail for resource-specific permissions

**Disadvantages:**
- Potential for permission explosion in large systems
- Limited expressiveness for complex conditions
- No support for hierarchical or inherited resource permissions
- Manual management of resource-specific permissions

**Best Suited For:**
- Small to medium applications (< 10,000 users)
- Clear resource ownership models
- Simple access patterns (owner/member/viewer)
- Projects requiring minimal migration effort

## Strategy 2: Policy-Based Access Control (PBAC)

### Overview

Implement a comprehensive policy engine that evaluates user attributes, resource attributes, and environmental context to make authorization decisions. This approach provides maximum flexibility and expressiveness for complex business rules.

### Technical Implementation

#### Database Schema

```sql
-- Policy definitions
CREATE TABLE policies (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    policy_document JSON NOT NULL,  -- Policy rules in JSON format
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Policy assignments to subjects
CREATE TABLE policy_assignments (
    id INTEGER PRIMARY KEY,
    policy_id INTEGER REFERENCES policies(id),
    subject_type VARCHAR(20) NOT NULL,  -- 'user', 'role', 'group'
    subject_id INTEGER NOT NULL,
    resource_type VARCHAR(50),          -- NULL for global policies
    priority INTEGER DEFAULT 0,        -- Higher priority = evaluated first
    is_active BOOLEAN DEFAULT TRUE,
    
    INDEX(subject_type, subject_id, resource_type, is_active)
);

-- Policy evaluation cache for performance
CREATE TABLE policy_evaluations (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    resource_type VARCHAR(50),
    resource_id INTEGER,
    action VARCHAR(100),
    decision ENUM('allow', 'deny') NOT NULL,
    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    
    INDEX(user_id, resource_type, resource_id, action, expires_at)
);
```

#### Policy Engine Implementation

```python
from typing import Dict, Any, List
from enum import Enum
import json
from datetime import datetime

class PolicyEffect(Enum):
    ALLOW = "allow"
    DENY = "deny"

class PolicyEngine:
    """Policy evaluation engine for attribute-based access control."""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def evaluate(
        self, 
        user: User, 
        action: str, 
        resource: Any = None,
        context: Dict[str, Any] = None
    ) -> bool:
        """
        Evaluate all applicable policies for authorization decision.
        
        Returns True if access should be granted, False otherwise.
        """
        
        # Check cache first
        cached_decision = self._get_cached_decision(user.id, action, resource)
        if cached_decision is not None:
            return cached_decision
        
        # Get applicable policies
        policies = self._get_applicable_policies(user, action, resource)
        
        # Evaluate policies in priority order
        decision = False  # Default deny
        
        for policy in sorted(policies, key=lambda p: p.priority, reverse=True):
            policy_decision = self._evaluate_policy(
                policy.policy_document, 
                user, 
                action, 
                resource, 
                context or {}
            )
            
            if policy_decision == PolicyEffect.DENY:
                decision = False
                break  # Explicit deny overrides everything
            elif policy_decision == PolicyEffect.ALLOW:
                decision = True  # Allow, but continue checking for denies
        
        # Cache the decision
        self._cache_decision(user.id, action, resource, decision)
        
        return decision
    
    def _evaluate_policy(
        self, 
        policy_doc: Dict[str, Any], 
        user: User, 
        action: str, 
        resource: Any,
        context: Dict[str, Any]
    ) -> PolicyEffect:
        """Evaluate a single policy document."""
        
        rules = policy_doc.get("rules", [])
        
        for rule in rules:
            if self._matches_action(rule.get("actions", []), action):
                if self._evaluate_conditions(rule.get("conditions", {}), user, resource, context):
                    return PolicyEffect(rule.get("effect", "deny"))
        
        return PolicyEffect.DENY
    
    def _evaluate_conditions(
        self, 
        conditions: Dict[str, Any], 
        user: User, 
        resource: Any,
        context: Dict[str, Any]
    ) -> bool:
        """Evaluate policy conditions against current context."""
        
        if not conditions:
            return True
        
        # Handle logical operators
        if "and" in conditions:
            return all(
                self._evaluate_conditions(cond, user, resource, context) 
                for cond in conditions["and"]
            )
        
        if "or" in conditions:
            return any(
                self._evaluate_conditions(cond, user, resource, context) 
                for cond in conditions["or"]
            )
        
        if "not" in conditions:
            return not self._evaluate_conditions(conditions["not"], user, resource, context)
        
        # Handle comparison operators
        if "equals" in conditions:
            left, right = conditions["equals"]
            return self._resolve_value(left, user, resource, context) == \
                   self._resolve_value(right, user, resource, context)
        
        if "in" in conditions:
            value, collection = conditions["in"]
            return self._resolve_value(value, user, resource, context) in \
                   self._resolve_value(collection, user, resource, context)
        
        # Add more operators as needed (greater_than, less_than, matches_regex, etc.)
        
        return False
    
    def _resolve_value(self, value_expr: str, user: User, resource: Any, context: Dict[str, Any]) -> Any:
        """Resolve attribute expressions to actual values."""
        
        if isinstance(value_expr, str) and value_expr.startswith("user."):
            attr_name = value_expr[5:]  # Remove "user." prefix
            return getattr(user, attr_name, None)
        
        if isinstance(value_expr, str) and value_expr.startswith("resource."):
            if resource is None:
                return None
            attr_name = value_expr[9:]  # Remove "resource." prefix
            return getattr(resource, attr_name, None)
        
        if isinstance(value_expr, str) and value_expr.startswith("context."):
            attr_name = value_expr[8:]  # Remove "context." prefix
            return context.get(attr_name)
        
        # Literal value
        return value_expr
```

#### Policy Definition Examples

```json
{
  "name": "ProjectManagerAccess",
  "description": "Project managers can manage their assigned projects",
  "rules": [
    {
      "effect": "allow",
      "actions": ["project.read", "project.update", "project.manage_members"],
      "conditions": {
        "and": [
          {"equals": ["user.id", "resource.manager_id"]},
          {"equals": ["resource.status", "active"]},
          {"in": ["context.request_time_hour", [9, 10, 11, 12, 13, 14, 15, 16, 17]]}
        ]
      }
    }
  ]
}
```

```json
{
  "name": "DepartmentHierarchy",
  "description": "Department managers can access all projects in their department",
  "rules": [
    {
      "effect": "allow", 
      "actions": ["project.read", "project.report"],
      "conditions": {
        "and": [
          {"equals": ["user.role", "department_manager"]},
          {"equals": ["user.department", "resource.department"]},
          {"not": {"equals": ["resource.confidentiality_level", "restricted"]}}
        ]
      }
    }
  ]
}
```

#### Usage Integration

```python
# FastAPI dependency using policy engine
def policy_check(action: str):
    """Policy-based permission checking dependency."""
    
    def check_policy(
        resource_id: int = None,
        current_user: User = Depends(get_current_user),
        request: Request = None
    ):
        # Load resource if needed
        resource = None
        if resource_id:
            resource = get_resource_by_id(resource_id)
        
        # Build context
        context = {
            "request_time": datetime.now(),
            "request_time_hour": datetime.now().hour,
            "ip_address": request.client.host if request else None,
            "user_agent": request.headers.get("user-agent") if request else None
        }
        
        # Evaluate policy
        if not policy_engine.evaluate(current_user, action, resource, context):
            raise Forbidden
    
    return Depends(check_policy)

# Usage in endpoints
@router.get("/projects/{project_id}", dependencies=[policy_check("project.read")])
def get_project(project_id: int):
    return get_project_by_id(project_id)
```

### Pros and Cons

**Advantages:**
- Maximum flexibility and expressiveness
- Supports complex business logic and hierarchical rules
- Centralized policy management
- Fine-grained attribute-based conditions
- Excellent for compliance and audit requirements

**Disadvantages:**
- High implementation complexity
- Performance overhead without aggressive caching
- Steep learning curve for policy syntax
- Debugging and troubleshooting can be difficult
- Risk of policy conflicts and unintended interactions

**Best Suited For:**
- Large enterprise applications
- Complex authorization requirements
- Regulatory compliance needs
- Multi-tenant applications with varying access patterns

## Strategy 3: Hybrid RBAC-ABAC with Attribute Store

### Overview

Combine the familiar RBAC model with attribute-based constraints, providing a gradual migration path from pure RBAC to more sophisticated access control. This approach maintains backward compatibility while adding powerful attribute-based capabilities.

### Technical Implementation

#### Database Schema Extensions

```sql
-- Attribute store for entities
CREATE TABLE attributes (
    id INTEGER PRIMARY KEY,
    entity_type VARCHAR(20) NOT NULL,  -- 'user', 'role', 'resource', 'context'
    entity_id INTEGER NOT NULL,        -- ID of the specific entity
    attribute_name VARCHAR(50) NOT NULL,
    attribute_value JSON NOT NULL,     -- Support complex attribute values
    attribute_type VARCHAR(20) DEFAULT 'string', -- 'string', 'number', 'boolean', 'array', 'object'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(entity_type, entity_id, attribute_name),
    INDEX(entity_type, entity_id, attribute_name)
);

-- Permission constraints for attribute-based conditions
CREATE TABLE permission_constraints (
    id INTEGER PRIMARY KEY,
    permission_id INTEGER REFERENCES permissions(id),
    constraint_type VARCHAR(30) NOT NULL, -- 'attribute_match', 'time_based', 'location_based'
    constraint_config JSON NOT NULL,      -- Configuration for the constraint
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0,
    
    INDEX(permission_id, constraint_type, is_active)
);

-- Enhanced user-role assignments with context
CREATE TABLE contextual_user_roles (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    role_id INTEGER REFERENCES roles(id),
    context_type VARCHAR(50),    -- 'global', 'department', 'project', 'location'
    context_value VARCHAR(100),  -- Value for the context (e.g., department ID)
    granted_by INTEGER REFERENCES users(id),
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    INDEX(user_id, role_id, context_type, context_value, is_active)
);
```

#### Model Extensions

```python
class Attribute(Base, RecordInfoMixin):
    """Flexible attribute store for any entity type."""
    
    __tablename__ = "attributes"
    
    id = Column(Integer, primary_key=True)
    entity_type = Column(String(20), nullable=False)
    entity_id = Column(Integer, nullable=False)
    attribute_name = Column(String(50), nullable=False)
    attribute_value = Column(JSON, nullable=False)
    attribute_type = Column(String(20), default="string")
    
    @property
    def typed_value(self):
        """Return attribute value with proper type conversion."""
        if self.attribute_type == "number":
            return float(self.attribute_value) if "." in str(self.attribute_value) else int(self.attribute_value)
        elif self.attribute_type == "boolean":
            return bool(self.attribute_value)
        elif self.attribute_type in ["array", "object"]:
            return self.attribute_value  # Already JSON-decoded
        return str(self.attribute_value)

class PermissionConstraint(Base, RecordInfoMixin):
    """Attribute-based constraints for permissions."""
    
    __tablename__ = "permission_constraints"
    
    id = Column(Integer, primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id"))
    constraint_type = Column(String(30), nullable=False)
    constraint_config = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)
    
    permission = relationship("Permission")

class ContextualUserRole(Base, RecordInfoMixin):
    """Context-aware user role assignments."""
    
    __tablename__ = "contextual_user_roles"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    role_id = Column(Integer, ForeignKey("roles.id"))
    context_type = Column(String(50))
    context_value = Column(String(100))
    granted_by = Column(Integer, ForeignKey("users.id"))
    granted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    user = relationship("User", foreign_keys=[user_id])
    role = relationship("Role")
    granter = relationship("User", foreign_keys=[granted_by])
```

#### Hybrid Permission Checking

```python
class HybridPermissionChecker:
    """Combined RBAC and ABAC permission checking."""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def has_permission(
        self,
        user_id: int,
        permission: str,
        resource: Any = None,
        context: Dict[str, Any] = None
    ) -> bool:
        """Check permission using hybrid RBAC-ABAC approach."""
        
        # Step 1: Check traditional RBAC permissions
        if self._has_rbac_permission(user_id, permission):
            # Step 2: Evaluate attribute-based constraints
            return self._evaluate_constraints(user_id, permission, resource, context)
        
        # Step 3: Check contextual role assignments
        return self._has_contextual_permission(user_id, permission, resource, context)
    
    def _has_rbac_permission(self, user_id: int, permission: str) -> bool:
        """Traditional RBAC permission check."""
        result = (
            self.db.query(Permission)
            .join(RolePermission, Role, UserRole)
            .join(User, User.id == UserRole.user_id)
            .filter(
                Permission.name == permission,
                User.id == user_id,
                Role.is_active == True,
                UserRole.is_active == True
            )
            .first()
        )
        return result is not None
    
    def _evaluate_constraints(
        self, 
        user_id: int, 
        permission: str, 
        resource: Any,
        context: Dict[str, Any]
    ) -> bool:
        """Evaluate attribute-based constraints for the permission."""
        
        # Get permission constraints
        permission_obj = self.db.query(Permission).filter(Permission.name == permission).first()
        if not permission_obj:
            return False
        
        constraints = (
            self.db.query(PermissionConstraint)
            .filter(
                PermissionConstraint.permission_id == permission_obj.id,
                PermissionConstraint.is_active == True
            )
            .order_by(PermissionConstraint.priority.desc())
            .all()
        )
        
        # Evaluate each constraint
        for constraint in constraints:
            if not self._evaluate_single_constraint(constraint, user_id, resource, context):
                return False
        
        return True
    
    def _evaluate_single_constraint(
        self,
        constraint: PermissionConstraint,
        user_id: int,
        resource: Any,
        context: Dict[str, Any]
    ) -> bool:
        """Evaluate a single attribute-based constraint."""
        
        config = constraint.constraint_config
        
        if constraint.constraint_type == "attribute_match":
            return self._evaluate_attribute_match(config, user_id, resource)
        
        elif constraint.constraint_type == "time_based":
            return self._evaluate_time_constraint(config, context)
        
        elif constraint.constraint_type == "location_based":
            return self._evaluate_location_constraint(config, context)
        
        return True  # Unknown constraint type - allow by default
    
    def _evaluate_attribute_match(
        self, 
        config: Dict[str, Any], 
        user_id: int, 
        resource: Any
    ) -> bool:
        """Evaluate attribute matching constraints."""
        
        user_attr_name = config.get("user_attribute")
        resource_attr_name = config.get("resource_attribute")
        match_type = config.get("match_type", "equals")
        
        if not user_attr_name or not resource_attr_name:
            return True
        
        # Get user attribute
        user_attr = self._get_attribute("user", user_id, user_attr_name)
        if not user_attr:
            return False
        
        # Get resource attribute
        resource_attr = None
        if resource:
            resource_type = resource.__class__.__name__.lower()
            resource_attr = self._get_attribute(resource_type, resource.id, resource_attr_name)
        
        if not resource_attr:
            return False
        
        # Perform comparison
        if match_type == "equals":
            return user_attr.typed_value == resource_attr.typed_value
        elif match_type == "in":
            return user_attr.typed_value in resource_attr.typed_value
        elif match_type == "contains":
            return resource_attr.typed_value in user_attr.typed_value
        
        return False
    
    def _get_attribute(self, entity_type: str, entity_id: int, attribute_name: str) -> Attribute:
        """Retrieve attribute value for an entity."""
        return (
            self.db.query(Attribute)
            .filter(
                Attribute.entity_type == entity_type,
                Attribute.entity_id == entity_id,
                Attribute.attribute_name == attribute_name
            )
            .first()
        )
```

#### Usage Examples

```python
# Grant contextual role
def assign_project_role(user_id: int, project_id: int, role_name: str):
    """Assign role to user within specific project context."""
    
    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        raise ValueError(f"Role {role_name} not found")
    
    contextual_role = ContextualUserRole(
        user_id=user_id,
        role_id=role.id,
        context_type="project",
        context_value=str(project_id),
        granted_by=current_user.id
    )
    
    db.add(contextual_role)
    db.commit()

# Set user attributes
def set_user_attributes(user_id: int, attributes: Dict[str, Any]):
    """Set multiple attributes for a user."""
    
    for attr_name, attr_value in attributes.items():
        # Determine attribute type
        attr_type = "string"
        if isinstance(attr_value, bool):
            attr_type = "boolean"
        elif isinstance(attr_value, (int, float)):
            attr_type = "number"
        elif isinstance(attr_value, (list, dict)):
            attr_type = "array" if isinstance(attr_value, list) else "object"
        
        # Upsert attribute
        existing = db.query(Attribute).filter(
            Attribute.entity_type == "user",
            Attribute.entity_id == user_id,
            Attribute.attribute_name == attr_name
        ).first()
        
        if existing:
            existing.attribute_value = attr_value
            existing.attribute_type = attr_type
            existing.updated_at = datetime.utcnow()
        else:
            new_attr = Attribute(
                entity_type="user",
                entity_id=user_id,
                attribute_name=attr_name,
                attribute_value=attr_value,
                attribute_type=attr_type
            )
            db.add(new_attr)
    
    db.commit()

# Create attribute-based constraint
def add_department_constraint(permission_name: str):
    """Add constraint requiring user and resource to be in same department."""
    
    permission = db.query(Permission).filter(Permission.name == permission_name).first()
    if not permission:
        raise ValueError(f"Permission {permission_name} not found")
    
    constraint = PermissionConstraint(
        permission_id=permission.id,
        constraint_type="attribute_match",
        constraint_config={
            "user_attribute": "department",
            "resource_attribute": "department", 
            "match_type": "equals"
        }
    )
    
    db.add(constraint)
    db.commit()
```

### Pros and Cons

**Advantages:**
- Gradual migration path from pure RBAC
- Maintains familiar role-based concepts
- Flexible attribute system for complex scenarios
- Good performance with proper indexing
- Supports both simple and complex use cases

**Disadvantages:**
- Medium implementation complexity
- Requires attribute management overhead
- Potential for attribute bloat
- Need to design constraint evaluation carefully

**Best Suited For:**
- Medium to large applications requiring migration
- Organizations with existing RBAC investments
- Applications needing both simple and complex authorization
- Projects requiring incremental enhancement approach

## Comparative Analysis

### Implementation Complexity

| Strategy | Database Changes | Code Changes | Learning Curve | Migration Effort |
|----------|------------------|--------------|----------------|------------------|
| Resource-Scoped | Low (1 table) | Low | Low | Minimal |
| Policy-Based | Medium (3 tables) | High | High | Significant |
| Hybrid RBAC-ABAC | High (3+ tables) | Medium | Medium | Moderate |

### Performance Characteristics

| Strategy | Query Complexity | Caching Requirements | Scalability | Memory Usage |
|----------|------------------|---------------------|-------------|--------------|
| Resource-Scoped | Medium | Optional | Good | Low |
| Policy-Based | High | Critical | Fair* | Medium |
| Hybrid RBAC-ABAC | Medium-High | Recommended | Good | Medium |

*Policy-Based scalability depends heavily on caching implementation

### Feature Capabilities

| Feature | Resource-Scoped | Policy-Based | Hybrid RBAC-ABAC |
|---------|----------------|--------------|-------------------|
| Resource-specific access | ✅ | ✅ | ✅ |
| Attribute-based conditions | ❌ | ✅ | ✅ |
| Hierarchical permissions | ⚡ Limited | ✅ | ✅ |
| Dynamic/contextual rules | ❌ | ✅ | ✅ |
| Time-based access | ⚡ Basic | ✅ | ✅ |
| Complex business logic | ❌ | ✅ | ⚡ Medium |
| Backward compatibility | ✅ | ✅ | ✅ |

## Use Case Validation: Project Management Scenarios

### Scenario 1: Project-Specific Access
*"A project manager should only access projects they manage"*

**Resource-Scoped Approach:**
```python
# Grant project-specific permissions
grant_resource_permission(user_id=manager.id, permission="project.manage", 
                         resource_type="project", resource_id=project.id)
```

**Policy-Based Approach:**
```json
{
  "rules": [{
    "effect": "allow",
    "actions": ["project.manage"],
    "conditions": {"equals": ["user.id", "resource.manager_id"]}
  }]
}
```

**Hybrid Approach:**
```python
# Assign contextual role
assign_contextual_role(user_id=manager.id, role="project_manager", 
                      context_type="project", context_value=project.id)
```

### Scenario 2: Hierarchical Department Access
*"Department managers can view all projects in their department"*

**Resource-Scoped:** ❌ Would require individual permissions for each project

**Policy-Based:** ✅ 
```json
{
  "conditions": {
    "and": [
      {"equals": ["user.role", "department_manager"]},
      {"equals": ["user.department", "resource.department"]}
    ]
  }
}
```

**Hybrid:** ✅
```python
# Add department constraint to role permissions
add_attribute_constraint("project.read", user_attr="department", 
                        resource_attr="department", match_type="equals")
```

### Scenario 3: Time-Limited Consultant Access
*"External consultant gets 30-day access to specific project"*

**Resource-Scoped:** ✅
```python
grant_resource_permission(user_id=consultant.id, permission="project.read",
                         resource_type="project", resource_id=project.id,
                         expires_at=datetime.now() + timedelta(days=30))
```

**Policy-Based:** ✅
```json
{
  "conditions": {
    "and": [
      {"equals": ["user.id", "123"]},
      {"less_than": ["context.current_time", "2024-08-04T23:59:59Z"]}
    ]
  }
}
```

**Hybrid:** ✅
```python
assign_contextual_role(user_id=consultant.id, role="project_viewer",
                      context_type="project", context_value=project.id,
                      expires_at=datetime.now() + timedelta(days=30))
```

## Implementation Recommendations

### Small Applications (< 1,000 users, < 10,000 resources)
**Recommended:** Strategy 1 (Resource-Scoped Permissions)

**Rationale:**
- Simple to implement and maintain
- Adequate performance for this scale
- Familiar patterns for development team
- Quick time to market

**Implementation Priority:**
1. Add `resource_permissions` table
2. Extend `has_permission()` function
3. Create resource permission management endpoints
4. Add FastAPI dependencies for resource-specific checking

### Medium Applications (1,000-10,000 users, complex business rules)
**Recommended:** Strategy 3 (Hybrid RBAC-ABAC)

**Rationale:**
- Balances flexibility with maintainability
- Allows incremental adoption of advanced features
- Preserves existing RBAC investment
- Good performance characteristics

**Implementation Priority:**
1. Add attribute store infrastructure
2. Implement contextual role assignments
3. Create constraint evaluation system
4. Build attribute management interfaces
5. Gradually migrate complex permissions to attribute-based

### Large/Enterprise Applications (> 10,000 users, regulatory requirements)
**Recommended:** Strategy 2 (Policy-Based Access Control)

**Rationale:**
- Maximum flexibility for complex requirements
- Excellent for compliance and audit needs
- Centralized policy management
- Supports sophisticated business rules

**Implementation Priority:**
1. Design policy definition language
2. Implement policy evaluation engine with caching
3. Create policy management interfaces
4. Build policy testing and debugging tools
5. Implement comprehensive audit logging
6. Performance optimization and monitoring

### High-Performance Applications (> 100 requests/second authorization)
**Recommended:** Strategy 1 or optimized Strategy 3

**Performance Optimizations:**
- Implement aggressive caching at all levels
- Pre-compute permissions for common scenarios
- Use database read replicas for permission checking
- Consider in-memory permission stores for hot data
- Implement permission result caching with proper invalidation

## Migration Considerations

### From Current RBAC to Enhanced System

#### Phase 1: Foundation (Weeks 1-2)
- Implement chosen database schema
- Create new permission checking functions
- Maintain backward compatibility with existing code
- Add comprehensive test coverage

#### Phase 2: API Enhancement (Weeks 3-4)  
- Update FastAPI dependencies to support new features
- Create management endpoints for new permission types
- Update existing endpoints to use enhanced permission checking
- Build basic administrative interfaces

#### Phase 3: Migration (Weeks 5-8)
- Identify existing permissions that need enhancement
- Migrate critical endpoints to new permission system
- Update user and role assignments as needed
- Performance testing and optimization

#### Phase 4: Advanced Features (Weeks 9-12)
- Implement advanced constraint types (time-based, location-based)
- Add policy/attribute management interfaces
- Create reporting and audit capabilities
- Documentation and training materials

### Risk Mitigation

**Performance Risks:**
- Implement comprehensive caching strategy
- Use database indexes for all query patterns
- Monitor query performance and optimize slow queries
- Consider read replicas for permission checking

**Complexity Risks:**
- Start with simple use cases and gradually add complexity
- Invest in testing infrastructure and tools
- Create clear documentation and examples
- Implement debugging and troubleshooting tools

**Migration Risks:**
- Maintain feature flags for rollback capability
- Implement comprehensive test coverage
- Use canary deployments for gradual rollout
- Plan for data migration and cleanup procedures

## Conclusion

Each strategy offers distinct advantages for different scenarios:

- **Resource-Scoped Permissions** provides a simple, evolutionary approach for straightforward use cases
- **Policy-Based Access Control** offers maximum flexibility for complex enterprise requirements
- **Hybrid RBAC-ABAC** strikes a balance between power and maintainability

The choice depends on your specific requirements for complexity, performance, migration constraints, and long-term flexibility needs. Consider starting with the simpler approaches and evolving toward more sophisticated systems as your authorization requirements grow in complexity.

All three strategies maintain backward compatibility with Kwik's existing RBAC system, ensuring a smooth transition path regardless of which approach you choose to implement.