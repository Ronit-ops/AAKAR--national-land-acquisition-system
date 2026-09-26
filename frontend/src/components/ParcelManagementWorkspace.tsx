import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  createParcel,
  getParcel,
  listParcels,
  updateParcel,
} from '../lib/api';

type Parcel = {
  id: string;
  parcel_reference: string;
  state: string;
  district: string;
  taluka: string | null;
  village: string | null;
  survey_number: string;
  subdivision_number: string | null;
  recorded_area_sq_m: string;
  surveyed_area_sq_m: string | null;
  acquired_area_sq_m: string | null;
  land_category: string | null;
  land_record_reference: string | null;
  source_system: string | null;
  geometry: unknown | null;
  created_at: string;
  updated_at: string;
};

type ParcelListResponse = {
  items: Parcel[];
  total: number;
  offset: number;
  limit: number;
};

type ParcelForm = {
  parcel_reference: string;
  state: string;
  district: string;
  taluka: string;
  village: string;
  survey_number: string;
  subdivision_number: string;
  recorded_area_sq_m: string;
  surveyed_area_sq_m: string;
  acquired_area_sq_m: string;
  land_category: string;
  land_record_reference: string;
  source_system: string;
};

type Props = {
  permissions: Set<string>;
};

const EMPTY_FORM: ParcelForm = {
  parcel_reference: '',
  state: '',
  district: '',
  taluka: '',
  village: '',
  survey_number: '',
  subdivision_number: '',
  recorded_area_sq_m: '',
  surveyed_area_sq_m: '',
  acquired_area_sq_m: '',
  land_category: '',
  land_record_reference: '',
  source_system: '',
};

const PAGE_SIZE = 20;

function formatArea(value: string | null): string {
  if (!value) {
    return '—';
  }

  const numeric = Number(value);

  if (!Number.isFinite(numeric)) {
    return value;
  }

  return `${numeric.toLocaleString(undefined, {
    maximumFractionDigits: 2,
  })} m²`;
}

function formatDate(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return 'Unavailable';
  }

  return date.toLocaleString();
}

function toPayload(form: ParcelForm) {
  return {
    parcel_reference: form.parcel_reference,
    state: form.state,
    district: form.district,
    taluka: form.taluka || null,
    village: form.village || null,
    survey_number: form.survey_number,
    subdivision_number: form.subdivision_number || null,
    recorded_area_sq_m: form.recorded_area_sq_m,
    surveyed_area_sq_m: form.surveyed_area_sq_m || null,
    acquired_area_sq_m: form.acquired_area_sq_m || null,
    land_category: form.land_category || null,
    land_record_reference: form.land_record_reference || null,
    source_system: form.source_system || null,
  };
}

function parcelToForm(parcel: Parcel): ParcelForm {
  return {
    parcel_reference: parcel.parcel_reference,
    state: parcel.state,
    district: parcel.district,
    taluka: parcel.taluka ?? '',
    village: parcel.village ?? '',
    survey_number: parcel.survey_number,
    subdivision_number: parcel.subdivision_number ?? '',
    recorded_area_sq_m: parcel.recorded_area_sq_m,
    surveyed_area_sq_m: parcel.surveyed_area_sq_m ?? '',
    acquired_area_sq_m: parcel.acquired_area_sq_m ?? '',
    land_category: parcel.land_category ?? '',
    land_record_reference: parcel.land_record_reference ?? '',
    source_system: parcel.source_system ?? '',
  };
}

