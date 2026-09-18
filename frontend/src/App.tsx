import { useCallback, useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import {
  clearAccessToken,
  getAccessToken,
  getCurrentUser,
  createManagedUser,
  getManagedUser,
  getMyRoles,
  listManagedUsers,
  loginUser,
  registerUser,
  updateManagedUser,
  updateManagedUserStatus,
} from './lib/api';
import type { User } from './types/auth';
import type { Role } from './types/rbac';
import type {
  ManagedUser,
  ManagedUserDetail,
  UpdateManagedUserRequest,
} from './types/users';
import './App.css';

type AuthMode = 'login' | 'register';
type WorkspaceMode = 'overview' | 'users';

function formatScopeLevel(scopeLevel: string): string {
  return scopeLevel
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function formatDateTime(value: string | null): string {
  if (!value) {
    return 'Never';
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return 'Unavailable';
  }

  return date.toLocaleString();
}

function formatRoleName(roleCode: string): string {
  return roleCode
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function App() {
  const [mode, setMode] = useState<AuthMode>('login');
  const [user, setUser] = useState<User | null>(null);
  const [roles, setRoles] = useState<Role[]>([]);
  const [rolesLoading, setRolesLoading] = useState(false);
  const [rolesError, setRolesError] = useState('');
  const [checkingSession, setCheckingSession] = useState(true);
  const [workspace, setWorkspace] = useState<WorkspaceMode>('overview');

  const isSystemAdministrator = useMemo(
    () => roles.some((role) => role.code === 'system_administrator'),
    [roles],
  );

  useEffect(() => {
    const restoreSession = async () => {
      if (!getAccessToken()) {
        setCheckingSession(false);
        return;
      }

      try {
        const currentUser = await getCurrentUser();
        setUser(currentUser);
      } catch {
        clearAccessToken();
      } finally {
        setCheckingSession(false);
      }
    };

    void restoreSession();
  }, []);

  useEffect(() => {
    if (!user) {
      return;
    }

    let cancelled = false;

    const loadRoles = async () => {
      setRolesLoading(true);
      setRolesError('');

      try {
        const response = await getMyRoles();

        if (!cancelled) {
          setRoles(response.roles);
        }
      } catch (requestError) {
        if (!cancelled) {
          setRolesError(
            requestError instanceof Error
              ? requestError.message
              : 'Unable to load your roles.',
          );
        }
      } finally {
        if (!cancelled) {
          setRolesLoading(false);
        }
      }
    };

    void loadRoles();

    return () => {
      cancelled = true;
    };
  }, [user]);


  const handleSignOut = () => {
    clearAccessToken();
    setRoles([]);
    setRolesError('');
    setWorkspace('overview');
    setUser(null);
  };

  if (checkingSession) {
    return (
      <main className="auth-shell">
        <div className="loading-screen">
          <div className="brand-mark">आ</div>
          <p>Restoring secure session...</p>
        </div>
      </main>
    );
  }

  if (user) {
    return (
      <main className="app-shell">
        <header className="app-header">
          <div className="brand">
            <div className="brand-mark brand-mark-small">आ</div>

            <div>
              <strong>AAKAR</strong>
              <span>आकार</span>
            </div>
          </div>

          <div className="header-actions">
            {isSystemAdministrator && (
              <button
                type="button"
                className={
                  workspace === 'users'
                    ? 'workspace-button workspace-button-active'
                    : 'workspace-button'
                }
                onClick={() => setWorkspace('users')}
              >
                User Management
              </button>
            )}

            <button
              type="button"
              className="ghost-button"
              onClick={handleSignOut}
            >
              Sign out
            </button>
          </div>
        </header>

        {workspace === 'users' && isSystemAdministrator ? (
          <UserManagementWorkspace currentUser={user} />
        ) : (
          <section className="session-card">
            <div className="status-badge">
              <span className="status-dot" />
              Authenticated session
            </div>

            <h1>Welcome, {user.full_name}</h1>

            <p className="session-copy">
              Your AAKAR account is authenticated and the current session token
              has been verified by the backend.
            </p>

            <div className="profile-grid">
              <div className="profile-item">
                <span>Email</span>
                <strong>{user.email}</strong>
              </div>

              <div className="profile-item">
                <span>Account status</span>
                <strong>{user.is_active ? 'Active' : 'Inactive'}</strong>
              </div>

              <div className="profile-item">
                <span>Email verification</span>
                <strong>
                  {user.is_email_verified ? 'Verified' : 'Not verified'}
                </strong>
              </div>

              <div className="profile-item">
                <span>Authentication</span>
                <strong>JWT Bearer</strong>
              </div>
            </div>

            <section className="roles-section">
              <div className="roles-heading">
                <div>
                  <p className="roles-eyebrow">ACCESS CONTROL</p>
                  <h2>Assigned roles</h2>
                </div>

                {rolesLoading && (
                  <span className="roles-loading">Loading roles...</span>
                )}
              </div>

              {rolesError && (
                <div className="error-message" role="alert">
                  {rolesError}
                </div>
              )}

              {!rolesLoading && !rolesError && roles.length === 0 && (
                <div className="no-role-card">
                  <span className="no-role-icon">!</span>

                  <div>
                    <strong>No role assigned</strong>
                    <p>
                      Your account is authenticated, but no active AAKAR role
                      is currently assigned.
                    </p>
                  </div>
                </div>
              )}

              {!rolesLoading && !rolesError && roles.length > 0 && (
                <div className="role-list">
                  {roles.map((role) => (
                    <article className="role-card" key={role.id}>
                      <div className="role-card-top">
                        <div>
                          <span className="role-code">{role.code}</span>
                          <h3>{role.name}</h3>
                        </div>

                        <span className="scope-badge">
                          {formatScopeLevel(role.scope_level)}
                        </span>
                      </div>

                      {role.description && (
                        <p className="role-description">{role.description}</p>
                      )}
                    </article>
                  ))}
                </div>
              )}

              <div className="authorization-note">
                <span>AAKAR</span>

                <p>
                  Role information is loaded from the backend. Actual access
                  to protected resources is enforced by server-side
                  authorization.
                </p>
              </div>
            </section>
          </section>
        )}
      </main>
    );
  }

  return (
    <main className="auth-shell">
      <section className="auth-visual">
        <div className="contour contour-one" />
        <div className="contour contour-two" />
        <div className="contour contour-three" />

        <div className="visual-content">
          <div className="brand">
            <div className="brand-mark">आ</div>

            <div>
              <strong>AAKAR</strong>
              <span>आकार</span>
            </div>
          </div>

          <div className="visual-copy">
            <p className="eyebrow">NATIONAL LAND MANAGEMENT SYSTEM</p>

            <h1>
              Shaping land.
              <br />
              Empowering development.
            </h1>

            <p>
              Secure access to the AAKAR platform for digital land acquisition
              workflows, records, and operational monitoring.
            </p>
          </div>

          <div className="visual-footer">
            <span>Secure government access</span>
            <span>AAKAR v0.1</span>
          </div>
        </div>
      </section>

      <section className="auth-panel">
        <div className="auth-card">
          <div className="mobile-brand">
            <div className="brand-mark">आ</div>

            <div>
              <strong>AAKAR</strong>
              <span>आकार</span>
            </div>
          </div>

          {mode === 'login' ? (
            <LoginForm
              onAuthenticated={setUser}
              onSwitchToRegister={() => setMode('register')}
            />
          ) : (
            <RegisterForm
              onRegistered={() => setMode('login')}
              onSwitchToLogin={() => setMode('login')}
            />
          )}
        </div>
      </section>
    </main>
  );
}

interface UserManagementWorkspaceProps {
  currentUser: User;
}

function UserManagementWorkspace({
  currentUser,
}: UserManagementWorkspaceProps) {
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [selectedUser, setSelectedUser] =
    useState<ManagedUserDetail | null>(null);

  const [search, setSearch] = useState('');
  const [activeFilter, setActiveFilter] = useState<'all' | 'active' | 'inactive'>(
    'all',
  );

  const [offset, setOffset] = useState(0);
  const limit = 25;

  const [total, setTotal] = useState(0);
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [usersError, setUsersError] = useState('');

  const [loadingDetails, setLoadingDetails] = useState(false);
  const [detailsError, setDetailsError] = useState('');

  const [savingProfile, setSavingProfile] = useState(false);
  const [profileError, setProfileError] = useState('');
  const [profileSuccess, setProfileSuccess] = useState('');

  const [changingStatus, setChangingStatus] = useState(false);

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createForm, setCreateForm] = useState({
    full_name: '',
    email: '',
    password: '',
  });
  const [createError, setCreateError] = useState('');
  const [createSuccess, setCreateSuccess] = useState('');
  const [creatingUser, setCreatingUser] = useState(false);

  const selectedUserIsCurrentUser =
    selectedUser?.id === currentUser.id || selectedUserId === currentUser.id;

  const activeFilterValue =
    activeFilter === 'all' ? undefined : activeFilter === 'active';

  const totalPages = Math.max(1, Math.ceil(total / limit));
  const currentPage = Math.floor(offset / limit) + 1;

  const loadUsers = useCallback(async () => {
    setLoadingUsers(true);
    setUsersError('');

    try {
      const response = await listManagedUsers({
        search: search.trim() || undefined,
        is_active: activeFilterValue,
        offset,
        limit,
      });

      setUsers(response.items);
      setTotal(response.total);
    } catch (requestError) {
      setUsersError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to load users.',
      );
    } finally {
      setLoadingUsers(false);
    }
  }, [activeFilterValue, offset, search]);

  const loadUserDetails = async (userId: string) => {
    setSelectedUserId(userId);
    setSelectedUser(null);
    setLoadingDetails(true);
    setDetailsError('');
    setProfileError('');
    setProfileSuccess('');

    try {
      const response = await getManagedUser(userId);
      setSelectedUser(response);
    } catch (requestError) {
      setDetailsError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to load user details.',
      );
    } finally {
      setLoadingDetails(false);
    }
  };

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadUsers();
    }, 250);

    return () => {
      window.clearTimeout(timer);
    };
  }, [loadUsers]);

  const handleSearchChange = (value: string) => {
    setSearch(value);
    setOffset(0);
    setSelectedUserId(null);
    setSelectedUser(null);
  };

  const handleFilterChange = (
    value: 'all' | 'active' | 'inactive',
  ) => {
    setActiveFilter(value);
    setOffset(0);
    setSelectedUserId(null);
    setSelectedUser(null);
  };

  const handleProfileSave = async (
    event: FormEvent<HTMLFormElement>,
    values: UpdateManagedUserRequest,
  ) => {
    event.preventDefault();

    if (!selectedUser) {
      return;
    }

    setSavingProfile(true);
    setProfileError('');
    setProfileSuccess('');

    try {
      const updatedUser = await updateManagedUser(selectedUser.id, values);

      setSelectedUser((current) =>
        current
          ? {
              ...current,
              ...updatedUser,
            }
          : current,
      );

      setUsers((currentUsers) =>
        currentUsers.map((item) =>
          item.id === updatedUser.id ? { ...item, ...updatedUser } : item,
        ),
      );

      setProfileSuccess('User profile updated successfully.');
    } catch (requestError) {
      setProfileError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to update user profile.',
      );
    } finally {
      setSavingProfile(false);
    }
  };

  const handleStatusChange = async () => {
    if (!selectedUser) {
      return;
    }

    if (selectedUserIsCurrentUser) {
      setProfileError('You cannot change your own account status.');
      return;
    }

    const nextStatus = !selectedUser.is_active;

    setChangingStatus(true);
    setProfileError('');
    setProfileSuccess('');

    try {
      const updatedUser = await updateManagedUserStatus(selectedUser.id, {
        is_active: nextStatus,
      });

      setSelectedUser((current) =>
        current
          ? {
              ...current,
              ...updatedUser,
            }
          : current,
      );

      setUsers((currentUsers) =>
        currentUsers.map((item) =>
          item.id === updatedUser.id ? { ...item, ...updatedUser } : item,
        ),
      );

      setProfileSuccess(
        nextStatus
          ? 'User account activated successfully.'
          : 'User account deactivated successfully.',
      );
    } catch (requestError) {
      setProfileError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to change account status.',
      );
    } finally {
      setChangingStatus(false);
    }
  };

  const handleCreateUser = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    setCreatingUser(true);
    setCreateError('');
    setCreateSuccess('');

    try {
      await createManagedUser(createForm);

      setCreateForm({
        full_name: '',
        email: '',
        password: '',
      });

      setCreateSuccess('User account created successfully.');
      setShowCreateForm(false);
      setOffset(0);
      await loadUsers();
    } catch (requestError) {
      setCreateError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to create the user account.',
      );
    } finally {
      setCreatingUser(false);
    }
  };

  return (
    <section className="management-shell">
      <div className="management-heading">
        <div>
          <p className="roles-eyebrow">IDENTITY & ADMINISTRATION</p>
          <h1>User Management</h1>
          <p>
            Manage AAKAR platform accounts, account status, and user profile
            information.
          </p>
        </div>

        <div className="management-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={() => {
              setShowCreateForm((current) => !current);
              setCreateError('');
              setCreateSuccess('');
            }}
          >
            {showCreateForm ? 'Close form' : 'Create user'}
          </button>
        </div>
      </div>

      {createSuccess && !showCreateForm && (
        <div className="success-message" role="status">
          {createSuccess}
        </div>
      )}

      {showCreateForm && (
        <form className="management-form-card" onSubmit={handleCreateUser}>
          <div className="management-card-heading">
            <div>
              <p className="roles-eyebrow">NEW ACCOUNT</p>
              <h2>Create user</h2>
            </div>
          </div>

          <div className="management-form-grid">
            <label>
              Full name
              <input
                type="text"
                value={createForm.full_name}
                onChange={(event) =>
                  setCreateForm((current) => ({
                    ...current,
                    full_name: event.target.value,
                  }))
                }
                minLength={2}
                maxLength={150}
                required
              />
            </label>

            <label>
              Email address
              <input
                type="email"
                value={createForm.email}
                onChange={(event) =>
                  setCreateForm((current) => ({
                    ...current,
                    email: event.target.value,
                  }))
                }
                maxLength={320}
                required
              />
            </label>

            <label>
              Temporary password
              <input
                type="password"
                value={createForm.password}
                onChange={(event) =>
                  setCreateForm((current) => ({
                    ...current,
                    password: event.target.value,
                  }))
                }
                minLength={8}
                maxLength={128}
                required
              />
            </label>
          </div>

          {createError && (
            <div className="error-message" role="alert">
              {createError}
            </div>
          )}

          <div className="management-form-actions">
            <button
              type="submit"
              className="primary-button"
              disabled={creatingUser}
            >
              {creatingUser ? 'Creating user...' : 'Create user'}
            </button>
          </div>
        </form>
      )}

      <div className="management-layout">
        <section className="users-panel">
          <div className="users-toolbar">
            <div className="search-field">
              <label htmlFor="user-search">Search users</label>
              <input
                id="user-search"
                type="search"
                placeholder="Search by name or email..."
                value={search}
                onChange={(event) => handleSearchChange(event.target.value)}
              />
            </div>

            <div className="filter-field">
              <label htmlFor="user-status-filter">Status</label>
              <select
                id="user-status-filter"
                value={activeFilter}
                onChange={(event) =>
                  handleFilterChange(
                    event.target.value as 'all' | 'active' | 'inactive',
                  )
                }
              >
                <option value="all">All accounts</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
          </div>

          {usersError && (
            <div className="error-message" role="alert">
              {usersError}
            </div>
          )}

          <div className="users-summary">
            <span>
              {total} {total === 1 ? 'account' : 'accounts'}
            </span>

            <span>
              Page {currentPage} of {totalPages}
            </span>
          </div>

          {loadingUsers ? (
            <div className="management-empty-state">
              <strong>Loading users...</strong>
              <p>Retrieving accounts from the secure AAKAR API.</p>
            </div>
          ) : users.length === 0 ? (
            <div className="management-empty-state">
              <strong>No users found</strong>
              <p>
                Try adjusting the search text or account-status filter.
              </p>
            </div>
          ) : (
            <div className="user-list">
              {users.map((managedUser) => {
                const isSelected = managedUser.id === selectedUserId;
                const isCurrent = managedUser.id === currentUser.id;

                return (
                  <button
                    type="button"
                    key={managedUser.id}
                    className={
                      isSelected
                        ? 'user-list-item user-list-item-active'
                        : 'user-list-item'
                    }
                    onClick={() => {
                      void loadUserDetails(managedUser.id);
                    }}
                  >
                    <div className="user-list-main">
                      <strong>{managedUser.full_name}</strong>
                      <span>{managedUser.email}</span>
                    </div>

                    <div className="user-list-meta">
                      <span
                        className={
                          managedUser.is_active
                            ? 'user-status user-status-active'
                            : 'user-status user-status-inactive'
                        }
                      >
                        {managedUser.is_active ? 'Active' : 'Inactive'}
                      </span>

                      {isCurrent && (
                        <span className="current-user-badge">You</span>
                      )}
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
              disabled={offset === 0 || loadingUsers}
              onClick={() =>
                setOffset((currentOffset) =>
                  Math.max(0, currentOffset - limit),
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
                offset + limit >= total || loadingUsers || total === 0
              }
              onClick={() => setOffset((currentOffset) => currentOffset + limit)}
            >
              Next
            </button>
          </div>
        </section>

        <section className="user-detail-panel">
          {loadingDetails && (
            <div className="management-empty-state">
              <strong>Loading user details...</strong>
              <p>Fetching the selected account and assigned roles.</p>
            </div>
          )}

          {!loadingDetails && detailsError && (
            <div className="error-message" role="alert">
              {detailsError}
            </div>
          )}

          {!loadingDetails && !detailsError && !selectedUser && (
            <div className="management-empty-state management-empty-state-large">
              <span className="detail-placeholder-icon">आ</span>
              <strong>Select an account</strong>
              <p>
                Choose a user from the list to inspect profile information,
                account status, and assigned roles.
              </p>
            </div>
          )}

          {!loadingDetails && !detailsError && selectedUser && (
            <UserDetailPanel
              user={selectedUser}
              isCurrentUser={selectedUserIsCurrentUser}
              savingProfile={savingProfile}
              changingStatus={changingStatus}
              profileError={profileError}
              profileSuccess={profileSuccess}
              onSave={handleProfileSave}
              onStatusChange={() => {
                void handleStatusChange();
              }}
            />
          )}
        </section>
      </div>
    </section>
  );
}

interface UserDetailPanelProps {
  user: ManagedUserDetail;
  isCurrentUser: boolean;
  savingProfile: boolean;
  changingStatus: boolean;
  profileError: string;
  profileSuccess: string;
  onSave: (
    event: FormEvent<HTMLFormElement>,
    values: UpdateManagedUserRequest,
  ) => Promise<void>;
  onStatusChange: () => void;
}

function UserDetailPanel({
  user,
  isCurrentUser,
  savingProfile,
  changingStatus,
  profileError,
  profileSuccess,
  onSave,
  onStatusChange,
}: UserDetailPanelProps) {
  const [fullName, setFullName] = useState(user.full_name);
  const [email, setEmail] = useState(user.email);


  return (
    <div className="detail-card">
      <div className="detail-card-heading">
        <div>
          <p className="roles-eyebrow">ACCOUNT DETAILS</p>
          <h2>{user.full_name}</h2>
          <span>{user.email}</span>
        </div>

        <span
          className={
            user.is_active
              ? 'user-status user-status-active'
              : 'user-status user-status-inactive'
          }
        >
          {user.is_active ? 'Active' : 'Inactive'}
        </span>
      </div>

      {profileError && (
        <div className="error-message" role="alert">
          {profileError}
        </div>
      )}

      {profileSuccess && (
        <div className="success-message" role="status">
          {profileSuccess}
        </div>
      )}

      <form
        className="detail-form"
        onSubmit={(event) =>
          void onSave(event, {
            full_name: fullName,
            email,
          })
        }
      >
        <label>
          Full name
          <input
            type="text"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            minLength={2}
            maxLength={150}
            required
          />
        </label>

        <label>
          Email address
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            maxLength={320}
            required
          />
        </label>

        <div className="detail-form-actions">
          <button
            type="submit"
            className="primary-button"
            disabled={savingProfile}
          >
            {savingProfile ? 'Saving...' : 'Save changes'}
          </button>

          <button
            type="button"
            className="secondary-button"
            disabled={changingStatus || isCurrentUser}
            onClick={onStatusChange}
          >
            {changingStatus
              ? 'Updating...'
              : user.is_active
                ? 'Deactivate account'
                : 'Activate account'}
          </button>
        </div>
      </form>

      <div className="account-meta-grid">
        <div className="profile-item">
          <span>Email verification</span>
          <strong>
            {user.is_email_verified ? 'Verified' : 'Not verified'}
          </strong>
        </div>

        <div className="profile-item">
          <span>Last login</span>
          <strong>{formatDateTime(user.last_login_at)}</strong>
        </div>

        <div className="profile-item">
          <span>Created</span>
          <strong>{formatDateTime(user.created_at)}</strong>
        </div>

        <div className="profile-item">
          <span>Updated</span>
          <strong>{formatDateTime(user.updated_at)}</strong>
        </div>
      </div>

      <section className="assigned-role-panel">
        <div className="roles-heading">
          <div>
            <p className="roles-eyebrow">ACCESS CONTROL</p>
            <h3>Assigned roles</h3>
          </div>

          <span className="role-count">
            {user.roles.length} {user.roles.length === 1 ? 'role' : 'roles'}
          </span>
        </div>

        {user.roles.length === 0 ? (
          <div className="no-role-card">
            <span className="no-role-icon">!</span>

            <div>
              <strong>No active roles</strong>
              <p>
                This account currently has no active AAKAR roles assigned.
              </p>
            </div>
          </div>
        ) : (
          <div className="role-list">
            {user.roles.map((role) => (
              <article className="role-card" key={role.id}>
                <div className="role-card-top">
                  <div>
                    <span className="role-code">{role.code}</span>
                    <h3>{role.name || formatRoleName(role.code)}</h3>
                  </div>

                  <span className="scope-badge">
                    {formatScopeLevel(role.scope_level)}
                  </span>
                </div>

                {role.description && (
                  <p className="role-description">{role.description}</p>
                )}
              </article>
            ))}
          </div>
        )}
      </section>

      {isCurrentUser && (
        <div className="authorization-note">
          <span>SECURITY</span>
          <p>
            Your own account status cannot be changed from User Management.
          </p>
        </div>
      )}
    </div>
  );
}

interface LoginFormProps {
  onAuthenticated: (user: User) => void;
  onSwitchToRegister: () => void;
}

function LoginForm({
  onAuthenticated,
  onSwitchToRegister,
}: LoginFormProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await loginUser({
        email,
        password,
      });

      onAuthenticated(response.user);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to sign in.',
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="auth-heading">
        <p className="eyebrow">SECURE SIGN-IN</p>
        <h2>Welcome back</h2>
        <p>Sign in to access your AAKAR workspace.</p>
      </div>

      <form className="auth-form" onSubmit={handleSubmit}>
        <label htmlFor="login-email">
          Email address

          <input
            id="login-email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="name@department.gov.in"
            required
          />
        </label>

        <label htmlFor="login-password">
          Password

          <input
            id="login-password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Enter your password"
            required
          />
        </label>

        {error && (
          <div className="error-message" role="alert">
            {error}
          </div>
        )}

        <button className="primary-button" type="submit" disabled={loading}>
          {loading ? 'Signing in...' : 'Sign in'}
        </button>
      </form>

      <p className="auth-switch">
        New to AAKAR?

        <button type="button" onClick={onSwitchToRegister}>
          Create an account
        </button>
      </p>
    </>
  );
}

interface RegisterFormProps {
  onRegistered: () => void;
  onSwitchToLogin: () => void;
}

function RegisterForm({
  onRegistered,
  onSwitchToLogin,
}: RegisterFormProps) {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      await registerUser({
        full_name: fullName,
        email,
        password,
      });

      setFullName('');
      setEmail('');
      setPassword('');
      setSuccess('Account created successfully. You can now sign in.');
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to create the account.',
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="auth-heading">
        <p className="eyebrow">ACCOUNT REGISTRATION</p>
        <h2>Create your account</h2>
        <p>Set up an AAKAR account for secure platform access.</p>
      </div>

      <form className="auth-form" onSubmit={handleSubmit}>
        <label htmlFor="register-name">
          Full name

          <input
            id="register-name"
            type="text"
            autoComplete="name"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            placeholder="Enter your full name"
            minLength={2}
            maxLength={150}
            required
          />
        </label>

        <label htmlFor="register-email">
          Email address

          <input
            id="register-email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="name@department.gov.in"
            required
          />
        </label>

        <label htmlFor="register-password">
          Password

          <input
            id="register-password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Minimum 8 characters"
            minLength={8}
            maxLength={128}
            required
          />
        </label>

        {error && (
          <div className="error-message" role="alert">
            {error}
          </div>
        )}

        {success && (
          <div className="success-message" role="status">
            {success}
          </div>
        )}

        <button className="primary-button" type="submit" disabled={loading}>
          {loading ? 'Creating account...' : 'Create account'}
        </button>
      </form>

      <p className="auth-switch">
        Already have an account?

        <button
          type="button"
          onClick={() => {
            onRegistered();
            setSuccess('');
            setError('');
          }}
        >
          Sign in
        </button>
      </p>

      <button
        type="button"
        className="back-button"
        onClick={onSwitchToLogin}
      >
        ← Back to sign in
      </button>
    </>
  );
}

export default App;
