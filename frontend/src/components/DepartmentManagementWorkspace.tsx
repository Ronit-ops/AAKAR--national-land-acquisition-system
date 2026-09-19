import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import {
  createDepartment,
  listDepartments,
  updateDepartment,
  updateDepartmentStatus,
} from '../lib/api';
import type {
  Department,
  UpdateDepartmentRequest,
} from '../types/organization';

type StatusFilter = 'all' | 'active' | 'inactive';

interface DepartmentFormState {
  code: string;
  name: string;
  description: string;
}

const PAGE_SIZE = 10;

const EMPTY_FORM: DepartmentFormState = {
  code: '',
  name: '',
  description: '',
};

function createFormFromDepartment(
  department: Department,
): DepartmentFormState {
  return {
    code: department.code,
    name: department.name,
    description: department.description ?? '',
  };
}

export default function DepartmentManagementWorkspace() {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [selectedDepartment, setSelectedDepartment] =
    useState<Department | null>(null);

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] =
    useState<StatusFilter>('all');

  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);

  const [loadingDepartments, setLoadingDepartments] = useState(true);
  const [departmentsError, setDepartmentsError] = useState('');

  const [showForm, setShowForm] = useState(false);
  const [editingDepartmentId, setEditingDepartmentId] =
    useState<string | null>(null);

  const [form, setForm] =
    useState<DepartmentFormState>(EMPTY_FORM);

  const [formError, setFormError] = useState('');
  const [formSuccess, setFormSuccess] = useState('');
  const [saving, setSaving] = useState(false);

  const [changingStatusId, setChangingStatusId] =
    useState<string | null>(null);

  const activeFilterValue =
    statusFilter === 'all'
      ? undefined
      : statusFilter === 'active';

  const currentPage =
    Math.floor(offset / PAGE_SIZE) + 1;

  const totalPages =
    Math.max(1, Math.ceil(total / PAGE_SIZE));

  const loadDepartments = useCallback(async () => {
    setLoadingDepartments(true);
    setDepartmentsError('');

    try {
      const response = await listDepartments({
        search: search.trim() || undefined,
        is_active: activeFilterValue,
        offset,
        limit: PAGE_SIZE,
      });

      setDepartments(response.items);
      setTotal(response.total);

      if (
        selectedDepartment &&
        !response.items.some(
          (department) =>
            department.id === selectedDepartment.id,
        )
      ) {
        setSelectedDepartment(null);
      }
    } catch (requestError) {
      setDepartmentsError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to load departments.',
      );
    } finally {
      setLoadingDepartments(false);
    }
  }, [
    activeFilterValue,
    offset,
    search,
    selectedDepartment,
  ]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadDepartments();
    }, 250);

    return () => {
      window.clearTimeout(timer);
    };
  }, [loadDepartments]);

  const resetForm = () => {
    setForm(EMPTY_FORM);
    setEditingDepartmentId(null);
    setFormError('');
  };

  const openCreateForm = () => {
    resetForm();
    setFormSuccess('');
    setShowForm(true);
  };

  const openEditForm = (department: Department) => {
    setEditingDepartmentId(department.id);
    setForm(createFormFromDepartment(department));
    setFormError('');
    setFormSuccess('');
    setShowForm(true);
  };

  const closeForm = () => {
    setShowForm(false);
    resetForm();
  };

  const handleSearchChange = (value: string) => {
    setSearch(value);
    setOffset(0);
    setSelectedDepartment(null);
  };

  const handleStatusFilterChange = (
    value: StatusFilter,
  ) => {
    setStatusFilter(value);
    setOffset(0);
    setSelectedDepartment(null);
  };

  const validateForm = (): string => {
    const code = form.code.trim();
    const name = form.name.trim();

    if (!code) {
      return 'Department code is required.';
    }

    if (code.length > 50) {
      return 'Department code cannot exceed 50 characters.';
    }

    if (!name) {
      return 'Department name is required.';
    }

    if (name.length > 200) {
      return 'Department name cannot exceed 200 characters.';
    }

    if (form.description.trim().length > 1000) {
      return 'Description cannot exceed 1000 characters.';
    }

    return '';
  };

  const handleSubmit = async (
    event: FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault();

    setFormError('');
    setFormSuccess('');

    const validationError = validateForm();

    if (validationError) {
      setFormError(validationError);
      return;
    }

    const payload: UpdateDepartmentRequest = {
      code: form.code.trim(),
      name: form.name.trim(),
      description: form.description.trim() || null,
    };

    setSaving(true);

    try {
      if (editingDepartmentId) {
        const updatedDepartment = await updateDepartment(
          editingDepartmentId,
          payload,
        );

        setDepartments((currentDepartments) =>
          currentDepartments.map((department) =>
            department.id === updatedDepartment.id
              ? updatedDepartment
              : department,
          ),
        );

        setSelectedDepartment(updatedDepartment);
        setFormSuccess(
          'Department updated successfully.',
        );
      } else {
        const createdDepartment =
          await createDepartment(payload);

        setFormSuccess(
          'Department created successfully.',
        );

        setOffset(0);
        setSelectedDepartment(createdDepartment);
      }

      resetForm();
      setShowForm(false);

      await loadDepartments();
    } catch (requestError) {
      setFormError(
        requestError instanceof Error
          ? requestError.message
          : editingDepartmentId
            ? 'Unable to update the department.'
            : 'Unable to create the department.',
      );
    } finally {
      setSaving(false);
    }
  };

  const handleStatusChange = async (
    department: Department,
  ) => {
    const nextStatus = !department.is_active;

    setChangingStatusId(department.id);
    setFormError('');
    setFormSuccess('');

    try {
      const updatedDepartment =
        await updateDepartmentStatus(
          department.id,
          {
            is_active: nextStatus,
          },
        );

      setDepartments((currentDepartments) =>
        currentDepartments.map((item) =>
          item.id === updatedDepartment.id
            ? updatedDepartment
            : item,
        ),
      );

      setSelectedDepartment(updatedDepartment);

      setFormSuccess(
        nextStatus
          ? 'Department activated successfully.'
          : 'Department deactivated successfully.',
      );

      await loadDepartments();
    } catch (requestError) {
      setFormError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to change department status.',
      );
    } finally {
      setChangingStatusId(null);
    }
  };

  return (
    <section className="management-shell">
      <div className="management-heading">
        <div>
          <p className="roles-eyebrow">
            ORGANIZATION & AUTHORITY
          </p>

          <h1>Department Management</h1>

          <p>
            Manage departments that form the organizational
            structure of the AAKAR platform.
          </p>
        </div>

        <div className="management-actions">
          <button
            type="button"
            className="primary-button"
            onClick={openCreateForm}
          >
            Create department
          </button>
        </div>
      </div>

      {formSuccess && (
        <div
          className="success-message"
          role="status"
        >
          {formSuccess}
        </div>
      )}

      {formError && !showForm && (
        <div
          className="error-message"
          role="alert"
        >
          {formError}
        </div>
      )}

      {showForm && (
        <form
          className="management-form-card"
          onSubmit={handleSubmit}
        >
          <div className="management-card-heading">
            <div>
              <p className="roles-eyebrow">
                {editingDepartmentId
                  ? 'EDIT DEPARTMENT'
                  : 'NEW DEPARTMENT'}
              </p>

              <h2>
                {editingDepartmentId
                  ? 'Update department'
                  : 'Create department'}
              </h2>
            </div>

            <button
              type="button"
              className="ghost-button"
              onClick={closeForm}
              disabled={saving}
            >
              Close
            </button>
          </div>

          <div className="management-form-grid">
            <label>
              Department code
              <input
                type="text"
                value={form.code}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    code: event.target.value,
                  }))
                }
                placeholder="e.g. LAND-ACQ"
                maxLength={50}
                required
              />
            </label>

            <label>
              Department name
              <input
                type="text"
                value={form.name}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    name: event.target.value,
                  }))
                }
                placeholder="Enter department name"
                maxLength={200}
                required
              />
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
                placeholder="Describe the department's purpose..."
                maxLength={1000}
                rows={4}
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

          <div className="management-form-actions">
            <button
              type="submit"
              className="primary-button"
              disabled={saving}
            >
              {saving
                ? editingDepartmentId
                  ? 'Saving changes...'
                  : 'Creating department...'
                : editingDepartmentId
                  ? 'Save changes'
                  : 'Create department'}
            </button>

            <button
              type="button"
              className="secondary-button"
              onClick={closeForm}
              disabled={saving}
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
              <label htmlFor="department-search">
                Search departments
              </label>

              <input
                id="department-search"
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
              <label htmlFor="department-status-filter">
                Status
              </label>

              <select
                id="department-status-filter"
                value={statusFilter}
                onChange={(event) =>
                  handleStatusFilterChange(
                    event.target.value as StatusFilter,
                  )
                }
              >
                <option value="all">
                  All departments
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

          {departmentsError && (
            <div
              className="error-message"
              role="alert"
            >
              {departmentsError}
            </div>
          )}

          <div className="users-summary">
            <span>
              {total}{' '}
              {total === 1
                ? 'department'
                : 'departments'}
            </span>

            <span>
              Page {currentPage} of {totalPages}
            </span>
          </div>

          {loadingDepartments ? (
            <div className="management-empty-state">
              <strong>
                Loading departments...
              </strong>

              <p>
                Retrieving organizational records from
                the secure AAKAR API.
              </p>
            </div>
          ) : departments.length === 0 ? (
            <div className="management-empty-state">
              <strong>
                No departments found
              </strong>

              <p>
                Try adjusting the search text or status
                filter, or create a new department.
              </p>
            </div>
          ) : (
            <div className="user-list">
              {departments.map((department) => {
                const isSelected =
                  selectedDepartment?.id ===
                  department.id;

                const changingStatus =
                  changingStatusId === department.id;

                return (
                  <button
                    type="button"
                    key={department.id}
                    className={
                      isSelected
                        ? 'user-list-item user-list-item-active'
                        : 'user-list-item'
                    }
                    onClick={() =>
                      setSelectedDepartment(
                        department,
                      )
                    }
                  >
                    <div className="user-list-main">
                      <strong>
                        {department.name}
                      </strong>

                      <span>
                        {department.code}
                      </span>
                    </div>

                    <div className="user-list-meta">
                      <span
                        className={
                          department.is_active
                            ? 'user-status user-status-active'
                            : 'user-status user-status-inactive'
                        }
                      >
                        {department.is_active
                          ? 'Active'
                          : 'Inactive'}
                      </span>

                      {changingStatus && (
                        <span className="current-user-badge">
                          Updating
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
                loadingDepartments
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
                loadingDepartments ||
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
          {!selectedDepartment ? (
            <div className="management-empty-state management-empty-state-large">
              <span className="detail-placeholder-icon">
                आ
              </span>

              <strong>
                Select a department
              </strong>

              <p>
                Choose a department from the list to
                inspect its organizational information
                and manage its status.
              </p>
            </div>
          ) : (
            <DepartmentDetailPanel
              department={selectedDepartment}
              changingStatus={
                changingStatusId ===
                selectedDepartment.id
              }
              onEdit={() =>
                openEditForm(selectedDepartment)
              }
              onStatusChange={() =>
                void handleStatusChange(
                  selectedDepartment,
                )
              }
            />
          )}
        </section>
      </div>
    </section>
  );
}

interface DepartmentDetailPanelProps {
  department: Department;
  changingStatus: boolean;
  onEdit: () => void;
  onStatusChange: () => void;
}

function DepartmentDetailPanel({
  department,
  changingStatus,
  onEdit,
  onStatusChange,
}: DepartmentDetailPanelProps) {
  return (
    <div className="detail-card">
      <div className="detail-card-heading">
        <div>
          <p className="roles-eyebrow">
            DEPARTMENT DETAILS
          </p>

          <h2>{department.name}</h2>

          <span>{department.code}</span>
        </div>

        <span
          className={
            department.is_active
              ? 'user-status user-status-active'
              : 'user-status user-status-inactive'
          }
        >
          {department.is_active
            ? 'Active'
            : 'Inactive'}
        </span>
      </div>

      <div className="detail-form-actions">
        <button
          type="button"
          className="primary-button"
          onClick={onEdit}
        >
          Edit department
        </button>

        <button
          type="button"
          className="secondary-button"
          disabled={changingStatus}
          onClick={onStatusChange}
        >
          {changingStatus
            ? 'Updating...'
            : department.is_active
              ? 'Deactivate department'
              : 'Activate department'}
        </button>
      </div>

      <div className="account-meta-grid">
        <div className="profile-item">
          <span>Department code</span>
          <strong>{department.code}</strong>
        </div>

        <div className="profile-item">
          <span>Status</span>
          <strong>
            {department.is_active
              ? 'Active'
              : 'Inactive'}
          </strong>
        </div>

        <div className="profile-item">
          <span>Created</span>
          <strong>
            {formatDateTime(
              department.created_at,
            )}
          </strong>
        </div>

        <div className="profile-item">
          <span>Updated</span>
          <strong>
            {formatDateTime(
              department.updated_at,
            )}
          </strong>
        </div>
      </div>

      <section className="assigned-role-panel">
        <div className="roles-heading">
          <div>
            <p className="roles-eyebrow">
              DESCRIPTION
            </p>

            <h3>Department purpose</h3>
          </div>
        </div>

        <p className="role-description">
          {department.description?.trim()
            ? department.description
            : 'No description has been provided for this department.'}
        </p>
      </section>

      <div className="authorization-note">
        <span>ORGANIZATION</span>

        <p>
          Departments are managed by authorized AAKAR
          system administrators and form the parent
          organizational level for authorities.
        </p>
      </div>
    </div>
  );
}

function formatDateTime(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return 'Unavailable';
  }

  return date.toLocaleString();
}