export default function ParcelManagementWorkspace({
  permissions,
}: Props) {
  const canCreate = permissions.has('parcel.create');
  const canUpdate = permissions.has('parcel.update');

  const [parcels, setParcels] = useState<Parcel[]>([]);
  const [selectedParcelId, setSelectedParcelId] =
    useState<string | null>(null);
  const [selectedParcel, setSelectedParcel] =
    useState<Parcel | null>(null);

  const [search, setSearch] = useState('');
  const [stateFilter, setStateFilter] = useState('');
  const [districtFilter, setDistrictFilter] = useState('');

  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);

  const [loading, setLoading] = useState(true);
  const [loadingDetails, setLoadingDetails] = useState(false);

  const [error, setError] = useState('');
  const [detailsError, setDetailsError] = useState('');

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [form, setForm] = useState<ParcelForm>(EMPTY_FORM);

  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState('');

 

  const currentPage =
    Math.floor(offset / PAGE_SIZE) + 1;

  const totalPages = Math.max(
    1,
    Math.ceil(total / PAGE_SIZE),
  );

  const canGoPrevious = offset > 0 && !loading;

  const canGoNext =
    offset + PAGE_SIZE < total && !loading;

  const loadParcels = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const response: ParcelListResponse =
        await listParcels({
          search: search.trim() || undefined,
          state: stateFilter.trim() || undefined,
          district: districtFilter.trim() || undefined,
          offset,
          limit: PAGE_SIZE,
        });

      setParcels(response.items);
      setTotal(response.total);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to load parcels.',
      );
    } finally {
      setLoading(false);
    }
  }, [
    search,
    stateFilter,
    districtFilter,
    offset,
  ]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadParcels();
    }, 250);

    return () => {
      window.clearTimeout(timer);
    };
  }, [loadParcels]);

  const loadParcelDetails = async (parcelId: string) => {
    setSelectedParcelId(parcelId);
    setSelectedParcel(null);
    setDetailsError('');
    setSuccess('');
    setLoadingDetails(true);

    try {
      const parcel = await getParcel(parcelId);

      setSelectedParcel(parcel);
      setForm(parcelToForm(parcel));
      setShowCreateForm(false);
    } catch (requestError) {
      setDetailsError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to load parcel details.',
      );
    } finally {
      setLoadingDetails(false);
    }
  };

  const handleSearchChange = (value: string) => {
    setSearch(value);
    setOffset(0);
    setSelectedParcelId(null);
    setSelectedParcel(null);
    setDetailsError('');
    setSuccess('');
  };

  const handleStateChange = (value: string) => {
    setStateFilter(value);
    setOffset(0);
    setSelectedParcelId(null);
    setSelectedParcel(null);
  };

  const handleDistrictChange = (value: string) => {
    setDistrictFilter(value);
    setOffset(0);
    setSelectedParcelId(null);
    setSelectedParcel(null);
  };

  const handleCreate = () => {
    setSelectedParcelId(null);
    setSelectedParcel(null);
    setDetailsError('');
    setSuccess('');
    setForm(EMPTY_FORM);
    setShowCreateForm(true);
  };

  const handleCancelForm = () => {
    setShowCreateForm(false);
    setSelectedParcel(null);
    setSelectedParcelId(null);
    setDetailsError('');
    setForm(EMPTY_FORM);
  };

  const handleFormChange = (
    field: keyof ParcelForm,
    value: string,
  ) => {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  };

  const validateForm = (): string | null => {
    if (!form.parcel_reference.trim()) {
      return 'Parcel reference is required.';
    }

    if (!form.state.trim()) {
      return 'State is required.';
    }

    if (!form.district.trim()) {
      return 'District is required.';
    }

    if (!form.survey_number.trim()) {
      return 'Survey number is required.';
    }

    const recordedArea = Number(
      form.recorded_area_sq_m,
    );

    if (
      !Number.isFinite(recordedArea) ||
      recordedArea <= 0
    ) {
      return 'Recorded area must be greater than zero.';
    }

    if (form.surveyed_area_sq_m) {
      const surveyedArea = Number(
        form.surveyed_area_sq_m,
      );

      if (
        !Number.isFinite(surveyedArea) ||
        surveyedArea <= 0
      ) {
        return 'Surveyed area must be greater than zero.';
      }
    }

    if (form.acquired_area_sq_m) {
      const acquiredArea = Number(
        form.acquired_area_sq_m,
      );

      if (
        !Number.isFinite(acquiredArea) ||
        acquiredArea <= 0
      ) {
        return 'Acquired area must be greater than zero.';
      }
    }

    return null;
  };

  const handleSubmit = async (
    event: React.FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault();

    setError('');
    setDetailsError('');
    setSuccess('');

    const validationError = validateForm();

    if (validationError) {
      setDetailsError(validationError);
      return;
    }

    setSaving(true);

    try {
      const payload = toPayload(form);

      if (selectedParcel) {
        const updated = await updateParcel(
          selectedParcel.id,
          payload,
        );

        setSelectedParcel(updated);

        setParcels((current) =>
          current.map((parcel) =>
            parcel.id === updated.id
              ? updated
              : parcel,
          ),
        );

        setSuccess(
          'Parcel record updated successfully.',
        );
      } else {
        const created = await createParcel(payload);

        setSuccess(
          'Parcel record created successfully.',
        );

        setShowCreateForm(false);
        setForm(parcelToForm(created));

        await loadParcels();

        setSelectedParcelId(created.id);
        setSelectedParcel(created);
      }
    } catch (requestError) {
      setDetailsError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to save the parcel record.',
      );
    } finally {
      setSaving(false);
    }
  };

  const visibleParcelCount = useMemo(
    () => parcels.length,
    [parcels],
  );

  return (
    <section className="management-shell">
      <div className="management-heading">
        <div>
          <p className="roles-eyebrow">
            LAND & PARCEL REGISTRY
          </p>

          <h1>Parcel Management</h1>

          <p>
            Maintain the canonical parcel registry used
            across AAKAR land acquisition workflows.
          </p>
        </div>

        <div className="management-actions">
          {canCreate && (
            <button
              type="button"
              className="primary-button"
              onClick={handleCreate}
              disabled={saving}
            >
              + Register parcel
            </button>
          )}
        </div>
      </div>

      {success && (
        <div
          className="success-message"
          role="status"
        >
          {success}
        </div>
      )}

      {error && (
        <div
          className="error-message"
          role="alert"
        >
          {error}
        </div>
      )}

      {showCreateForm && (
        <form
          className="management-form-card"
          onSubmit={handleSubmit}
        >
          <div className="management-card-heading">
            <div>
              <p className="roles-eyebrow">
                NEW PARCEL
              </p>

              <h2>Register parcel</h2>
            </div>

            <button
              type="button"
              className="secondary-button"
              onClick={handleCancelForm}
              disabled={saving}
            >
              Cancel
            </button>
          </div>

          <ParcelFormFields
            form={form}
            onChange={handleFormChange}
          />

          {detailsError && (
            <div
              className="error-message"
              role="alert"
            >
              {detailsError}
            </div>
          )}

          <div className="management-form-actions">
            <button
              type="submit"
              className="primary-button"
              disabled={saving}
            >
              {saving
                ? 'Registering...'
                : 'Register parcel'}
            </button>
          </div>
        </form>
      )}

      <div className="management-layout">
        <section className="users-panel">
          <div className="users-toolbar">
            <div className="search-field">
              <label htmlFor="parcel-search">
                Search parcels
              </label>

              <input
                id="parcel-search"
                type="search"
                placeholder="Reference, survey number, village..."
                value={search}
                onChange={(event) =>
                  handleSearchChange(
                    event.target.value,
                  )
                }
              />
            </div>

            <div className="filter-field">
              <label htmlFor="parcel-state-filter">
                State
              </label>

              <input
                id="parcel-state-filter"
                type="text"
                placeholder="State"
                value={stateFilter}
                onChange={(event) =>
                  handleStateChange(
                    event.target.value,
                  )
                }
              />
            </div>

            <div className="filter-field">
              <label htmlFor="parcel-district-filter">
                District
              </label>

              <input
                id="parcel-district-filter"
                type="text"
                placeholder="District"
                value={districtFilter}
                onChange={(event) =>
                  handleDistrictChange(
                    event.target.value,
                  )
                }
              />
            </div>
          </div>

          <div className="users-summary">
            <span>
              {total}{' '}
              {total === 1 ? 'parcel' : 'parcels'}
            </span>

            <span>
              Showing {visibleParcelCount} · Page{' '}
              {currentPage} of {totalPages}
            </span>
          </div>

          {loading ? (
            <div className="management-empty-state">
              <strong>Loading parcels...</strong>

              <p>
                Retrieving parcel records from the
                secure AAKAR API.
              </p>
            </div>
          ) : parcels.length === 0 ? (
            <div className="management-empty-state">
              <strong>No parcels found</strong>

              <p>
                Try changing the search or location
                filters.
              </p>
            </div>
          ) : (
            <div className="user-list">
              {parcels.map((parcel) => {
                const isSelected =
                  parcel.id === selectedParcelId;

                return (
                  <button
                    type="button"
                    key={parcel.id}
                    className={
                      isSelected
                        ? 'user-list-item user-list-item-active'
                        : 'user-list-item'
                    }
                    onClick={() => {
                      void loadParcelDetails(
                        parcel.id,
                      );
                    }}
                  >
                    <div className="user-list-main">
                      <strong>
                        {parcel.parcel_reference}
                      </strong>

                      <span>
                        Survey No.{' '}
                        {parcel.survey_number}
                        {parcel.subdivision_number
                          ? ` / ${parcel.subdivision_number}`
                          : ''}
                      </span>
                    </div>

                    <div className="user-list-meta">
                      <span className="user-status user-status-active">
                        {parcel.village ||
                          parcel.district}
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
              disabled={!canGoPrevious}
              onClick={() =>
                setOffset((current) =>
                  Math.max(
                    0,
                    current - PAGE_SIZE,
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
              disabled={!canGoNext}
              onClick={() =>
                setOffset(
                  (current) =>
                    current + PAGE_SIZE,
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
                Loading parcel details...
              </strong>

              <p>
                Fetching the selected parcel record.
              </p>
            </div>
          )}

          {!loadingDetails &&
            detailsError &&
            !showCreateForm && (
              <div
                className="error-message"
                role="alert"
              >
                {detailsError}
              </div>
            )}

          {!loadingDetails &&
            !detailsError &&
            !selectedParcel &&
            !showCreateForm && (
              <div className="management-empty-state management-empty-state-large">
                <span className="detail-placeholder-icon">
                  ◈
                </span>

                <strong>
                  Select a parcel
                </strong>

                <p>
                  Choose a parcel from the registry
                  to inspect its location, survey
                  reference, area and land-record
                  information.
                </p>
              </div>
            )}

          {!loadingDetails &&
            selectedParcel &&
            !showCreateForm && (
              <div className="detail-card">
                <div className="detail-card-heading">
                  <div>
                    <p className="roles-eyebrow">
                      PARCEL RECORD
                    </p>

                    <h2>
                      {selectedParcel.parcel_reference}
                    </h2>

                    <span>
                      Survey No.{' '}
                      {selectedParcel.survey_number}
                      {selectedParcel.subdivision_number
                        ? ` / ${selectedParcel.subdivision_number}`
                        : ''}
                    </span>
                  </div>

                  {canUpdate && (
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={() => {
                        setShowCreateForm(true);
                        setDetailsError('');
                        setSuccess('');
                      }}
                    >
                      Edit parcel
                    </button>
                  )}
                </div>

                {success && (
                  <div
                    className="success-message"
                    role="status"
                  >
                    {success}
                  </div>
                )}

                <div className="account-meta-grid">
                  <div className="profile-item">
                    <span>State</span>
                    <strong>
                      {selectedParcel.state}
                    </strong>
                  </div>

                  <div className="profile-item">
                    <span>District</span>
                    <strong>
                      {selectedParcel.district}
                    </strong>
                  </div>

                  <div className="profile-item">
                    <span>Taluka</span>
                    <strong>
                      {selectedParcel.taluka || '—'}
                    </strong>
                  </div>

                  <div className="profile-item">
                    <span>Village</span>
                    <strong>
                      {selectedParcel.village || '—'}
                    </strong>
                  </div>

                  <div className="profile-item">
                    <span>Recorded area</span>
                    <strong>
                      {formatArea(
                        selectedParcel.recorded_area_sq_m,
                      )}
                    </strong>
                  </div>

                  <div className="profile-item">
                    <span>Surveyed area</span>
                    <strong>
                      {formatArea(
                        selectedParcel.surveyed_area_sq_m,
                      )}
                    </strong>
                  </div>

                  <div className="profile-item">
                    <span>Acquired area</span>
                    <strong>
                      {formatArea(
                        selectedParcel.acquired_area_sq_m,
                      )}
                    </strong>
                  </div>

                  <div className="profile-item">
                    <span>Land category</span>
                    <strong>
                      {selectedParcel.land_category ||
                        '—'}
                    </strong>
                  </div>

                  <div className="profile-item">
                    <span>Land record reference</span>
                    <strong>
                      {selectedParcel.land_record_reference ||
                        '—'}
                    </strong>
                  </div>

                  <div className="profile-item">
                    <span>Source system</span>
                    <strong>
                      {selectedParcel.source_system ||
                        '—'}
                    </strong>
                  </div>

                  <div className="profile-item">
                    <span>Created</span>
                    <strong>
                      {formatDate(
                        selectedParcel.created_at,
                      )}
                    </strong>
                  </div>

                  <div className="profile-item">
                    <span>Last updated</span>
                    <strong>
                      {formatDate(
                        selectedParcel.updated_at,
                      )}
                    </strong>
                  </div>
                </div>

                <div className="authorization-note">
                  <span>GIS</span>

                  <p>
                    Spatial geometry is part of the
                    canonical parcel record. Geometry
                    capture, validation and map
                    operations will be handled by the
                    dedicated GIS workflow.
                  </p>
                </div>
              </div>
            )}

          {!loadingDetails &&
            showCreateForm &&
            selectedParcel && (
              <form
                className="detail-card"
                onSubmit={handleSubmit}
              >
                <div className="detail-card-heading">
                  <div>
                    <p className="roles-eyebrow">
                      EDIT PARCEL
                    </p>

                    <h2>
                      {selectedParcel.parcel_reference}
                    </h2>
                  </div>

                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => {
                      setShowCreateForm(false);
                      setForm(
                        parcelToForm(selectedParcel),
                      );
                      setDetailsError('');
                    }}
                    disabled={saving}
                  >
                    Cancel
                  </button>
                </div>

                <ParcelFormFields
                  form={form}
                  onChange={handleFormChange}
                />

                {detailsError && (
                  <div
                    className="error-message"
                    role="alert"
                  >
                    {detailsError}
                  </div>
                )}

                <div className="detail-form-actions">
                  <button
                    type="submit"
                    className="primary-button"
                    disabled={saving}
                  >
                    {saving
                      ? 'Saving...'
                      : 'Save parcel changes'}
                  </button>
                </div>
              </form>
            )}
        </section>
      </div>
    </section>
  );
}

type ParcelFormFieldsProps = {
  form: ParcelForm;
  onChange: (
    field: keyof ParcelForm,
    value: string,
  ) => void;
};

function ParcelFormFields({
  form,
  onChange,
}: ParcelFormFieldsProps) {
  return (
    <div className="management-form-grid">
      <label>
        Parcel reference

        <input
          type="text"
          value={form.parcel_reference}
          onChange={(event) =>
            onChange(
              'parcel_reference',
              event.target.value,
            )
          }
          maxLength={100}
          required
        />
      </label>

      <label>
        State

        <input
          type="text"
          value={form.state}
          onChange={(event) =>
            onChange('state', event.target.value)
          }
          maxLength={100}
          required
        />
      </label>

      <label>
        District

        <input
          type="text"
          value={form.district}
          onChange={(event) =>
            onChange(
              'district',
              event.target.value,
            )
          }
          maxLength={100}
          required
        />
      </label>

      <label>
        Taluka

        <input
          type="text"
          value={form.taluka}
          onChange={(event) =>
            onChange(
              'taluka',
              event.target.value,
            )
          }
          maxLength={100}
        />
      </label>

      <label>
        Village

        <input
          type="text"
          value={form.village}
          onChange={(event) =>
            onChange(
              'village',
              event.target.value,
            )
          }
          maxLength={100}
        />
      </label>

      <label>
        Survey number

        <input
          type="text"
          value={form.survey_number}
          onChange={(event) =>
            onChange(
              'survey_number',
              event.target.value,
            )
          }
          maxLength={100}
          required
        />
      </label>

      <label>
        Subdivision number

        <input
          type="text"
          value={form.subdivision_number}
          onChange={(event) =>
            onChange(
              'subdivision_number',
              event.target.value,
            )
          }
          maxLength={100}
        />
      </label>

      <label>
        Recorded area (m²)

        <input
          type="number"
          min="0.0001"
          step="0.0001"
          value={form.recorded_area_sq_m}
          onChange={(event) =>
            onChange(
              'recorded_area_sq_m',
              event.target.value,
            )
          }
          required
        />
      </label>

      <label>
        Surveyed area (m²)

        <input
          type="number"
          min="0.0001"
          step="0.0001"
          value={form.surveyed_area_sq_m}
          onChange={(event) =>
            onChange(
              'surveyed_area_sq_m',
              event.target.value,
            )
          }
        />
      </label>

      <label>
        Acquired area (m²)

        <input
          type="number"
          min="0.0001"
          step="0.0001"
          value={form.acquired_area_sq_m}
          onChange={(event) =>
            onChange(
              'acquired_area_sq_m',
              event.target.value,
            )
          }
        />
      </label>

      <label>
        Land category

        <input
          type="text"
          value={form.land_category}
          onChange={(event) =>
            onChange(
              'land_category',
              event.target.value,
            )
          }
          maxLength={100}
        />
      </label>

      <label>
        Land record reference

        <input
          type="text"
          value={form.land_record_reference}
          onChange={(event) =>
            onChange(
              'land_record_reference',
              event.target.value,
            )
          }
          maxLength={150}
        />
      </label>

      <label>
        Source system

        <input
          type="text"
          value={form.source_system}
          onChange={(event) =>
            onChange(
              'source_system',
              event.target.value,
            )
          }
          maxLength={150}
        />
      </label>
    </div>
  );
}