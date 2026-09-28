import { useCallback, useEffect, useMemo, useState } from 'react';

import type { FormEvent } from 'react';



import {

  assignUserRole,

  clearAccessToken,

  getAccessToken,

  getCurrentUser,

  createManagedUser,

  getManagedUser,

  getMyPermissions,

  getMyRoles,

  listManagedUsers,

  listRoles,

  loginUser,

  registerUser,

  removeUserRole,

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



import DepartmentManagementWorkspace from './components/DepartmentManagementWorkspace';

import AuthorityManagementWorkspace from './components/AuthorityManagementWorkspace';

import PermissionManagementWorkspace from './components/PermissionManagementWorkspace';

import AuditHistoryWorkspace from './components/AuditHistoryWorkspace';

import ProjectManagementWorkspace from './components/ProjectManagementWorkspace';
import LandRequirementWorkspace from './components/LandRequirementWorkspace';
import AcquisitionCaseWorkspace from './components/AcquisitionCaseWorkspace';
import ParcelManagementWorkspace from './components/ParcelManagementWorkspace';
import SurveyManagementWorkspace from './components/SurveyManagementWorkspace';



import LanguageSelector from './components/LanguageSelector';

import { useAakarLanguage } from './i18n/i18n';



import './App.css';



type AuthMode = 'login' | 'register';



type WorkspaceMode =

  | 'overview'

  | 'projects'

  | 'landRequirements'

  | 'acquisitionCases'
  | 'parcels'
  | 'survey'

  | 'users'

  | 'departments'

  | 'authorities'

  | 'permissions'

  | 'audit';



function formatScopeLevel(scopeLevel: string): string {

  return scopeLevel

    .split('_')

    .map(

      (part) =>

        part.charAt(0).toUpperCase() + part.slice(1),

    )

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

    .map(

      (part) =>

        part.charAt(0).toUpperCase() + part.slice(1),

    )

    .join(' ');

}



type NavigationItem = {

  workspace: Exclude<WorkspaceMode, 'overview'>;

  label: string;

  permission: string;

};



const OPERATIONS_NAVIGATION: NavigationItem[] = [

  {

    workspace: 'projects',

    label: 'Project Management',

    permission: 'project.read',

  },

  {

    workspace: 'landRequirements',

    label: 'Land Requirement Management',

    permission: 'land_requirement.read',

  },

  {

    workspace: 'acquisitionCases',

    label: 'Acquisition Case Management',

    permission: 'acquisition_case.read',

  },
  {
    workspace: 'parcels',
    label: 'Parcel Management',
    permission: 'parcel.read',
  },
  {
    workspace: 'survey',
    label: 'Survey & Measurement',
    permission: 'survey.read',
  },

];



const ADMINISTRATION_NAVIGATION: NavigationItem[] = [

  {

    workspace: 'users',

    label: 'User Management',

    permission: 'user.read',

  },

  {

    workspace: 'departments',

    label: 'Department Management',

    permission: 'department.read',

  },

  {

    workspace: 'authorities',

    label: 'Authority Management',

    permission: 'authority.read',

  },

  {

    workspace: 'permissions',

    label: 'Permission Management',

    permission: 'permission.read',

  },

  {

    workspace: 'audit',

    label: 'Audit & Activity History',

    permission: 'audit.read',

  },

];



type ApplicationArea =

  | 'administration'

  | 'operations'

  | 'restricted';



const SYSTEM_ADMINISTRATION_ROLE_CODES = new Set([

  'system_administrator',

  'audit_compliance',

]);



const OPERATIONAL_ROLE_CODES = new Set([

  'national_administrator',

  'central_ministry_officer',

  'national_monitoring_officer',

  'state_nodal_officer',

  'state_land_authority_officer',

  'state_department_officer',

  'district_collector',

  'additional_collector',

  'land_acquisition_officer',

  'revenue_officer',

  'rr_officer',

  'survey_gis_officer',

  'project_director',

  'infrastructure_officer',

  'field_verification_officer',

  'project_implementing_agency',

  'field_officer',

  'aakar_development_admin',

]);



function App() {

  const { t } = useAakarLanguage();

  const [mode, setMode] = useState<AuthMode>('login');

  const [user, setUser] = useState<User | null>(null);

  const [roles, setRoles] = useState<Role[]>([]);

  const [rolesLoading, setRolesLoading] = useState(false);

  const [rolesError, setRolesError] = useState('');

  const [permissions, setPermissions] = useState<string[]>([]);

  const [permissionsLoading, setPermissionsLoading] = useState(false);

  const [permissionsError, setPermissionsError] = useState('');

  const [checkingSession, setCheckingSession] =

    useState(true);



  const [workspace, setWorkspace] =

    useState<WorkspaceMode>('overview');



  const permissionSet = useMemo(

    () => new Set(permissions),

    [permissions],

  );



  const isSystemAdministrationRole = useMemo(

    () =>

      roles.some((role) =>

        SYSTEM_ADMINISTRATION_ROLE_CODES.has(role.code),

      ),

    [roles],

  );



  const isOperationalRole = useMemo(

    () =>

      roles.some((role) =>

        OPERATIONAL_ROLE_CODES.has(role.code),

      ),

    [roles],

  );



  const applicationArea = useMemo<ApplicationArea>(() => {

    if (isSystemAdministrationRole) {

      return 'administration';

    }



    if (isOperationalRole) {

      return 'operations';

    }



    if (permissionSet.has('project.read')) {

      return 'operations';

    }



    return 'restricted';

  }, [

    isOperationalRole,

    isSystemAdministrationRole,

    permissionSet,

  ]);



  const visibleOperations = useMemo(

    () =>

      applicationArea === 'operations'

        ? OPERATIONS_NAVIGATION.filter((item) =>

            permissionSet.has(item.permission),

          )

        : [],

    [applicationArea, permissionSet],

  );



  const visibleAdministration = useMemo(

    () =>

      applicationArea === 'administration'

        ? ADMINISTRATION_NAVIGATION.filter((item) =>

            permissionSet.has(item.permission),

          )

        : [],

    [applicationArea, permissionSet],

  );



  const visibleNavigation = useMemo(

    () =>

      applicationArea === 'administration'

        ? visibleAdministration

        : visibleOperations,

    [

      applicationArea,

      visibleAdministration,

      visibleOperations,

    ],

  );



  const hasPermission = useCallback(

    (permission: string) =>

      permissionSet.has(permission),

    [permissionSet],

  );



  useEffect(() => {

    const restoreSession = async () => {

      if (!getAccessToken()) {

        setCheckingSession(false);

        return;

      }



      try {

        const currentUser =

          await getCurrentUser();



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



    const loadAccessContext = async () => {

      setRolesLoading(true);

      setPermissionsLoading(true);

      setRolesError('');

      setPermissionsError('');



      try {

        const [rolesResponse, permissionsResponse] =

          await Promise.all([

            getMyRoles(),

            getMyPermissions(),

          ]);



        if (!cancelled) {

          setRoles(rolesResponse.roles);

          setPermissions(

            permissionsResponse.permissions,

          );

        }

      } catch (requestError) {

        if (!cancelled) {

          const message =

            requestError instanceof Error

              ? requestError.message

              : 'Unable to load your access permissions.';



          setRolesError(message);

          setPermissionsError(message);

          setRoles([]);

          setPermissions([]);

        }

      } finally {

        if (!cancelled) {

          setRolesLoading(false);

          setPermissionsLoading(false);

        }

      }

    };



    void loadAccessContext();



    return () => {

      cancelled = true;

    };

  }, [user]);



  useEffect(() => {

    if (!user || rolesLoading || permissionsLoading) {

      return;

    }



    if (workspace === 'overview') {

      return;

    }



    const selectedItem = visibleNavigation.find(

      (item) => item.workspace === workspace,

    );



    if (!selectedItem) {

      setWorkspace('overview');

    }

  }, [

    permissionsLoading,

    rolesLoading,

    user,

    visibleNavigation,

    workspace,

  ]);



  const handleSignOut = () => {

    clearAccessToken();

    setRoles([]);

    setRolesError('');

    setPermissions([]);

    setPermissionsError('');

    setWorkspace('overview');

    setUser(null);

  };



  const handleWorkspaceChange = (

    nextWorkspace: WorkspaceMode,

  ) => {

    if (nextWorkspace === 'overview') {

      setWorkspace('overview');

      return;

    }



    const navigationItem = visibleNavigation.find(

      (item) => item.workspace === nextWorkspace,

    );



    if (navigationItem) {

      setWorkspace(nextWorkspace);

    }

  };



  const renderWorkspace = () => {

    if (workspace === 'projects') {

      if (!hasPermission('project.read')) {

        return null;

      }



      return <ProjectManagementWorkspace />;

    }

    if (workspace === 'landRequirements') {
      if (!hasPermission('land_requirement.read')) {
        return null;
      }

      return (
        <LandRequirementWorkspace
          permissions={permissionSet}
        />
      );
    }

    if (workspace === 'acquisitionCases') {
      if (!hasPermission('acquisition_case.read')) {
        return null;
      }

      return (
        <AcquisitionCaseWorkspace
          permissions={permissionSet}
        />
      );
    }

    if (workspace === 'parcels') {
      if (!hasPermission('parcel.read')) {
        return null;
      }

      return (
        <ParcelManagementWorkspace
          permissions={permissionSet}
        />
      );
    }



    if (workspace === 'survey') {
      if (!hasPermission('survey.read')) {
        return null;
      }

      return <SurveyManagementWorkspace />;
    }


    if (workspace === 'users') {

      if (!hasPermission('user.read')) {

        return null;

      }



      return (

        <UserManagementWorkspace

          currentUser={user!}

        />

      );

    }



    if (workspace === 'departments') {

      if (!hasPermission('department.read')) {

        return null;

      }



      return <DepartmentManagementWorkspace />;

    }



    if (workspace === 'authorities') {

      if (!hasPermission('authority.read')) {

        return null;

      }



      return <AuthorityManagementWorkspace />;

    }



    if (workspace === 'permissions') {

      if (!hasPermission('permission.read')) {

        return null;

      }



      return <PermissionManagementWorkspace />;

    }



    if (workspace === 'audit') {

      if (!hasPermission('audit.read')) {

        return null;

      }



      return <AuditHistoryWorkspace />;

    }



    const isAdministration =

      applicationArea === 'administration';



    const areaTitle = isAdministration
      ? t('workspace.systemAdministration')
      : applicationArea === 'operations'
        ? t('workspace.landAcquisitionOperations')
        : t('workspace.aakarAccess');



    const areaDescription = isAdministration
      ? t('workspace.platformGovernance')
      : applicationArea === 'operations'
        ? t('workspace.projectLifecycle')
        : t('workspace.rolePermissionContext');



    return (

      <section className="workspace-home">

        <div className="workspace-home-head">

          <div>

            <p className="workspace-eyebrow">
                {isAdministration
                  ? t('workspace.governance').toUpperCase()
                  : t('workspace.landAcquisitionOperations').toUpperCase()}
              </p>

            <h1>{areaTitle}</h1>

            <p>{areaDescription}</p>

          </div>



          <div className="workspace-secure-badge">
              <span className="status-dot" />
              {t('common.secureSession')}
            </div>

        </div>



        <div className="workspace-home-grid">

          <article className="workspace-info-card workspace-info-card-primary">

            <span className="workspace-card-label">
                {t('workspace.rolePermissionContext').toUpperCase()}
              </span>
              <strong>{roles[0]?.name ?? t('common.unavailable')}</strong>
              <p>
                {roles.length > 1
                  ? `${roles.length} ${t('common.permissions')}`
                  : roles.length === 1
                    ? t('overview.accessContextLoaded')
                    : t('overview.roleRequired')}
              </p>

          </article>



          <article className="workspace-info-card">

            <span className="workspace-card-label">
                {t('overview.effectiveAccess')}
              </span>
              <strong>
                {permissions.length} {t('common.permissions')}
              </strong>
              <p>{t('workspace.rolePermissionContext')}</p>

          </article>



          <article className="workspace-info-card">

            <span className="workspace-card-label">
                {t('overview.currentUser')}
              </span>

            <strong>{user!.full_name}</strong>

            <p>{user!.email}</p>

          </article>

        </div>



        <section className="workspace-module-panel">

          <div>

            <span className="workspace-eyebrow">
                {t('overview.authorizedModules').toUpperCase()}
              </span>
              <h2>{t('overview.authorizedModules')}</h2>

          </div>



          {visibleNavigation.length > 0 ? (

            <div className="workspace-module-list">

              {visibleNavigation.map((item) => (

                <button

                  type="button"

                  key={item.workspace}

                  className="workspace-module-row"

                  onClick={() => handleWorkspaceChange(item.workspace)}

                >

                  <span className="workspace-module-icon">

                    {isAdministration ? '⚙' : '▣'}

                  </span>

                  <span>

                    <strong>{item.label}</strong>

                    <small>{t('common.authorizedModule')}</small>

                  </span>

                  <span className="workspace-module-arrow">→</span>

                </button>

              ))}

            </div>

          ) : (

            <div className="workspace-empty-state">
                <strong>{t('overview.noActiveModules')}</strong>
                <p>{t('overview.roleRequired')}</p>
              </div>

          )}

        </section>



        {rolesError && (

          <div className="error-message" role="alert">

            {rolesError}

          </div>

        )}



        {permissionsError && (

          <div className="error-message" role="alert">

            {permissionsError}

          </div>

        )}

      </section>

    );

  };



  if (checkingSession) {

    return (

      <main className="auth-shell">

        <div className="loading-screen">

          <div className="brand-mark">आ</div>

          <p>{t('common.secureSession')}...</p>

        </div>

      </main>

    );

  }



  if (user) {

    const isAdministration =

      applicationArea === 'administration';



    const shellTitle = isAdministration
      ? t('workspace.systemAdministration')
      : applicationArea === 'operations'
        ? t('workspace.landAcquisitionOperations')
        : t('workspace.aakarAccess');

    const shellSubtitle = isAdministration
      ? t('workspace.platformGovernance')
      : applicationArea === 'operations'
        ? t('workspace.projectLifecycle')
        : t('workspace.rolePermissionContext');



    return (

      <main

        className={`app-shell aakar-v2-shell ${

          applicationArea === 'administration'

            ? 'aakar-admin-shell'

            : applicationArea === 'operations'

              ? 'aakar-operations-shell'

              : 'aakar-restricted-shell'

        }`}

      >

        <aside className="aakar-v2-sidebar">

          <div className="aakar-v2-brand">

            <div className="brand-mark brand-mark-small">आ</div>

            <div>

              <strong>AAKAR</strong>

              <span>आकार</span>

            </div>

          </div>



          <div className="aakar-v2-area-card">

            <span>{t('workspace.aakarAccess').toUpperCase()}</span>

            <strong>{shellTitle}</strong>

            <small>{shellSubtitle}</small>

          </div>



          <nav

            className="aakar-v2-navigation"

            aria-label={t('workspace.aakarAccess')}

          >

            <button

              type="button"

              className={

                workspace === 'overview'

                  ? 'aakar-v2-nav-item aakar-v2-nav-item-active'

                  : 'aakar-v2-nav-item'

              }

              onClick={() => handleWorkspaceChange('overview')}

            >

              <span className="aakar-v2-nav-icon">⌂</span>

              <span>{t('workspace.overview')}</span>

            </button>



            {applicationArea === 'operations' &&

              visibleOperations.length > 0 && (

                <div className="aakar-v2-nav-group">

                  <span className="aakar-v2-nav-label">
                    {t('workspace.operations').toUpperCase()}
                  </span>

                  {visibleOperations.map((item) => (

                    <button

                      type="button"

                      key={item.workspace}

                      className={

                        workspace === item.workspace

                          ? 'aakar-v2-nav-item aakar-v2-nav-item-active'

                          : 'aakar-v2-nav-item'

                      }

                      onClick={() => handleWorkspaceChange(item.workspace)}

                    >

                      <span className="aakar-v2-nav-icon">▣</span>

                      <span>{

                        item.workspace === 'projects'

                          ? t('nav.projectManagement')

                          : item.workspace === 'users'

                            ? t('nav.userManagement')

                            : item.workspace === 'departments'

                              ? t('nav.departmentManagement')

                              : item.workspace === 'authorities'

                                ? t('nav.authorityManagement')

                                : item.workspace === 'permissions'

                                  ? t('nav.permissionManagement')

                                  : item.workspace === 'audit'

                                    ? t('nav.auditHistory')

                                    : item.label

                      }</span>

                    </button>

                  ))}

                </div>

              )}



            {applicationArea === 'administration' &&

              visibleAdministration.length > 0 && (

                <div className="aakar-v2-nav-group">

                  <span className="aakar-v2-nav-label">
                    {t('workspace.governance').toUpperCase()}
                  </span>

                  {visibleAdministration.map((item) => (

                    <button

                      type="button"

                      key={item.workspace}

                      className={

                        workspace === item.workspace

                          ? 'aakar-v2-nav-item aakar-v2-nav-item-active'

                          : 'aakar-v2-nav-item'

                      }

                      onClick={() => handleWorkspaceChange(item.workspace)}

                    >

                      <span className="aakar-v2-nav-icon">⚙</span>

                      <span>{

                        item.workspace === 'projects'

                          ? t('nav.projectManagement')

                          : item.workspace === 'users'

                            ? t('nav.userManagement')

                            : item.workspace === 'departments'

                              ? t('nav.departmentManagement')

                              : item.workspace === 'authorities'

                                ? t('nav.authorityManagement')

                                : item.workspace === 'permissions'

                                  ? t('nav.permissionManagement')

                                  : item.workspace === 'audit'

                                    ? t('nav.auditHistory')

                                    : item.label

                      }</span>

                    </button>

                  ))}

                </div>

              )}

          </nav>



          <div className="aakar-v2-sidebar-footer">

            <div className="aakar-v2-user">

              <div className="aakar-v2-user-avatar">

                {user.full_name.charAt(0).toUpperCase()}

              </div>

              <div>

                <strong>{user.full_name}</strong>

                <span>

                  {roles[0]?.name ?? 'Authenticated user'}

                </span>

              </div>

            </div>



            <button

              type="button"

              className="aakar-v2-signout"

              onClick={handleSignOut}

            >

              {t('common.signOut')}

            </button>

          </div>

        </aside>



        <section className="aakar-v2-main">

          <header className="aakar-v2-topbar">

            <div>

              <p className="aakar-v2-breadcrumb">

                AAKAR / {shellTitle}

              </p>

              <h1>

                {workspace === 'overview'

                  ? t('overview.title')

                  : visibleNavigation.find(

                      (item) => item.workspace === workspace,

                    )?.workspace === 'projects'

                    ? t('nav.projectManagement')

                    : visibleNavigation.find((item) => item.workspace === workspace)?.workspace === 'users'

                      ? t('nav.userManagement')

                      : visibleNavigation.find((item) => item.workspace === workspace)?.workspace === 'departments'

                        ? t('nav.departmentManagement')

                        : visibleNavigation.find((item) => item.workspace === workspace)?.workspace === 'authorities'

                          ? t('nav.authorityManagement')

                          : visibleNavigation.find((item) => item.workspace === workspace)?.workspace === 'permissions'

                            ? t('nav.permissionManagement')

                            : visibleNavigation.find((item) => item.workspace === workspace)?.workspace === 'audit'

                              ? t('nav.auditHistory')

                              : visibleNavigation.find((item) => item.workspace === workspace)?.label ?? t('workspace.aakarAccess')}

              </h1>

            </div>



            <div className="aakar-v2-topbar-meta">

              <LanguageSelector />

              {permissionsLoading || rolesLoading ? (

                <span className="aakar-v2-access-status is-loading">

                  {t('common.loadingAccess')}

                </span>

              ) : (

                <span className="aakar-v2-access-status">

                  <span className="status-dot" />

                  {t('common.secureSession')}

                </span>

              )}

            </div>

          </header>



          <div className="aakar-v2-content">

            {rolesLoading || permissionsLoading ? (

              <section className="workspace-access-loading">

                <div className="workspace-loading-mark">आ</div>

                <p>{t('common.preparingWorkspace')}</p>

              </section>

            ) : (

              renderWorkspace()

            )}

          </div>

        </section>

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

            <p className="eyebrow">

              NATIONAL LAND MANAGEMENT SYSTEM

            </p>



            <h1>

              Shaping land.

              <br />

              Empowering development.

            </h1>



            <p>

              Secure access to the AAKAR platform

              for digital land acquisition workflows,

              records, and operational monitoring.

            </p>

          </div>



          <div className="visual-footer">

            <span>

              Secure government access

            </span>



            <span>AAKAR v0.1</span>

          </div>

        </div>

      </section>



      <section className="auth-panel">

        <div className="aakar-auth-language">

          <LanguageSelector />

        </div>

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

              onSwitchToRegister={() =>

                setMode('register')

              }

            />

          ) : (

            <RegisterForm

              onRegistered={() =>

                setMode('login')

              }

              onSwitchToLogin={() =>

                setMode('login')

              }

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

  const [users, setUsers] =

    useState<ManagedUser[]>([]);



  const [selectedUserId, setSelectedUserId] =

    useState<string | null>(null);



  const [selectedUser, setSelectedUser] =

    useState<ManagedUserDetail | null>(null);



  const [search, setSearch] = useState('');



  const [activeFilter, setActiveFilter] =

    useState<

      'all' | 'active' | 'inactive'

    >('all');



  const [offset, setOffset] = useState(0);

  const limit = 25;



  const [total, setTotal] = useState(0);



  const [loadingUsers, setLoadingUsers] =

    useState(true);



  const [usersError, setUsersError] =

    useState('');



  const [loadingDetails, setLoadingDetails] =

    useState(false);



  const [detailsError, setDetailsError] =

    useState('');



  const [savingProfile, setSavingProfile] =

    useState(false);



  const [profileError, setProfileError] =

    useState('');



  const [profileSuccess, setProfileSuccess] =

    useState('');



  const [changingStatus, setChangingStatus] =

    useState(false);



  const [showCreateForm, setShowCreateForm] =

    useState(false);



  const [createForm, setCreateForm] =

    useState({

      full_name: '',

      email: '',

      password: '',

    });



  const [createError, setCreateError] =

    useState('');



  const [createSuccess, setCreateSuccess] =

    useState('');



  const [creatingUser, setCreatingUser] =

    useState(false);



  const [availableRoles, setAvailableRoles] =

    useState<Role[]>([]);



  const [loadingRoles, setLoadingRoles] =

    useState(false);



  const [rolesError, setRolesError] =

    useState('');



  const [selectedRoleCode, setSelectedRoleCode] =

    useState('');



  const [assigningRole, setAssigningRole] =

    useState(false);



  const [removingRoleCode, setRemovingRoleCode] =

    useState<string | null>(null);



  const [roleError, setRoleError] =

    useState('');



  const [roleSuccess, setRoleSuccess] =

    useState('');



  const selectedUserIsCurrentUser =

    selectedUser?.id === currentUser.id ||

    selectedUserId === currentUser.id;



  const activeFilterValue =

    activeFilter === 'all'

      ? undefined

      : activeFilter === 'active';



  const totalPages = Math.max(

    1,

    Math.ceil(total / limit),

  );



  const currentPage =

    Math.floor(offset / limit) + 1;



  const loadUsers = useCallback(async () => {

    setLoadingUsers(true);

    setUsersError('');



    try {

      const response =

        await listManagedUsers({

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

  }, [

    activeFilterValue,

    offset,

    search,

  ]);



  const loadAvailableRoles = useCallback(async () => {

    setLoadingRoles(true);

    setRolesError('');



    try {

      const response = await listRoles();

      setAvailableRoles(response);

    } catch (requestError) {

      setRolesError(

        requestError instanceof Error

          ? requestError.message

          : 'Unable to load available roles.',

      );

    } finally {

      setLoadingRoles(false);

    }

  }, []);



  const loadUserDetails = async (

    userId: string,

  ) => {

    setSelectedUserId(userId);

    setSelectedUser(null);

    setLoadingDetails(true);

    setDetailsError('');

    setProfileError('');

    setProfileSuccess('');

    setRoleError('');

    setRoleSuccess('');

    setSelectedRoleCode('');



    try {

      const response =

        await getManagedUser(userId);



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



  useEffect(() => {

    void loadAvailableRoles();

  }, [loadAvailableRoles]);



  const handleSearchChange = (

    value: string,

  ) => {

    setSearch(value);

    setOffset(0);

    setSelectedUserId(null);

    setSelectedUser(null);

    setRoleError('');

    setRoleSuccess('');

    setSelectedRoleCode('');

  };



  const handleFilterChange = (

    value:

      | 'all'

      | 'active'

      | 'inactive',

  ) => {

    setActiveFilter(value);

    setOffset(0);

    setSelectedUserId(null);

    setSelectedUser(null);

    setRoleError('');

    setRoleSuccess('');

    setSelectedRoleCode('');

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

      const updatedUser =

        await updateManagedUser(

          selectedUser.id,

          values,

        );



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

          item.id === updatedUser.id

            ? {

                ...item,

                ...updatedUser,

              }

            : item,

        ),

      );



      setProfileSuccess(

        'User profile updated successfully.',

      );

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

      setProfileError(

        'You cannot change your own account status.',

      );

      return;

    }



    const nextStatus =

      !selectedUser.is_active;



    setChangingStatus(true);

    setProfileError('');

    setProfileSuccess('');



    try {

      const updatedUser =

        await updateManagedUserStatus(

          selectedUser.id,

          {

            is_active: nextStatus,

          },

        );



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

          item.id === updatedUser.id

            ? {

                ...item,

                ...updatedUser,

              }

            : item,

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



  const handleAssignRole = async () => {

    if (!selectedUser || !selectedRoleCode) {

      return;

    }



    const roleAlreadyAssigned = selectedUser.roles.some(

      (role) => role.code === selectedRoleCode,

    );



    if (roleAlreadyAssigned) {

      setRoleError('This role is already assigned to the user.');

      return;

    }



    setAssigningRole(true);

    setRoleError('');

    setRoleSuccess('');



    try {

      await assignUserRole(selectedUser.id, {

        role_code: selectedRoleCode,

      });



      const refreshedUser =

        await getManagedUser(selectedUser.id);



      setSelectedUser(refreshedUser);

      setSelectedRoleCode('');

      setRoleSuccess('Role assigned successfully.');

    } catch (requestError) {

      setRoleError(

        requestError instanceof Error

          ? requestError.message

          : 'Unable to assign the selected role.',

      );

    } finally {

      setAssigningRole(false);

    }

  };



  const handleRemoveRole = async (

    roleCode: string,

  ) => {

    if (!selectedUser) {

      return;

    }



    setRemovingRoleCode(roleCode);

    setRoleError('');

    setRoleSuccess('');



    try {

      await removeUserRole(

        selectedUser.id,

        roleCode,

      );



      const refreshedUser =

        await getManagedUser(selectedUser.id);



      setSelectedUser(refreshedUser);

      setRoleSuccess('Role removed successfully.');

    } catch (requestError) {

      setRoleError(

        requestError instanceof Error

          ? requestError.message

          : 'Unable to remove the selected role.',

      );

    } finally {

      setRemovingRoleCode(null);

    }

  };



  const assignableRoles = availableRoles.filter(

    (role) =>

      !selectedUser?.roles.some(

        (assignedRole) =>

          assignedRole.code === role.code,

      ),

  );



  const handleCreateUser = async (

    event: FormEvent<HTMLFormElement>,

  ) => {

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



      setCreateSuccess(

        'User account created successfully.',

      );



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

          <p className="roles-eyebrow">

            IDENTITY & ADMINISTRATION

          </p>



          <h1>User Management</h1>



          <p>

            Manage AAKAR platform accounts,

            account status, and user profile

            information.

          </p>

        </div>



        <div className="management-actions">

          <button

            type="button"

            className="secondary-button"

            onClick={() => {

              setShowCreateForm(

                (current) => !current,

              );



              setCreateError('');

              setCreateSuccess('');

            }}

          >

            {showCreateForm

              ? 'Close form'

              : 'Create user'}

          </button>

        </div>

      </div>



      {createSuccess &&

        !showCreateForm && (

          <div

            className="success-message"

            role="status"

          >

            {createSuccess}

          </div>

        )}



      {showCreateForm && (

        <form

          className="management-form-card"

          onSubmit={handleCreateUser}

        >

          <div className="management-card-heading">

            <div>

              <p className="roles-eyebrow">

                NEW ACCOUNT

              </p>



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

                    full_name:

                      event.target.value,

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

                    email:

                      event.target.value,

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

                    password:

                      event.target.value,

                  }))

                }

                minLength={8}

                maxLength={128}

                required

              />

            </label>

          </div>



          {createError && (

            <div

              className="error-message"

              role="alert"

            >

              {createError}

            </div>

          )}



          <div className="management-form-actions">

            <button

              type="submit"

              className="primary-button"

              disabled={creatingUser}

            >

              {creatingUser

                ? 'Creating user...'

                : 'Create user'}

            </button>

          </div>

        </form>

      )}



      <div className="management-layout">

        <section className="users-panel">

          <div className="users-toolbar">

            <div className="search-field">

              <label htmlFor="user-search">

                Search users

              </label>



              <input

                id="user-search"

                type="search"

                placeholder="Search by name or email..."

                value={search}

                onChange={(event) =>

                  handleSearchChange(

                    event.target.value,

                  )

                }

              />

            </div>



            <div className="filter-field">

              <label htmlFor="user-status-filter">

                Status

              </label>



              <select

                id="user-status-filter"

                value={activeFilter}

                onChange={(event) =>

                  handleFilterChange(

                    event.target.value as

                      | 'all'

                      | 'active'

                      | 'inactive',

                  )

                }

              >

                <option value="all">

                  All accounts

                </option>



                <option value="active">

                  Active

                </option>



                <option value="inactive">

                  Inactive

                </option>

              </select>

            </div>

          </div>



          {usersError && (

            <div

              className="error-message"

              role="alert"

            >

              {usersError}

            </div>

          )}



          <div className="users-summary">

            <span>

              {total}{' '}

              {total === 1

                ? 'account'

                : 'accounts'}

            </span>



            <span>

              Page {currentPage} of{' '}

              {totalPages}

            </span>

          </div>



          {loadingUsers ? (

            <div className="management-empty-state">

              <strong>

                Loading users...

              </strong>



              <p>

                Retrieving accounts from the

                secure AAKAR API.

              </p>

            </div>

          ) : users.length === 0 ? (

            <div className="management-empty-state">

              <strong>

                No users found

              </strong>



              <p>

                Try adjusting the search text or

                account-status filter.

              </p>

            </div>

          ) : (

            <div className="user-list">

              {users.map((managedUser) => {

                const isSelected =

                  managedUser.id ===

                  selectedUserId;



                const isCurrent =

                  managedUser.id ===

                  currentUser.id;



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

                      void loadUserDetails(

                        managedUser.id,

                      );

                    }}

                  >

                    <div className="user-list-main">

                      <strong>

                        {managedUser.full_name}

                      </strong>



                      <span>

                        {managedUser.email}

                      </span>

                    </div>



                    <div className="user-list-meta">

                      <span

                        className={

                          managedUser.is_active

                            ? 'user-status user-status-active'

                            : 'user-status user-status-inactive'

                        }

                      >

                        {managedUser.is_active

                          ? 'Active'

                          : 'Inactive'}

                      </span>



                      {isCurrent && (

                        <span className="current-user-badge">

                          You

                        </span>

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

              disabled={

                offset === 0 ||

                loadingUsers

              }

              onClick={() =>

                setOffset(

                  (currentOffset) =>

                    Math.max(

                      0,

                      currentOffset - limit,

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

                offset + limit >= total ||

                loadingUsers ||

                total === 0

              }

              onClick={() =>

                setOffset(

                  (currentOffset) =>

                    currentOffset + limit,

                )

              }

            >

              Next

            </button>

          </div>

        </section>



        <section className="user-detail-panel">

          {loadingDetails && (

            <div className="management-empty-state">

              <strong>

                Loading user details...

              </strong>



              <p>

                Fetching the selected account

                and assigned roles.

              </p>

            </div>

          )}



          {!loadingDetails &&

            detailsError && (

              <div

                className="error-message"

                role="alert"

              >

                {detailsError}

              </div>

            )}



          {!loadingDetails &&

            !detailsError &&

            !selectedUser && (

              <div className="management-empty-state management-empty-state-large">

                <span className="detail-placeholder-icon">

                  आ

                </span>



                <strong>

                  Select an account

                </strong>



                <p>

                  Choose a user from the list to

                  inspect profile information,

                  account status, and assigned

                  roles.

                </p>

              </div>

            )}



          {!loadingDetails &&

            !detailsError &&

            selectedUser && (

              <UserDetailPanel

                user={selectedUser}

                isCurrentUser={

                  selectedUserIsCurrentUser

                }

                savingProfile={

                  savingProfile

                }

                changingStatus={

                  changingStatus

                }

                profileError={profileError}

                profileSuccess={

                  profileSuccess

                }

                availableRoles={assignableRoles}

                loadingRoles={loadingRoles}

                rolesError={rolesError}

                selectedRoleCode={selectedRoleCode}

                assigningRole={assigningRole}

                removingRoleCode={removingRoleCode}

                roleError={roleError}

                roleSuccess={roleSuccess}

                onRoleCodeChange={setSelectedRoleCode}

                onAssignRole={() => {

                  void handleAssignRole();

                }}

                onRemoveRole={(roleCode) => {

                  void handleRemoveRole(roleCode);

                }}

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

  availableRoles: Role[];

  loadingRoles: boolean;

  rolesError: string;

  selectedRoleCode: string;

  assigningRole: boolean;

  removingRoleCode: string | null;

  roleError: string;

  roleSuccess: string;

  onRoleCodeChange: (roleCode: string) => void;

  onAssignRole: () => void;

  onRemoveRole: (roleCode: string) => void;

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

  availableRoles,

  loadingRoles,

  rolesError,

  selectedRoleCode,

  assigningRole,

  removingRoleCode,

  roleError,

  roleSuccess,

  onRoleCodeChange,

  onAssignRole,

  onRemoveRole,

  onSave,

  onStatusChange,

}: UserDetailPanelProps) {

  const [fullName, setFullName] =

    useState(user.full_name);



  const [email, setEmail] =

    useState(user.email);



  return (

    <div className="detail-card">

      <div className="detail-card-heading">

        <div>

          <p className="roles-eyebrow">

            ACCOUNT DETAILS

          </p>



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

          {user.is_active

            ? 'Active'

            : 'Inactive'}

        </span>

      </div>



      {profileError && (

        <div

          className="error-message"

          role="alert"

        >

          {profileError}

        </div>

      )}



      {profileSuccess && (

        <div

          className="success-message"

          role="status"

        >

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

            onChange={(event) =>

              setFullName(

                event.target.value,

              )

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

            value={email}

            onChange={(event) =>

              setEmail(event.target.value)

            }

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

            {savingProfile

              ? 'Saving...'

              : 'Save changes'}

          </button>



          <button

            type="button"

            className="secondary-button"

            disabled={

              changingStatus ||

              isCurrentUser

            }

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

          <span>

            Email verification

          </span>



          <strong>

            {user.is_email_verified

              ? 'Verified'

              : 'Not verified'}

          </strong>

        </div>



        <div className="profile-item">

          <span>Last login</span>



          <strong>

            {formatDateTime(

              user.last_login_at,

            )}

          </strong>

        </div>



        <div className="profile-item">

          <span>Created</span>



          <strong>

            {formatDateTime(

              user.created_at,

            )}

          </strong>

        </div>



        <div className="profile-item">

          <span>Updated</span>



          <strong>

            {formatDateTime(

              user.updated_at,

            )}

          </strong>

        </div>

      </div>



      <section className="assigned-role-panel">

        <div className="roles-heading">

          <div>

            <p className="roles-eyebrow">

              ACCESS CONTROL

            </p>



            <h3>Assigned roles</h3>

          </div>



          <span className="role-count">

            {user.roles.length}{' '}

            {user.roles.length === 1

              ? 'role'

              : 'roles'}

          </span>

        </div>



        {roleError && (

          <div

            className="error-message"

            role="alert"

          >

            {roleError}

          </div>

        )}



        {roleSuccess && (

          <div

            className="success-message"

            role="status"

          >

            {roleSuccess}

          </div>

        )}



        <div className="role-assignment-panel">

          <div>

            <p className="role-assignment-label">

              ASSIGN ROLE

            </p>



            <p className="role-assignment-help">

              Select an active AAKAR role to grant

              this account access.

            </p>

          </div>



          <div className="role-assignment-controls">

            <select

              value={selectedRoleCode}

              onChange={(event) =>

                onRoleCodeChange(event.target.value)

              }

              disabled={

                loadingRoles ||

                assigningRole ||

                availableRoles.length === 0

              }

              aria-label="Select role to assign"

            >

              <option value="">

                {loadingRoles

                  ? 'Loading roles...'

                  : availableRoles.length === 0

                    ? 'No additional roles available'

                    : 'Select a role...'}

              </option>



              {availableRoles.map((role) => (

                <option

                  key={role.id}

                  value={role.code}

                >

                  {role.name || formatRoleName(role.code)}

                  {' — '}

                  {formatScopeLevel(role.scope_level)}

                </option>

              ))}

            </select>



            <button

              type="button"

              className="primary-button"

              disabled={

                !selectedRoleCode ||

                assigningRole ||

                loadingRoles

              }

              onClick={onAssignRole}

            >

              {assigningRole

                ? 'Assigning...'

                : 'Assign role'}

            </button>

          </div>



          {rolesError && (

            <p className="role-assignment-error">

              {rolesError}

            </p>

          )}

        </div>



        {user.roles.length === 0 ? (

          <div className="no-role-card">

            <span className="no-role-icon">

              !

            </span>



            <div>

              <strong>

                No active roles

              </strong>



              <p>

                This account currently has no

                active AAKAR roles assigned.

              </p>

            </div>

          </div>

        ) : (

          <div className="role-list">

            {user.roles.map((role) => (

              <article

                className="role-card"

                key={role.id}

              >

                <div className="role-card-top">

                  <div>

                    <span className="role-code">

                      {role.code}

                    </span>



                    <h3>

                      {role.name ||

                        formatRoleName(

                          role.code,

                        )}

                    </h3>

                  </div>



                  <div className="role-card-actions">

                    <span className="scope-badge">

                      {formatScopeLevel(

                        role.scope_level,

                      )}

                    </span>



                    <button

                      type="button"

                      className="ghost-button role-remove-button"

                      disabled={

                        removingRoleCode ===

                        role.code

                      }

                      onClick={() =>

                        onRemoveRole(role.code)

                      }

                    >

                      {removingRoleCode ===

                      role.code

                        ? 'Removing...'

                        : 'Remove'}

                    </button>

                  </div>

                </div>



                {role.description && (

                  <p className="role-description">

                    {role.description}

                  </p>

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

            Your own account status cannot be

            changed from User Management. Role

            assignments are managed by authorized

            administrators.

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

  const [password, setPassword] =

    useState('');



  const [error, setError] = useState('');

  const [loading, setLoading] =

    useState(false);



  const handleSubmit = async (

    event: FormEvent<HTMLFormElement>,

  ) => {

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

        <p className="eyebrow">

          SECURE SIGN-IN

        </p>



        <h2>Welcome back</h2>



        <p>

          Sign in to access your AAKAR

          workspace.

        </p>

      </div>



      <form

        className="auth-form"

        onSubmit={handleSubmit}

      >

        <label htmlFor="login-email">

          Email address



          <input

            id="login-email"

            type="email"

            autoComplete="email"

            value={email}

            onChange={(event) =>

              setEmail(event.target.value)

            }

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

            onChange={(event) =>

              setPassword(

                event.target.value,

              )

            }

            placeholder="Enter your password"

            required

          />

        </label>



        {error && (

          <div

            className="error-message"

            role="alert"

          >

            {error}

          </div>

        )}



        <button

          className="primary-button"

          type="submit"

          disabled={loading}

        >

          {loading

            ? 'Signing in...'

            : 'Sign in'}

        </button>

      </form>



      <p className="auth-switch">

        New to AAKAR?



        <button

          type="button"

          onClick={onSwitchToRegister}

        >

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

  const [fullName, setFullName] =

    useState('');



  const [email, setEmail] =

    useState('');



  const [password, setPassword] =

    useState('');



  const [error, setError] =

    useState('');



  const [success, setSuccess] =

    useState('');



  const [loading, setLoading] =

    useState(false);



  const handleSubmit = async (

    event: FormEvent<HTMLFormElement>,

  ) => {

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



      setSuccess(

        'Account created successfully. You can now sign in.',

      );

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

        <p className="eyebrow">

          ACCOUNT REGISTRATION

        </p>



        <h2>Create your account</h2>



        <p>

          Set up an AAKAR account for secure

          platform access.

        </p>

      </div>



      <form

        className="auth-form"

        onSubmit={handleSubmit}

      >

        <label htmlFor="register-name">

          Full name



          <input

            id="register-name"

            type="text"

            autoComplete="name"

            value={fullName}

            onChange={(event) =>

              setFullName(

                event.target.value,

              )

            }

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

            onChange={(event) =>

              setEmail(

                event.target.value,

              )

            }

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

            onChange={(event) =>

              setPassword(

                event.target.value,

              )

            }

            placeholder="Minimum 8 characters"

            minLength={8}

            maxLength={128}

            required

          />

        </label>



        {error && (

          <div

            className="error-message"

            role="alert"

          >

            {error}

          </div>

        )}



        {success && (

          <div

            className="success-message"

            role="status"

          >

            {success}

          </div>

        )}



        <button

          className="primary-button"

          type="submit"

          disabled={loading}

        >

          {loading

            ? 'Creating account...'

            : 'Create account'}

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