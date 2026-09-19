import { useCallback, useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import {
  createAuthority,
  getAuthority,
  listAuthorities,
  listDepartments,
  updateAuthority,
  updateAuthorityStatus,
} from '../lib/api';
import type {
  Authority,
  AuthorityType,
  Department,
} from '../types/organization';

const PAGE_SIZE = 10;

const AUTHORITY_TYPES: AuthorityType[] = [
  'CENTRAL',
  'STATE',
  'DISTRICT',
  'OTHER',
];

function formatAuthorityType(value: AuthorityType): string {
  return value.charAt(0) + value.slice(1).toLowerCase();
}

function formatDateTime(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return 'Unavailable';
  }

  return date.toLocaleString();
}

function getDepartmentName(
  departments: Department[],
  departmentId: string,
): string {
  return (
    departments.find((department) => department.id === departmentId)?.name ??
    'Unknown department'
  );
}

interface AuthorityFormValues {
  department_id: string;
  code: string;
  name: string;
  authority_type: AuthorityType;
  description: string;
}

const EMPTY_FORM: AuthorityFormValues = {
  department_id: '',
  code: '',
  name: '',
  authority_type: 'OTHER',
  description: '',
};

function validateForm(values: AuthorityFormValues): string {
  const code = values.code.trim();
  const name = values.name.trim();
  const description = values.description.trim();

  if (!values.department_id) {
    return 'Please select a department.';
  }

  if (!code) {
    return 'Authority code is required.';
  }

  if (code.length > 50) {
    return 'Authority code must be 50 characters or fewer.';
  }

  if (!name) {
    return 'Authority name is required.';
  }

  if (name.length > 200) {
    return 'Authority name must be 200 characters or fewer.';
  }

  if (!AUTHORITY_TYPES.includes(values.authority_type)) {
    return 'Please select a valid authority type.';
  }

  if (description.length > 1000) {
    return 'Description must be 1000 characters or fewer.';
  }

  return '';
}

