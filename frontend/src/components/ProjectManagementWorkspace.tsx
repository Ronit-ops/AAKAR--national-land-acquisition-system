import { useCallback, useEffect, useMemo, useState } from 'react';

import type { FormEvent } from 'react';



import {

  activateProject,

  closeProject,

  createProject,

  getProject,

  listAuthorities,

  listProjects,

  updateProject,

} from '../lib/api';



import type {

  CreateProjectRequest,

  Project,

  ProjectStatus,

  UpdateProjectRequest,

} from '../types/projects';



import type { Authority } from '../types/organization';

import { useAakarLanguage } from '../i18n/i18n';



const PAGE_SIZE = 10;



const PROJECT_STATUSES: ProjectStatus[] = [

  'DRAFT',

  'ACTIVE',

  'CLOSED',

];



interface ProjectFormValues {

  code: string;

  name: string;

  sector: string;

  description: string;

  responsible_authority_id: string;

}



const EMPTY_FORM: ProjectFormValues = {

  code: '',

  name: '',

  sector: '',

  description: '',

  responsible_authority_id: '',

};



function formatStatus(
  status: ProjectStatus,
  translate: (key: string) => string,
): string {
  switch (status) {
    case 'ACTIVE':
      return translate('project.active');
    case 'CLOSED':
      return translate('project.closed');
    case 'DRAFT':
    default:
      return translate('project.draft');
  }
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



function validateForm(values: ProjectFormValues): string {

  const code = values.code.trim();

  const name = values.name.trim();

  const sector = values.sector.trim();

  const description = values.description.trim();



  if (!code) {

    return 'Project code is required.';

  }



  if (code.length > 50) {

    return 'Project code must be 50 characters or fewer.';

  }



  if (!name) {

    return 'Project name is required.';

  }



  if (name.length < 2) {

    return 'Project name must contain at least 2 characters.';

  }



  if (name.length > 200) {

    return 'Project name must be 200 characters or fewer.';

  }



  if (!sector) {

    return 'Project sector is required.';

  }



  if (sector.length > 100) {

    return 'Project sector must be 100 characters or fewer.';

  }



  if (description.length > 5000) {

    return 'Description must be 5000 characters or fewer.';

  }



  if (!values.responsible_authority_id) {

    return 'Please select a responsible authority.';

  }



  return '';

}



function getStatusClass(status: ProjectStatus): string {

  switch (status) {

    case 'ACTIVE':

      return 'project-status project-status-active';



    case 'CLOSED':

      return 'project-status project-status-closed';



    case 'DRAFT':

    default:

      return 'project-status project-status-draft';

  }

}



export default function ProjectManagementWorkspace() {
  const { t } = useAakarLanguage();

  const [projects, setProjects] = useState<Project[]>([]);

  const [authorities, setAuthorities] = useState<Authority[]>([]);



  const [selectedProjectId, setSelectedProjectId] =

    useState<string | null>(null);



  const [selectedProject, setSelectedProject] =

    useState<Project | null>(null);



  const [search, setSearch] = useState('');

  const [statusFilter, setStatusFilter] =

    useState<'all' | ProjectStatus>('all');



  const [offset, setOffset] = useState(0);

  const [total, setTotal] = useState(0);



  const [loadingProjects, setLoadingProjects] = useState(true);

  const [loadingAuthorities, setLoadingAuthorities] = useState(true);



  const [projectsError, setProjectsError] = useState('');

  const [authoritiesError, setAuthoritiesError] = useState('');



  const [showForm, setShowForm] = useState(false);

  const [editingProjectId, setEditingProjectId] =

    useState<string | null>(null);



  const [form, setForm] =

    useState<ProjectFormValues>(EMPTY_FORM);



  const [formError, setFormError] = useState('');

  const [formSuccess, setFormSuccess] = useState('');

  const [savingForm, setSavingForm] = useState(false);



  const [changingStatus, setChangingStatus] = useState(false);



  const totalPages = Math.max(

    1,

    Math.ceil(total / PAGE_SIZE),

  );



  const currentPage =

    Math.floor(offset / PAGE_SIZE) + 1;



  const activeAuthorities = useMemo(

    () =>

      authorities.filter(

        (authority) => authority.is_active,

      ),

    [authorities],

  );



  const filteredProjects = useMemo(() => {

    if (statusFilter === 'all') {

      return projects;

    }



    return projects.filter(

      (project) => project.status === statusFilter,

    );

  }, [projects, statusFilter]);



  const getAuthorityName = useCallback(

    (authorityId: string): string =>

      authorities.find(

        (authority) => authority.id === authorityId,

      )?.name ?? 'Unknown authority',

    [authorities],

  );



  const loadProjects = useCallback(async () => {

    setLoadingProjects(true);

    setProjectsError('');



    try {

      const response = await listProjects({

        search: search.trim() || undefined,

        offset,

        limit: PAGE_SIZE,

      });



      setProjects(response.items);

      setTotal(response.total);



      if (

        selectedProjectId &&

        !response.items.some(

          (project) => project.id === selectedProjectId,

        )

      ) {

        setSelectedProjectId(null);

        setSelectedProject(null);

      }

    } catch (error) {

      setProjectsError(

        getErrorMessage(

          error,

          'Unable to load projects.',

        ),

      );

    } finally {

      setLoadingProjects(false);

    }

  }, [offset, search, selectedProjectId]);



  const loadAuthorities = useCallback(async () => {

    setLoadingAuthorities(true);

    setAuthoritiesError('');



    try {

      const response = await listAuthorities({

        is_active: true,

        offset: 0,

        limit: 100,

      });



      setAuthorities(response.items);

    } catch (error) {

      setAuthoritiesError(

        getErrorMessage(

          error,

          'Unable to load responsible authorities.',

        ),

      );

    } finally {

      setLoadingAuthorities(false);

    }

  }, []);



  useEffect(() => {

    const timer = window.setTimeout(() => {

      void loadProjects();

    }, 250);



    return () => {

      window.clearTimeout(timer);

    };

  }, [loadProjects]);



  useEffect(() => {

    const timer = window.setTimeout(() => {

      void loadAuthorities();

    }, 0);



    return () => {

      window.clearTimeout(timer);

    };

  }, [loadAuthorities]);



  const resetForm = () => {

    setForm(EMPTY_FORM);

    setEditingProjectId(null);

    setFormError('');

  };



  const openCreateForm = () => {

    resetForm();

    setFormSuccess('');

    setShowForm(true);

  };



  const openEditForm = (project: Project) => {

    setForm({

      code: project.code,

      name: project.name,

      sector: project.sector,

      description: project.description ?? '',

      responsible_authority_id:

        project.responsible_authority_id,

    });



    setEditingProjectId(project.id);

    setFormError('');

    setFormSuccess('');

    setShowForm(true);

  };



  const handleFormSubmit = async (

    event: FormEvent<HTMLFormElement>,

  ) => {

    event.preventDefault();



    const validationError = validateForm(form);



    if (validationError) {

      setFormError(validationError);

      setFormSuccess('');

      return;

    }



    const authority = activeAuthorities.find(

      (item) =>

        item.id === form.responsible_authority_id,

    );



    if (!authority) {

      setFormError(

        'The selected authority is unavailable or inactive.',

      );

      setFormSuccess('');

      return;

    }



    setSavingForm(true);

    setFormError('');

    setFormSuccess('');



    try {

      const basePayload = {

        code: form.code.trim(),

        name: form.name.trim(),

        sector: form.sector.trim(),

        description: form.description.trim() || null,

        responsible_authority_id:

          form.responsible_authority_id,

      };



      if (editingProjectId) {

        const payload: UpdateProjectRequest = {

          ...basePayload,

        };



        const updatedProject = await updateProject(

          editingProjectId,

          payload,

        );



        setProjects((current) =>

          current.map((project) =>

            project.id === updatedProject.id

              ? updatedProject

              : project,

          ),

        );



        setSelectedProject(updatedProject);

        setSelectedProjectId(updatedProject.id);



        setFormSuccess(

          'Project changes saved successfully.',

        );

      } else {

        const payload: CreateProjectRequest = {

          ...basePayload,

        };



        const createdProject = await createProject(

          payload,

        );



        setProjects((current) => [

          createdProject,

          ...current,

        ]);



        setTotal((current) => current + 1);



        setSelectedProject(createdProject);

        setSelectedProjectId(createdProject.id);



        setFormSuccess(

          'Project created successfully.',

        );



        resetForm();

        setShowForm(false);

      }

    } catch (error) {

      setFormError(

        getErrorMessage(

          error,

          'Unable to save the project.',

        ),

      );

    } finally {

      setSavingForm(false);

    }

  };



  const handleSelectProject = async (

    projectId: string,

  ) => {

    setSelectedProjectId(projectId);

    setSelectedProject(null);

    setProjectsError('');



    try {

      const project = await getProject(projectId);

      setSelectedProject(project);

    } catch (error) {

      setProjectsError(

        getErrorMessage(

          error,

          'Unable to load project details.',

        ),

      );

    }

  };



  const handleActivateProject = async () => {

    if (!selectedProject) {

      return;

    }



    setChangingStatus(true);

    setFormError('');

    setFormSuccess('');



    try {

      const response = await activateProject(

        selectedProject.id,

      );



      const updatedProject: Project = {

        ...selectedProject,

        status: response.status,

      };



      setSelectedProject(updatedProject);



      setProjects((current) =>

        current.map((project) =>

          project.id === updatedProject.id

            ? updatedProject

            : project,

        ),

      );



      setFormSuccess(

        'Project activated successfully.',

      );

    } catch (error) {

      setFormError(

        getErrorMessage(

          error,

          'Unable to activate the project.',

        ),

      );

    } finally {

      setChangingStatus(false);

    }

  };



  const handleCloseProject = async () => {

    if (!selectedProject) {

      return;

    }



    setChangingStatus(true);

    setFormError('');

    setFormSuccess('');



    try {

      const response = await closeProject(

        selectedProject.id,

      );



      const updatedProject: Project = {

        ...selectedProject,

        status: response.status,

      };



      setSelectedProject(updatedProject);



      setProjects((current) =>

        current.map((project) =>

          project.id === updatedProject.id

            ? updatedProject

            : project,

        ),

      );



      setFormSuccess(

        'Project closed successfully.',

      );

    } catch (error) {

      setFormError(

        getErrorMessage(

          error,

          'Unable to close the project.',

        ),

      );

    } finally {

      setChangingStatus(false);

    }

  };



  const handleSearchChange = (value: string) => {

    setSearch(value);

    setOffset(0);

    setSelectedProjectId(null);

    setSelectedProject(null);

  };



  const handleStatusFilterChange = (

    value: 'all' | ProjectStatus,

  ) => {

    setStatusFilter(value);

    setOffset(0);

    setSelectedProjectId(null);

    setSelectedProject(null);

  };



  return (

    <section className="management-shell">

      <div className="management-heading">

        <div>

          <p className="roles-eyebrow">

            {t('project.title')}

          </p>



          <h1>{t('project.title')}</h1>



          <p>

            Create and manage infrastructure projects

            that drive the AAKAR land acquisition lifecycle.

          </p>

        </div>



        <div className="management-actions">

          <button

            type="button"

            className="primary-button"

            onClick={openCreateForm}

          >

            {t('project.create')}

          </button>

        </div>

      </div>



      {formSuccess && !showForm && (

        <div

          className="success-message"

          role="status"

        >

          {formSuccess}

        </div>

      )}



      {authoritiesError && (

        <div

          className="error-message"

          role="alert"

        >

          {authoritiesError}

        </div>

      )}



      {showForm && (

        <form

          className="management-form-card"

          onSubmit={handleFormSubmit}

        >

          <div className="management-card-heading">

            <div>

              <p className="roles-eyebrow">

                {editingProjectId ? t('project.edit') : t('project.new')}

              </p>



              <h2>

                {editingProjectId

                  ? t('project.edit')

                  : t('project.create')}

              </h2>

            </div>



            <button

              type="button"

              className="ghost-button"

              onClick={() => {

                setShowForm(false);

                resetForm();

              }}

              disabled={savingForm}

            >

              {t('project.close')}

            </button>

          </div>



          <div className="management-form-grid">

            <label>

              {t('project.code')}



              <input

                type="text"

                value={form.code}

                onChange={(event) =>

                  setForm((current) => ({

                    ...current,

                    code: event.target.value,

                  }))

                }

                maxLength={50}

                placeholder="e.g. NH-001"

                required

                disabled={savingForm}

              />

            </label>



            <label>

              {t('project.name')}



              <input

                type="text"

                value={form.name}

                onChange={(event) =>

                  setForm((current) => ({

                    ...current,

                    name: event.target.value,

                  }))

                }

                maxLength={200}

                placeholder="Enter project name"

                required

                disabled={savingForm}

              />

            </label>



            <label>

              {t('project.sector')}



              <input

                type="text"

                value={form.sector}

                onChange={(event) =>

                  setForm((current) => ({

                    ...current,

                    sector: event.target.value,

                  }))

                }

                maxLength={100}

                placeholder="e.g. Roads & Highways"

                required

                disabled={savingForm}

              />

            </label>



            <label>

              {t('project.responsibleAuthority')}



              <select

                value={form.responsible_authority_id}

                onChange={(event) =>

                  setForm((current) => ({

                    ...current,

                    responsible_authority_id:

                      event.target.value,

                  }))

                }

                required

                disabled={

                  savingForm ||

                  loadingAuthorities

                }

              >

                <option value="">

                  {loadingAuthorities

                    ? 'Loading authorities...'

                    : 'Select authority'}

                </option>



                {activeAuthorities.map(

                  (authority) => (

                    <option

                      key={authority.id}

                      value={authority.id}

                    >

                      {authority.code} —{' '}

                      {authority.name}

                    </option>

                  ),

                )}

              </select>

            </label>



            <label className="management-form-full">

              {t('project.description')}



              <textarea

                value={form.description}

                onChange={(event) =>

                  setForm((current) => ({

                    ...current,

                    description:

                      event.target.value,

                  }))

                }

                maxLength={5000}

                rows={5}

                placeholder="Describe the project purpose and scope."

                disabled={savingForm}

              />

            </label>

          </div>



          {formError && (

            <div

              className="error-message"

              role="alert"

            >

              {formError}

            </div>

          )}



          {formSuccess && (

            <div

              className="success-message"

              role="status"

            >

              {formSuccess}

            </div>

          )}



          <div className="management-form-actions">

            <button

              type="submit"

              className="primary-button"

              disabled={

                savingForm ||

                loadingAuthorities

              }

            >

              {savingForm

                ? t('project.saving')

                : editingProjectId

                  ? t('project.saveChanges')

                  : t('project.create')}

            </button>



            <button

              type="button"

              className="secondary-button"

              disabled={savingForm}

              onClick={() => {

                setShowForm(false);

                resetForm();

              }}

            >

              {t('project.cancel')}

            </button>

          </div>

        </form>

      )}



      <div className="management-layout">

        <section className="users-panel">

          <div className="users-toolbar">

            <div className="search-field">

              <label htmlFor="project-search">

                {t('project.search')}

              </label>



              <input

                id="project-search"

                type="search"

                placeholder="Search by code or name..."

                value={search}

                onChange={(event) =>

                  handleSearchChange(

                    event.target.value,

                  )

                }

              />

            </div>



            <div className="filter-field">

              <label htmlFor="project-status-filter">

                {t('project.status')}

              </label>



              <select

                id="project-status-filter"

                value={statusFilter}

                onChange={(event) =>

                  handleStatusFilterChange(

                    event.target.value as

                      | 'all'

                      | ProjectStatus,

                  )

                }

              >

                <option value="all">

                  {t('project.allProjects')}

                </option>



                {PROJECT_STATUSES.map(

                  (status) => (

                    <option

                      value={status}

                      key={status}

                    >

                      {formatStatus(status, t)}

                    </option>

                  ),

                )}

              </select>

            </div>

          </div>



          {projectsError && (

            <div

              className="error-message"

              role="alert"

            >

              {projectsError}

            </div>

          )}



          <div className="users-summary">

            <span>

              {total}{' '}

              {total === 1

                ? 'project'

                : 'projects'}

            </span>



            <span>

              Page {currentPage} of {totalPages}

            </span>

          </div>



          {loadingProjects ? (

            <div className="management-empty-state">

              <strong>

                {t('project.loading')}

              </strong>



              <p>

                Retrieving project records from the

                secure AAKAR API.

              </p>

            </div>

          ) : filteredProjects.length === 0 ? (

            <div className="management-empty-state">

              <strong>

                {t('project.noProjects')}

              </strong>



              <p>

                Try adjusting the search text or

                project status filter.

              </p>

            </div>

          ) : (

            <div className="user-list">

              {filteredProjects.map(

                (project) => (

                  <button

                    type="button"

                    key={project.id}

                    className={

                      project.id ===

                      selectedProjectId

                        ? 'user-list-item user-list-item-active'

                        : 'user-list-item'

                    }

                    onClick={() => {

                      void handleSelectProject(

                        project.id,

                      );

                    }}

                  >

                    <span className="user-list-main">

                      <strong>

                        {project.name}

                      </strong>



                      <span>

                        {project.code} ·{' '}

                        {project.sector}

                      </span>

                    </span>



                    <span

                      className={getStatusClass(

                        project.status,

                      )}

                    >

                      {formatStatus(project.status, t)}

                    </span>

                  </button>

                ),

              )}

            </div>

          )}



          <div className="pagination-controls">

            <button

              type="button"

              className="ghost-button"

              disabled={

                offset === 0 ||

                loadingProjects

              }

              onClick={() =>

                setOffset((currentOffset) =>

                  Math.max(

                    0,

                    currentOffset -

                      PAGE_SIZE,

                  ),

                )

              }

            >

              {t('project.previous')}

            </button>



            <span>

              {currentPage} / {totalPages}

            </span>



            <button

              type="button"

              className="ghost-button"

              disabled={

                offset + PAGE_SIZE >= total ||

                loadingProjects ||

                total === 0

              }

              onClick={() =>

                setOffset(

                  (currentOffset) =>

                    currentOffset +

                    PAGE_SIZE,

                )

              }

            >

              {t('project.next')}

            </button>

          </div>

        </section>



        <section className="detail-panel">

          {!selectedProject && (

            <div className="management-empty-state management-empty-state-large">

              <span className="detail-placeholder-icon">

                P

              </span>



              <strong>

                {t('project.selectProject')}

              </strong>



              <p>

                Choose a project to inspect its

                details, responsible authority,

                lifecycle status, and available

                actions.

              </p>

            </div>

          )}



          {selectedProject && (

            <div className="profile-card">

              <div className="management-card-heading">

                <div>

                  <p className="roles-eyebrow">

                    {t('project.details')}

                  </p>



                  <h2>

                    {selectedProject.name}

                  </h2>



                  <p>

                    {selectedProject.code}

                  </p>

                </div>



                <span

                  className={getStatusClass(

                    selectedProject.status,

                  )}

                >

                  {formatStatus(selectedProject.status, t)}

                </span>

              </div>



              <div className="profile-grid">

                <div className="profile-item">

                  <span>

                    {t('project.code')}

                  </span>



                  <strong>

                    {selectedProject.code}

                  </strong>

                </div>



                <div className="profile-item">

                  <span>

                    {t('project.sector')}

                  </span>



                  <strong>

                    {selectedProject.sector}

                  </strong>

                </div>



                <div className="profile-item">

                  <span>

                    {t('project.responsibleAuthority')}

                  </span>



                  <strong>

                    {getAuthorityName(

                      selectedProject.responsible_authority_id,

                    )}

                  </strong>

                </div>



                <div className="profile-item">

                  <span>

                    {t('project.lifecycleStatus')}

                  </span>



                  <strong>

                    {formatStatus(selectedProject.status, t)}

                  </strong>

                </div>



                <div className="profile-item">

                  <span>

                    {t('project.created')}

                  </span>



                  <strong>

                    {formatDateTime(

                      selectedProject.created_at,

                    )}

                  </strong>

                </div>



                <div className="profile-item">

                  <span>

                    {t('project.lastUpdated')}

                  </span>



                  <strong>

                    {formatDateTime(

                      selectedProject.updated_at,

                    )}

                  </strong>

                </div>

              </div>



              <div className="profile-description">

                <span>

                  {t('project.description')}

                </span>



                <p>

                  {selectedProject.description ||

                    t('project.noDescription')}

                </p>

              </div>



              <div className="profile-description">

                <span>

                  {t('project.spatialBoundary')}

                </span>



                <p>

                  {selectedProject.boundary

                    ? `Boundary available (${selectedProject.boundary.type}).`

                    : t('project.noSpatialBoundary')}

                </p>

              </div>



              {formError && (

                <div

                  className="error-message"

                  role="alert"

                >

                  {formError}

                </div>

              )}



              {formSuccess && (

                <div

                  className="success-message"

                  role="status"

                >

                  {formSuccess}

                </div>

              )}



              <div className="management-form-actions">

                <button

                  type="button"

                  className="secondary-button"

                  onClick={() =>

                    openEditForm(

                      selectedProject,

                    )

                  }

                  disabled={changingStatus}

                >

                  {t('project.edit')}

                </button>



                {selectedProject.status ===

                  'DRAFT' && (

                  <button

                    type="button"

                    className="primary-button"

                    onClick={() => {

                      void handleActivateProject();

                    }}

                    disabled={changingStatus}

                  >

                    {changingStatus

                      ? 'Processing...'

                      : t('project.activate')}

                  </button>

                )}



                {selectedProject.status ===

                  'ACTIVE' && (

                  <button

                    type="button"

                    className="secondary-button"

                    onClick={() => {

                      void handleCloseProject();

                    }}

                    disabled={changingStatus}

                  >

                    {changingStatus

                      ? 'Processing...'

                      : t('project.closeProject')}

                  </button>

                )}

              </div>

            </div>

          )}

        </section>

      </div>



      <div className="authorization-note">

        <span>{t('project.lifecycle')}</span>



        <p>

          Projects move through the controlled

          lifecycle: Draft → Active → Closed.

          Consequential lifecycle transitions are

          validated and authorized by the AAKAR

          backend.

        </p>

      </div>

    </section>

  );

}