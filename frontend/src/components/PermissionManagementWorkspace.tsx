import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  assignPermissionToRole,
  createPermission,
  listPermissions,
  listRolePermissions,
  listRoles,
  removePermissionFromRole,
  updatePermission,
  updatePermissionStatus,
} from '../lib/api';
import type {
  CreatePermissionRequest,
  Permission,
  RolePermissionAssignment,
  UpdatePermissionRequest,
} from '../types/permissions';
import type { Role } from '../types/rbac';

const PAGE_SIZE = 25;



function formatRoleName(roleCode: string): string {
  return roleCode
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function formatDateTime(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return 'Unavailable';
  }

  return date.toLocaleString();
}

function getErrorMessage(
  error: unknown,
  fallback: string,
): string {
  return error instanceof Error ? error.message : fallback;
}

function PermissionManagementWorkspace() {
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);

  const [search, setSearch] = useState('');
  const [resourceFilter, setResourceFilter] = useState('');
  const [activeFilter, setActiveFilter] = useState<
    'all' | 'active' | 'inactive'
  >('all');

  const [selectedPermissionId, setSelectedPermissionId] =
    useState<string | null>(null);
  const [selectedPermission, setSelectedPermission] =
    useState<Permission | null>(null);

  const [roles, setRoles] = useState<Role[]>([]);
  const [selectedRole, setSelectedRole] = useState('');
  const [loadingRoles, setLoadingRoles] = useState(true);
  const [rolesError, setRolesError] = useState('');

  const [roleAssignments, setRoleAssignments] = useState<
    RolePermissionAssignment[]
  >([]);

  const [loadingPermissions, setLoadingPermissions] = useState(true);
  const [loadingAssignments, setLoadingAssignments] = useState(false);

  const [permissionsError, setPermissionsError] = useState('');
  const [assignmentsError, setAssignmentsError] = useState('');
  const [actionError, setActionError] = useState('');
  const [actionSuccess, setActionSuccess] = useState('');

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingPermission, setEditingPermission] =
    useState<Permission | null>(null);

  const [saving, setSaving] = useState(false);
  const [changingStatus, setChangingStatus] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [removing, setRemoving] = useState(false);

  const [form, setForm] = useState<CreatePermissionRequest>({
    code: '',
    name: '',
    resource: '',
    action: '',
    description: '',
  });

  const [assignmentCode, setAssignmentCode] = useState('');

  const totalPages = Math.max(
    1,
    Math.ceil(total / PAGE_SIZE),
  );

  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  const activeFilterValue =
    activeFilter === 'all'
      ? undefined
      : activeFilter === 'active';

  const selectedAssignmentCodes = useMemo(
    () =>
      new Set(
        roleAssignments.map(
          (assignment) => assignment.permission_code,
        ),
      ),
    [roleAssignments],
  );

  const availablePermissions = useMemo(
    () =>
      permissions.filter(
        (permission) =>
          permission.is_active &&
          !selectedAssignmentCodes.has(permission.code),
      ),
    [permissions, selectedAssignmentCodes],
  );

  const loadRoles = useCallback(async () => {
    setLoadingRoles(true);
    setRolesError('');

    try {
      const response = await listRoles();
      setRoles(response);

      setSelectedRole((current) => {
        if (current && response.some((role) => role.code === current)) {
          return current;
        }

        return response[0]?.code ?? '';
      });
    } catch (error) {
      setRoles([]);
      setSelectedRole('');
      setRolesError(
        getErrorMessage(
          error,
          'Unable to load active roles.',
        ),
      );
    } finally {
      setLoadingRoles(false);
    }
  }, []);

  const loadPermissions = useCallback(async () => {
    setLoadingPermissions(true);
    setPermissionsError('');

    try {
      const response = await listPermissions({
        search: search.trim() || undefined,
        resource: resourceFilter.trim() || undefined,
        is_active: activeFilterValue,
        offset,
        limit: PAGE_SIZE,
      });

      setPermissions(response.items);
      setTotal(response.total);

      setSelectedPermission((current) => {
        if (!current) {
          return current;
        }

        return (
          response.items.find(
            (permission) => permission.id === current.id,
          ) ?? null
        );
      });
    } catch (error) {
      setPermissionsError(
        getErrorMessage(
          error,
          'Unable to load permissions.',
        ),
      );
    } finally {
      setLoadingPermissions(false);
    }
  }, [
    activeFilterValue,
    offset,
    resourceFilter,
    search,
  ]);

  const loadRoleAssignments = useCallback(async () => {
    setLoadingAssignments(true);
    setAssignmentsError('');

    try {
      const response = await listRolePermissions(
        selectedRole,
      );

      setRoleAssignments(response);
    } catch (error) {
      setAssignmentsError(
        getErrorMessage(
          error,
          'Unable to load role permissions.',
        ),
      );
      setRoleAssignments([]);
    } finally {
      setLoadingAssignments(false);
    }
  }, [selectedRole]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadPermissions();
    }, 250);

    return () => {
      window.clearTimeout(timer);
    };
  }, [loadPermissions]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadRoles();
    }, 0);

    return () => {
      window.clearTimeout(timer);
    };
  }, [loadRoles]);

  useEffect(() => {
    if (!selectedRole) {
      return;
    }

    const timer = window.setTimeout(() => {
      void loadRoleAssignments();
    }, 0);

    return () => {
      window.clearTimeout(timer);
    };
  }, [loadRoleAssignments, selectedRole]);

  const handleSearchChange = (value: string) => {
    setSearch(value);
    setOffset(0);
    setSelectedPermissionId(null);
    setSelectedPermission(null);
  };

  const handleResourceChange = (value: string) => {
    setResourceFilter(value);
    setOffset(0);
    setSelectedPermissionId(null);
    setSelectedPermission(null);
  };

  const handleActiveFilterChange = (
    value: 'all' | 'active' | 'inactive',
  ) => {
    setActiveFilter(value);
    setOffset(0);
    setSelectedPermissionId(null);
    setSelectedPermission(null);
  };

  const resetForm = () => {
    setForm({
      code: '',
      name: '',
      resource: '',
      action: '',
      description: '',
    });
    setEditingPermission(null);
    setShowCreateForm(false);
  };

  const handleCreatePermission = async (
    event: React.FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault();

    setSaving(true);
    setActionError('');
    setActionSuccess('');

    try {
      await createPermission({
        code: form.code,
        name: form.name,
        resource: form.resource,
        action: form.action,
        description: form.description || null,
      });

      setActionSuccess(
        'Permission created successfully.',
      );

      resetForm();
      setOffset(0);
      await loadPermissions();
    } catch (error) {
      setActionError(
        getErrorMessage(
          error,
          'Unable to create permission.',
        ),
      );
    } finally {
      setSaving(false);
    }
  };

  const startEditing = (permission: Permission) => {
    setEditingPermission(permission);
    setShowCreateForm(true);

    setForm({
      code: permission.code,
      name: permission.name,
      resource: permission.resource,
      action: permission.action,
      description: permission.description ?? '',
    });

    setActionError('');
    setActionSuccess('');
  };

  const handleUpdatePermission = async (
    event: React.FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault();

    if (!editingPermission) {
      return;
    }

    setSaving(true);
    setActionError('');
    setActionSuccess('');

    const payload: UpdatePermissionRequest = {
      code: form.code,
      name: form.name,
      resource: form.resource,
      action: form.action,
      description: form.description || null,
    };

    try {
      const updated = await updatePermission(
        editingPermission.id,
        payload,
      );

      setSelectedPermission(updated);

      setActionSuccess(
        'Permission updated successfully.',
      );

      resetForm();
      await loadPermissions();
    } catch (error) {
      setActionError(
        getErrorMessage(
          error,
          'Unable to update permission.',
        ),
      );
    } finally {
      setSaving(false);
    }
  };

  const handleStatusChange = async () => {
    if (!selectedPermission) {
      return;
    }

    setChangingStatus(true);
    setActionError('');
    setActionSuccess('');

    try {
      const updated = await updatePermissionStatus(
        selectedPermission.id,
        {
          is_active: !selectedPermission.is_active,
        },
      );

      setSelectedPermission(updated);

      setPermissions((current) =>
        current.map((permission) =>
          permission.id === updated.id
            ? updated
            : permission,
        ),
      );

      setActionSuccess(
        updated.is_active
          ? 'Permission activated successfully.'
          : 'Permission deactivated successfully.',
      );
    } catch (error) {
      setActionError(
        getErrorMessage(
          error,
          'Unable to change permission status.',
        ),
      );
    } finally {
      setChangingStatus(false);
    }
  };

  const handleAssignPermission = async (
    event: React.FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault();

    if (!assignmentCode) {
      return;
    }

    setAssigning(true);
    setActionError('');
    setActionSuccess('');

    try {
      await assignPermissionToRole(
        selectedRole,
        {
            permission_code: assignmentCode,
        },
      );

      setAssignmentCode('');

      setActionSuccess(
        `Permission assigned to ${formatRoleName(selectedRole)}.`,
      );

      await loadRoleAssignments();
    } catch (error) {
      setActionError(
        getErrorMessage(
          error,
          'Unable to assign permission to the role.',
        ),
      );
    } finally {
      setAssigning(false);
    }
  };

  const handleRemovePermission = async (
    permissionCode: string,
  ) => {
    setRemoving(true);
    setActionError('');
    setActionSuccess('');

    try {
      await removePermissionFromRole(
        selectedRole,
        permissionCode,
      );

      setActionSuccess(
        `Permission removed from ${formatRoleName(selectedRole)}.`,
      );

      await loadRoleAssignments();
    } catch (error) {
      setActionError(
        getErrorMessage(
          error,
          'Unable to remove permission from the role.',
        ),
      );
    } finally {
      setRemoving(false);
    }
  };

  return (
    <section className="management-shell">
      <div className="management-heading">
        <div>
          <p className="roles-eyebrow">
            ACCESS CONTROL
          </p>
          <h1>Permission Management</h1>
          <p>
            Manage platform permissions and control which
            permissions are assigned to each AAKAR role.
          </p>
        </div>

        <div className="management-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={() => {
              if (showCreateForm) {
                resetForm();
              } else {
                setShowCreateForm(true);
                setEditingPermission(null);
                setForm({
                  code: '',
                  name: '',
                  resource: '',
                  action: '',
                  description: '',
                });
              }

              setActionError('');
              setActionSuccess('');
            }}
          >
            {showCreateForm
              ? 'Close form'
              : 'Create permission'}
          </button>
        </div>
      </div>

      {actionSuccess && (
        <div className="success-message" role="status">
          {actionSuccess}
        </div>
      )}

      {actionError && (
        <div className="error-message" role="alert">
          {actionError}
        </div>
      )}

      {showCreateForm && (
        <form
          className="management-form-card"
          onSubmit={
            editingPermission
              ? handleUpdatePermission
              : handleCreatePermission
          }
        >
          <div className="management-card-heading">
            <div>
              <p className="roles-eyebrow">
                {editingPermission
                  ? 'EDIT PERMISSION'
                  : 'NEW PERMISSION'}
              </p>
              <h2>
                {editingPermission
                  ? 'Update permission'
                  : 'Create permission'}
              </h2>
            </div>

            {editingPermission && (
              <button
                type="button"
                className="ghost-button"
                onClick={resetForm}
              >
                Cancel edit
              </button>
            )}
          </div>

          <div className="management-form-grid">
            <label>
              Permission code
              <input
                type="text"
                value={form.code}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    code: event.target.value,
                  }))
                }
                maxLength={100}
                placeholder="resource.action"
                required
              />
            </label>

            <label>
              Permission name
              <input
                type="text"
                value={form.name}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    name: event.target.value,
                  }))
                }
                maxLength={150}
                placeholder="Read users"
                required
              />
            </label>

            <label>
              Resource
              <input
                type="text"
                value={form.resource}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    resource: event.target.value,
                  }))
                }
                maxLength={80}
                placeholder="user"
                required
              />
            </label>

            <label>
              Action
              <input
                type="text"
                value={form.action}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    action: event.target.value,
                  }))
                }
                maxLength={80}
                placeholder="read"
                required
              />
            </label>

            <label className="management-form-full">
              Description
              <textarea
                value={form.description ?? ''}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    description: event.target.value,
                  }))
                }
                rows={3}
                placeholder="Explain what this permission allows."
              />
            </label>
          </div>

          <div className="management-form-actions">
            <button
              type="submit"
              className="primary-button"
              disabled={saving}
            >
              {saving
                ? 'Saving...'
                : editingPermission
                  ? 'Save changes'
                  : 'Create permission'}
            </button>
          </div>
        </form>
      )}

      <div className="management-layout">
        <section className="users-panel">
          <div className="users-toolbar">
            <div className="search-field">
              <label htmlFor="permission-search">
                Search permissions
              </label>
              <input
                id="permission-search"
                type="search"
                placeholder="Search code or name..."
                value={search}
                onChange={(event) =>
                  handleSearchChange(event.target.value)
                }
              />
            </div>

            <div className="filter-field">
              <label htmlFor="permission-resource">
                Resource
              </label>
              <input
                id="permission-resource"
                type="text"
                placeholder="e.g. user"
                value={resourceFilter}
                onChange={(event) =>
                  handleResourceChange(event.target.value)
                }
              />
            </div>

            <div className="filter-field">
              <label htmlFor="permission-status">
                Status
              </label>
              <select
                id="permission-status"
                value={activeFilter}
                onChange={(event) =>
                  handleActiveFilterChange(
                    event.target.value as
                      | 'all'
                      | 'active'
                      | 'inactive',
                  )
                }
              >
                <option value="all">
                  All permissions
                </option>
                <option value="active">Active</option>
                <option value="inactive">
                  Inactive
                </option>
              </select>
            </div>
          </div>

          {permissionsError && (
            <div className="error-message" role="alert">
              {permissionsError}
            </div>
          )}

          <div className="users-summary">
            <span>
              {total}{' '}
              {total === 1
                ? 'permission'
                : 'permissions'}
            </span>

            <span>
              Page {currentPage} of {totalPages}
            </span>
          </div>

          {loadingPermissions ? (
            <div className="management-empty-state">
              <strong>
                Loading permissions...
              </strong>
              <p>
                Retrieving access-control records from
                the secure AAKAR API.
              </p>
            </div>
          ) : permissions.length === 0 ? (
            <div className="management-empty-state">
              <strong>No permissions found</strong>
              <p>
                Try adjusting the search text,
                resource, or status filter.
              </p>
            </div>
          ) : (
            <div className="user-list">
              {permissions.map((permission) => {
                const isSelected =
                  permission.id === selectedPermissionId;

                return (
                  <button
                    type="button"
                    key={permission.id}
                    className={
                      isSelected
                        ? 'user-list-item user-list-item-active'
                        : 'user-list-item'
                    }
                    onClick={() => {
                      setSelectedPermissionId(
                        permission.id,
                      );
                      setSelectedPermission(
                        permission,
                      );
                      setActionError('');
                      setActionSuccess('');
                    }}
                  >
                    <div className="user-list-main">
                      <strong>
                        {permission.name}
                      </strong>
                      <span>
                        {permission.code}
                      </span>
                    </div>

                    <div className="user-list-meta">
                      <span
                        className={
                          permission.is_active
                            ? 'user-status user-status-active'
                            : 'user-status user-status-inactive'
                        }
                      >
                        {permission.is_active
                          ? 'Active'
                          : 'Inactive'}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          <div className="pagination-controls">
            <button
              type="button"
              className="ghost-button"
              disabled={
                offset === 0 ||
                loadingPermissions
              }
              onClick={() =>
                setOffset((currentOffset) =>
                  Math.max(
                    0,
                    currentOffset - PAGE_SIZE,
                  ),
                )
              }
            >
              Previous
            </button>

            <span>
              {currentPage} / {totalPages}
            </span>

            <button
              type="button"
              className="ghost-button"
              disabled={
                offset + PAGE_SIZE >= total ||
                loadingPermissions ||
                total === 0
              }
              onClick={() =>
                setOffset(
                  (currentOffset) =>
                    currentOffset + PAGE_SIZE,
                )
              }
            >
              Next
            </button>
          </div>
        </section>

        <section className="user-detail-panel">
          {!selectedPermission ? (
            <div className="management-empty-state management-empty-state-large">
              <span className="detail-placeholder-icon">
                A
              </span>
              <strong>
                Select a permission
              </strong>
              <p>
                Choose a permission from the list to
                inspect its details and manage its
                role assignments.
              </p>
            </div>
          ) : (
            <div className="detail-card">
              <div className="detail-card-heading">
                <div>
                  <p className="roles-eyebrow">
                    PERMISSION DETAILS
                  </p>
                  <h2>
                    {selectedPermission.name}
                  </h2>
                  <span>
                    {selectedPermission.code}
                  </span>
                </div>

                <span
                  className={
                    selectedPermission.is_active
                      ? 'user-status user-status-active'
                      : 'user-status user-status-inactive'
                  }
                >
                  {selectedPermission.is_active
                    ? 'Active'
                    : 'Inactive'}
                </span>
              </div>

              {selectedPermission.description && (
                <p className="role-description">
                  {selectedPermission.description}
                </p>
              )}

              <div className="account-meta-grid">
                <div className="profile-item">
                  <span>Resource</span>
                  <strong>
                    {selectedPermission.resource}
                  </strong>
                </div>

                <div className="profile-item">
                  <span>Action</span>
                  <strong>
                    {selectedPermission.action}
                  </strong>
                </div>

                <div className="profile-item">
                  <span>System permission</span>
                  <strong>
                    {selectedPermission.is_system_permission
                      ? 'Yes'
                      : 'No'}
                  </strong>
                </div>

                <div className="profile-item">
                  <span>Created</span>
                  <strong>
                    {formatDateTime(
                      selectedPermission.created_at,
                    )}
                  </strong>
                </div>
              </div>

              <div className="detail-form-actions">
                <button
                  type="button"
                  className="primary-button"
                  onClick={() =>
                    startEditing(
                      selectedPermission,
                    )
                  }
                >
                  Edit permission
                </button>

                <button
                  type="button"
                  className="secondary-button"
                  disabled={changingStatus}
                  onClick={() => {
                    void handleStatusChange();
                  }}
                >
                  {changingStatus
                    ? 'Updating...'
                    : selectedPermission.is_active
                      ? 'Deactivate permission'
                      : 'Activate permission'}
                </button>
              </div>

              <section className="assigned-role-panel">
                <div className="roles-heading">
                  <div>
                    <p className="roles-eyebrow">
                      ROLE ASSIGNMENTS
                    </p>
                    <h3>
                      Permissions by role
                    </h3>
                  </div>
                </div>

                <div className="management-form-card">
                  <form
                    onSubmit={
                      handleAssignPermission
                    }
                  >
                    <div className="management-form-grid">
                      <label>
                        Role
                        <select
                          value={selectedRole}
                          onChange={(event) =>
                            setSelectedRole(
                              event.target.value,
                            )
                          }
                          disabled={
                            loadingRoles ||
                            roles.length === 0
                          }
                        >
                          {loadingRoles ? (
                            <option value="">
                              Loading roles...
                            </option>
                          ) : roles.length === 0 ? (
                            <option value="">
                              No active roles available
                            </option>
                          ) : (
                            roles.map((role) => (
                              <option
                                value={role.code}
                                key={role.id}
                              >
                                {role.name ||
                                  formatRoleName(
                                    role.code,
                                  )}
                              </option>
                            ))
                          )}
                        </select>
                      </label>

                      <label>
                        Permission to assign
                        <select
                          value={assignmentCode}
                          onChange={(event) =>
                            setAssignmentCode(
                              event.target.value,
                            )
                          }
                        >
                          <option value="">
                            Select permission
                          </option>

                          {availablePermissions.map(
                            (permission) => (
                              <option
                                value={
                                  permission.code
                                }
                                key={
                                  permission.id
                                }
                              >
                                {permission.name} —{' '}
                                {
                                  permission.code
                                }
                              </option>
                            ),
                          )}
                        </select>
                      </label>
                    </div>

                    <div className="management-form-actions">
                      <button
                        type="submit"
                        className="primary-button"
                        disabled={
                          assigning ||
                          !assignmentCode
                        }
                      >
                        {assigning
                          ? 'Assigning...'
                          : 'Assign permission'}
                      </button>
                    </div>
                  </form>
                </div>

                {rolesError && (
                  <div
                    className="error-message"
                    role="alert"
                  >
                    {rolesError}
                  </div>
                )}

                {assignmentsError && (
                  <div
                    className="error-message"
                    role="alert"
                  >
                    {assignmentsError}
                  </div>
                )}

                {loadingAssignments ? (
                  <div className="management-empty-state">
                    <strong>
                      Loading assignments...
                    </strong>
                    <p>
                      Retrieving the selected
                      role's active permission
                      assignments.
                    </p>
                  </div>
                ) : roleAssignments.length === 0 ? (
                  <div className="management-empty-state">
                    <strong>
                      No permissions assigned
                    </strong>
                    <p>
                      This role currently has no
                      permission assignments.
                    </p>
                  </div>
                ) : (
                  <div className="role-list">
                    {roleAssignments.map(
                      (assignment) => (
                        <article
                          className="role-card"
                          key={
                            assignment.permission_id
                          }
                        >
                          <div className="role-card-top">
                            <div>
                              <span className="role-code">
                                {
                                  assignment.permission_code
                                }
                              </span>
                              <h3>
                                {
                                  assignment.permission_code
                                }
                              </h3>
                            </div>

                            <button
                              type="button"
                              className="ghost-button"
                              disabled={removing}
                              onClick={() => {
                                void handleRemovePermission(
                                  assignment.permission_code,
                                );
                              }}
                            >
                              Remove
                            </button>
                          </div>

                          <p className="role-description">
                            Assigned to{' '}
                            {formatRoleName(
                              assignment.role_code,
                            )}{' '}
                            on{' '}
                            {formatDateTime(
                              assignment.assigned_at,
                            )}
                            .
                          </p>
                        </article>
                      ),
                    )}
                  </div>
                )}
              </section>

              <div className="authorization-note">
                <span>SECURITY</span>
                <p>
                  Permission administration is
                  protected by the backend
                  system-administrator role. The
                  frontend only provides the
                  management interface.
                </p>
              </div>
            </div>
          )}
        </section>
      </div>
    </section>
  );
}

export default PermissionManagementWorkspace;