export default function AuthorityManagementWorkspace() {
  const [authorities, setAuthorities] = useState<Authority[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);

  const [selectedAuthorityId, setSelectedAuthorityId] = useState<
    string | null
  >(null);
  const [selectedAuthority, setSelectedAuthority] =
    useState<Authority | null>(null);

  const [search, setSearch] = useState('');
  const [departmentFilter, setDepartmentFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [activeFilter, setActiveFilter] = useState<
    'all' | 'active' | 'inactive'
  >('all');

  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);

  const [loadingAuthorities, setLoadingAuthorities] = useState(true);
  const [loadingDepartments, setLoadingDepartments] = useState(true);
  const [authoritiesError, setAuthoritiesError] = useState('');
  const [departmentsError, setDepartmentsError] = useState('');

  const [showForm, setShowForm] = useState(false);
  const [editingAuthorityId, setEditingAuthorityId] = useState<string | null>(
    null,
  );

  const [form, setForm] = useState<AuthorityFormValues>(EMPTY_FORM);
  const [formError, setFormError] = useState('');
  const [formSuccess, setFormSuccess] = useState('');
  const [savingForm, setSavingForm] = useState(false);

  const [changingStatus, setChangingStatus] = useState(false);

  const activeFilterValue =
    activeFilter === 'all' ? undefined : activeFilter === 'active';

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  const activeDepartments = useMemo(
    () => departments.filter((department) => department.is_active),
    [departments],
  );

  const loadAuthorities = useCallback(async () => {
    setLoadingAuthorities(true);
    setAuthoritiesError('');

    try {
      const response = await listAuthorities({
        search: search.trim() || undefined,
        department_id: departmentFilter || undefined,
        authority_type: typeFilter || undefined,
        is_active: activeFilterValue,
        offset,
        limit: PAGE_SIZE,
      });

      setAuthorities(response.items);
      setTotal(response.total);

      if (
        selectedAuthorityId &&
        !response.items.some(
          (authority) => authority.id === selectedAuthorityId,
        )
      ) {
        setSelectedAuthorityId(null);
        setSelectedAuthority(null);
      }
    } catch (requestError) {
      setAuthoritiesError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to load authorities.',
      );
    } finally {
      setLoadingAuthorities(false);
    }
  }, [
    activeFilterValue,
    departmentFilter,
    offset,
    search,
    selectedAuthorityId,
    typeFilter,
  ]);

  useEffect(() => {
    let cancelled = false;

    const fetchDepartments = async () => {
      setLoadingDepartments(true);
      setDepartmentsError('');

      try {
        const response = await listDepartments({
          is_active: true,
          offset: 0,
          limit: 100,
        });

        if (!cancelled) {
          setDepartments(response.items);
        }
      } catch (requestError) {
        if (!cancelled) {
          setDepartmentsError(
            requestError instanceof Error
              ? requestError.message
              : 'Unable to load departments.',
          );
        }
      } finally {
        if (!cancelled) {
          setLoadingDepartments(false);
        }
      }
    };

    void fetchDepartments();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadAuthorities();
    }, 250);

    return () => {
      window.clearTimeout(timer);
    };
  }, [loadAuthorities]);

  const resetForm = () => {
    setForm(EMPTY_FORM);
    setEditingAuthorityId(null);
    setFormError('');
  };

  const openCreateForm = () => {
    resetForm();
    setFormSuccess('');
    setShowForm(true);
  };

  const openEditForm = (authority: Authority) => {
    setForm({
      department_id: authority.department_id,
      code: authority.code,
      name: authority.name,
      authority_type: authority.authority_type,
      description: authority.description ?? '',
    });

    setEditingAuthorityId(authority.id);
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

    const department = activeDepartments.find(
      (item) => item.id === form.department_id,
    );

    if (!department) {
      setFormError(
        'The selected department is unavailable or inactive.',
      );
      setFormSuccess('');
      return;
    }

    setSavingForm(true);
    setFormError('');
    setFormSuccess('');

    try {
      const payload = {
        department_id: form.department_id,
        code: form.code.trim(),
        name: form.name.trim(),
        authority_type: form.authority_type,
        description: form.description.trim() || null,
      };

      if (editingAuthorityId) {
        const updatedAuthority = await updateAuthority(
          editingAuthorityId,
          payload,
        );

        setAuthorities((current) =>
          current.map((authority) =>
            authority.id === updatedAuthority.id
              ? updatedAuthority
              : authority,
          ),
        );

        setSelectedAuthority(updatedAuthority);
        setSelectedAuthorityId(updatedAuthority.id);

        setFormSuccess('Changes saved successfully.');
      } else {
        const createdAuthority = await createAuthority(payload);

        setAuthorities((current) => [
          createdAuthority,
          ...current,
        ]);

        setTotal((current) => current + 1);
        setSelectedAuthority(createdAuthority);
        setSelectedAuthorityId(createdAuthority.id);

        setFormSuccess('Authority created successfully.');
        resetForm();
        setShowForm(false);
      }
    } catch (requestError) {
      setFormError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to save the authority.',
      );
    } finally {
      setSavingForm(false);
    }
  };

  const handleSelectAuthority = async (authorityId: string) => {
    setSelectedAuthorityId(authorityId);
    setSelectedAuthority(null);
    setAuthoritiesError('');

    try {
      const authority = await getAuthority(authorityId);
      setSelectedAuthority(authority);
    } catch (requestError) {
      setAuthoritiesError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to load authority details.',
      );
    }
  };

  const handleStatusChange = async () => {
    if (!selectedAuthority) {
      return;
    }

    const nextStatus = !selectedAuthority.is_active;

    setChangingStatus(true);
    setFormError('');
    setFormSuccess('');

    try {
      const updatedAuthority = await updateAuthorityStatus(
        selectedAuthority.id,
        {
          is_active: nextStatus,
        },
      );

      setSelectedAuthority(updatedAuthority);

      setAuthorities((current) =>
        current.map((authority) =>
          authority.id === updatedAuthority.id
            ? updatedAuthority
            : authority,
        ),
      );

      setFormSuccess(
        nextStatus
          ? 'Authority activated successfully.'
          : 'Authority deactivated successfully.',
      );
    } catch (requestError) {
      setFormError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to change authority status.',
      );
    } finally {
      setChangingStatus(false);
    }
  };

  const handleSearchChange = (value: string) => {
    setSearch(value);
    setOffset(0);
    setSelectedAuthorityId(null);
    setSelectedAuthority(null);
  };

  const handleDepartmentFilterChange = (value: string) => {
    setDepartmentFilter(value);
    setOffset(0);
    setSelectedAuthorityId(null);
    setSelectedAuthority(null);
  };

  const handleTypeFilterChange = (value: string) => {
    setTypeFilter(value);
    setOffset(0);
    setSelectedAuthorityId(null);
    setSelectedAuthority(null);
  };

  const handleActiveFilterChange = (
    value: 'all' | 'active' | 'inactive',
  ) => {
    setActiveFilter(value);
    setOffset(0);
    setSelectedAuthorityId(null);
    setSelectedAuthority(null);
  };

  return (
    <section className="management-shell">
      <div className="management-heading">
        <div>
          <p className="roles-eyebrow">ORGANIZATION & AUTHORITY</p>
          <h1>Authority Management</h1>
          <p>
            Manage authorities that operate within the AAKAR organizational
            structure.
          </p>
        </div>

        <div className="management-actions">
          <button
            type="button"
            className="primary-button"
            onClick={openCreateForm}
          >
            Create authority
          </button>
        </div>
      </div>

      {formSuccess && !showForm && (
        <div className="success-message" role="status">
          {formSuccess}
        </div>
      )}

      {departmentsError && (
        <div className="error-message" role="alert">
          {departmentsError}
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
                {editingAuthorityId
                  ? 'EDIT AUTHORITY'
                  : 'NEW AUTHORITY'}
              </p>
              <h2>
                {editingAuthorityId
                  ? 'Edit authority'
                  : 'Create authority'}
              </h2>
            </div>

            <button
              type="button"
              className="ghost-button"
              onClick={() => {
                setShowForm(false);
                resetForm();
              }}
            >
              Close
            </button>
          </div>

          <div className="management-form-grid">
            <label>
              Parent department
              <select
                value={form.department_id}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    department_id: event.target.value,
                  }))
                }
                disabled={loadingDepartments || savingForm}
                required
              >
                <option value="">
                  {loadingDepartments
                    ? 'Loading departments...'
                    : 'Select department'}
                </option>

                {activeDepartments.map((department) => (
                  <option
                    value={department.id}
                    key={department.id}
                  >
                    {department.code} — {department.name}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Authority code
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
                required
              />
            </label>

            <label>
              Authority name
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
                required
              />
            </label>

            <label>
              Authority type
              <select
                value={form.authority_type}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    authority_type: event.target.value as AuthorityType,
                  }))
                }
                required
              >
                {AUTHORITY_TYPES.map((authorityType) => (
                  <option
                    value={authorityType}
                    key={authorityType}
                  >
                    {formatAuthorityType(authorityType)}
                  </option>
                ))}
              </select>
            </label>

            <label className="management-form-full">
              Description
              <textarea
                value={form.description}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    description: event.target.value,
                  }))
                }
                maxLength={1000}
                rows={4}
              />
            </label>
          </div>

          {formError && (
            <div className="error-message" role="alert">
              {formError}
            </div>
          )}

          {formSuccess && (
            <div className="success-message" role="status">
              {formSuccess}
            </div>
          )}

          <div className="management-form-actions">
            <button
              type="submit"
              className="primary-button"
              disabled={savingForm || loadingDepartments}
            >
              {savingForm
                ? 'Saving...'
                : editingAuthorityId
                  ? 'Save changes'
                  : 'Create authority'}
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
              Cancel
            </button>
          </div>
        </form>
      )}

      <div className="management-layout">
        <section className="users-panel">
          <div className="users-toolbar">
            <div className="search-field">
              <label htmlFor="authority-search">
                Search authorities
              </label>

              <input
                id="authority-search"
                type="search"
                placeholder="Search by code or name..."
                value={search}
                onChange={(event) =>
                  handleSearchChange(event.target.value)
                }
              />
            </div>

            <div className="filter-field">
              <label htmlFor="authority-department-filter">
                Department
              </label>

              <select
                id="authority-department-filter"
                value={departmentFilter}
                onChange={(event) =>
                  handleDepartmentFilterChange(event.target.value)
                }
              >
                <option value="">All departments</option>

                {departments.map((department) => (
                  <option
                    value={department.id}
                    key={department.id}
                  >
                    {department.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="filter-field">
              <label htmlFor="authority-type-filter">Type</label>

              <select
                id="authority-type-filter"
                value={typeFilter}
                onChange={(event) =>
                  handleTypeFilterChange(event.target.value)
                }
              >
                <option value="">All types</option>

                {AUTHORITY_TYPES.map((authorityType) => (
                  <option
                    value={authorityType}
                    key={authorityType}
                  >
                    {formatAuthorityType(authorityType)}
                  </option>
                ))}
              </select>
            </div>

            <div className="filter-field">
              <label htmlFor="authority-status-filter">Status</label>

              <select
                id="authority-status-filter"
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
                <option value="all">All authorities</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
          </div>

          {authoritiesError && (
            <div className="error-message" role="alert">
              {authoritiesError}
            </div>
          )}

          <div className="users-summary">
            <span>
              {total} {total === 1 ? 'authority' : 'authorities'}
            </span>

            <span>
              Page {currentPage} of {totalPages}
            </span>
          </div>

          {loadingAuthorities ? (
            <div className="management-empty-state">
              <strong>Loading authorities...</strong>
              <p>
                Retrieving authority records from the secure AAKAR API.
              </p>
            </div>
          ) : authorities.length === 0 ? (
            <div className="management-empty-state">
              <strong>No authorities found</strong>
              <p>
                Try adjusting the search text or authority filters.
              </p>
            </div>
          ) : (
            <div className="user-list">
              {authorities.map((authority) => (
                <button
                  type="button"
                  key={authority.id}
                  className={
                    authority.id === selectedAuthorityId
                      ? 'user-list-item user-list-item-active'
                      : 'user-list-item'
                  }
                  onClick={() => {
                    void handleSelectAuthority(authority.id);
                  }}
                >
                  <div className="user-list-main">
                    <strong>{authority.name}</strong>
                    <span>
                      {authority.code} ·{' '}
                      {getDepartmentName(
                        departments,
                        authority.department_id,
                      )}
                    </span>
                  </div>

                  <div className="user-list-meta">
                    <span className="scope-badge">
                      {formatAuthorityType(
                        authority.authority_type,
                      )}
                    </span>

                    <span
                      className={
                        authority.is_active
                          ? 'user-status user-status-active'
                          : 'user-status user-status-inactive'
                      }
                    >
                      {authority.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}

          <div className="pagination-controls">
            <button
              type="button"
              className="ghost-button"
              disabled={offset === 0 || loadingAuthorities}
              onClick={() =>
                setOffset((currentOffset) =>
                  Math.max(0, currentOffset - PAGE_SIZE),
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
                loadingAuthorities ||
                total === 0
              }
              onClick={() =>
                setOffset((currentOffset) =>
                  currentOffset + PAGE_SIZE,
                )
              }
            >
              Next
            </button>
          </div>
        </section>

        <section className="user-detail-panel">
          {!selectedAuthority && (
            <div className="management-empty-state management-empty-state-large">
              <span className="detail-placeholder-icon">आ</span>

              <strong>Select an authority</strong>

              <p>
                Choose an authority from the list to inspect its
                department, type, status, and description.
              </p>
            </div>
          )}

          {selectedAuthority && (
            <div className="detail-card">
              <div className="detail-card-heading">
                <div>
                  <p className="roles-eyebrow">AUTHORITY DETAILS</p>
                  <h2>{selectedAuthority.name}</h2>
                  <span>{selectedAuthority.code}</span>
                </div>

                <span
                  className={
                    selectedAuthority.is_active
                      ? 'user-status user-status-active'
                      : 'user-status user-status-inactive'
                  }
                >
                  {selectedAuthority.is_active
                    ? 'Active'
                    : 'Inactive'}
                </span>
              </div>

              {formError && !showForm && (
                <div className="error-message" role="alert">
                  {formError}
                </div>
              )}

              {formSuccess && !showForm && (
                <div className="success-message" role="status">
                  {formSuccess}
                </div>
              )}

              <div className="management-form-actions">
                <button
                  type="button"
                  className="primary-button"
                  onClick={() => openEditForm(selectedAuthority)}
                >
                  Edit authority
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
                    : selectedAuthority.is_active
                      ? 'Deactivate authority'
                      : 'Activate authority'}
                </button>
              </div>

              <div className="profile-grid">
                <div className="profile-item">
                  <span>Authority code</span>
                  <strong>{selectedAuthority.code}</strong>
                </div>

                <div className="profile-item">
                  <span>Authority type</span>
                  <strong>
                    {formatAuthorityType(
                      selectedAuthority.authority_type,
                    )}
                  </strong>
                </div>

                <div className="profile-item">
                  <span>Parent department</span>
                  <strong>
                    {getDepartmentName(
                      departments,
                      selectedAuthority.department_id,
                    )}
                  </strong>
                </div>

                <div className="profile-item">
                  <span>Status</span>
                  <strong>
                    {selectedAuthority.is_active
                      ? 'Active'
                      : 'Inactive'}
                  </strong>
                </div>

                <div className="profile-item">
                  <span>Created</span>
                  <strong>
                    {formatDateTime(selectedAuthority.created_at)}
                  </strong>
                </div>

                <div className="profile-item">
                  <span>Updated</span>
                  <strong>
                    {formatDateTime(selectedAuthority.updated_at)}
                  </strong>
                </div>
              </div>

              <div className="authorization-note">
                <span>ORGANIZATION</span>

                <p>
                  Authorities must belong to an active department.
                  Organizational relationships are enforced by the
                  AAKAR backend.
                </p>
              </div>

              <div className="authorization-note">
                <span>DESCRIPTION</span>

                <p>
                  {selectedAuthority.description ||
                    'No description provided.'}
                </p>
              </div>
            </div>
          )}
        </section>
      </div>
    </section>
  );
}