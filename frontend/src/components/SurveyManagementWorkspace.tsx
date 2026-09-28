import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react';

import {
  cancelSurvey,
  completeSurvey,
  createSurvey,
  getSurvey,
  listSurveys,
  reviewSurvey,
  startSurvey,
  verifySurvey,
} from '../lib/api';

import {
  SURVEY_METHODS,
  SURVEY_STATUSES,
  SURVEY_TYPES,
  type SurveyMethod,
  type SurveyRecord,
  type SurveyStatus,
  type SurveyType,
} from '../types/surveys';

const PAGE_SIZE = 10;

type FormState = {
  acquisition_case_id: string;
  parcel_id: string;
  survey_reference: string;
  survey_type: SurveyType;
  survey_method: SurveyMethod;
  scheduled_at: string;
  surveyor_user_id: string;
  recorded_area_sq_m: string;
  notes: string;
};

const INITIAL_FORM: FormState = {
  acquisition_case_id: '',
  parcel_id: '',
  survey_reference: '',
  survey_type: 'PRELIMINARY',
  survey_method: 'FIELD_SURVEY',
  scheduled_at: '',
  surveyor_user_id: '',
  recorded_area_sq_m: '',
  notes: '',
};

function formatLabel(value: string): string {
  return value
    .toLowerCase()
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (character) =>
      character.toUpperCase(),
    );
}

function formatDateTime(
  value: string | null,
): string {
  if (!value) {
    return '—';
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function formatNumber(
  value: string | null,
): string {
  if (value === null || value === '') {
    return '—';
  }

  const number = Number(value);

  if (Number.isNaN(number)) {
    return value;
  }

  return number.toLocaleString(undefined, {
    maximumFractionDigits: 4,
  });
}

function statusClass(
  status: string,
): string {
  switch (status) {
    case 'PLANNED':
      return 'survey-status survey-status--planned';

    case 'IN_PROGRESS':
      return 'survey-status survey-status--progress';

    case 'COMPLETED':
      return 'survey-status survey-status--completed';

    case 'REQUIRES_REVIEW':
      return 'survey-status survey-status--review';

    case 'VERIFIED':
      return 'survey-status survey-status--verified';

    case 'CANCELLED':
      return 'survey-status survey-status--cancelled';

    default:
      return 'survey-status';
  }
}

function canStart(
  status: SurveyStatus | string,
): boolean {
  return status === 'PLANNED';
}

function canComplete(
  status: SurveyStatus | string,
): boolean {
  return status === 'IN_PROGRESS';
}

function canReview(
  status: SurveyStatus | string,
): boolean {
  return status === 'COMPLETED';
}

function canVerify(
  status: SurveyStatus | string,
): boolean {
  return status === 'REQUIRES_REVIEW';
}

function canCancel(
  status: SurveyStatus | string,
): boolean {
  return (
    status === 'PLANNED' ||
    status === 'IN_PROGRESS'
  );
}

export default function SurveyManagementWorkspace() {
  const [surveys, setSurveys] = useState<
    SurveyRecord[]
  >([]);

  const [selectedSurvey, setSelectedSurvey] =
    useState<SurveyRecord | null>(null);

  const [form, setForm] =
    useState<FormState>(INITIAL_FORM);

  const [statusFilter, setStatusFilter] =
    useState('');

  const [caseFilter, setCaseFilter] =
    useState('');

  const [parcelFilter, setParcelFilter] =
    useState('');

  const [offset, setOffset] =
    useState(0);

  const [total, setTotal] =
    useState(0);

  const [loading, setLoading] =
    useState(false);

  const [saving, setSaving] =
    useState(false);

  const [detailLoading, setDetailLoading] =
    useState(false);

  const [actionLoading, setActionLoading] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);

  const [successMessage, setSuccessMessage] =
    useState<string | null>(null);

  const [showCreateForm, setShowCreateForm] =
    useState(false);

  const [measuredArea, setMeasuredArea] =
    useState('');

  const [conductedAt, setConductedAt] =
    useState('');

  const loadSurveys = useCallback(
    async () => {
      setLoading(true);
      setError(null);

      try {
        const response =
          await listSurveys({
            acquisition_case_id:
              caseFilter || undefined,
            parcel_id:
              parcelFilter || undefined,
            status:
              statusFilter || undefined,
            offset,
            limit: PAGE_SIZE,
          });

        setSurveys(response.items);
        setTotal(response.total);
      } catch (requestError) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : 'Unable to load surveys.',
        );
      } finally {
        setLoading(false);
      }
    },
    [
      caseFilter,
      parcelFilter,
      statusFilter,
      offset,
    ],
  );

  useEffect(() => {
    void loadSurveys();
  }, [loadSurveys]);

  const refreshSelectedSurvey =
    useCallback(
      async (
        surveyId: string,
      ) => {
        setDetailLoading(true);

        try {
          const survey =
            await getSurvey(surveyId);

          setSelectedSurvey(survey);
          setSurveys((current) =>
            current.map((item) =>
              item.id === survey.id
                ? survey
                : item,
            ),
          );
        } catch (requestError) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : 'Unable to load survey details.',
          );
        } finally {
          setDetailLoading(false);
        }
      },
      [],
    );

  const handleCreate = async (
    event: React.FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault();

    setSaving(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const payload = {
        acquisition_case_id:
          form.acquisition_case_id.trim(),
        parcel_id:
          form.parcel_id.trim(),
        survey_reference:
          form.survey_reference.trim(),
        survey_type:
          form.survey_type,
        survey_method:
          form.survey_method,
        scheduled_at:
          form.scheduled_at
            ? new Date(
                form.scheduled_at,
              ).toISOString()
            : null,
        surveyor_user_id:
          form.surveyor_user_id.trim() || null,
        recorded_area_sq_m:
          form.recorded_area_sq_m.trim(),
        notes:
          form.notes.trim() || null,
      };

      if (
        !payload.acquisition_case_id ||
        !payload.parcel_id ||
        !payload.survey_reference ||
        !payload.recorded_area_sq_m
      ) {
        setError(
          'Case ID, parcel ID, survey reference and recorded area are required.',
        );
        return;
      }

      const created =
        await createSurvey(payload);

      setForm(INITIAL_FORM);
      setShowCreateForm(false);
      setSuccessMessage(
        'Survey record created successfully.',
      );

      setSelectedSurvey(created);

      await loadSurveys();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to create survey.',
      );
    } finally {
      setSaving(false);
    }
  };

  const executeAction = async (
    action: (
      surveyId: string,
    ) => Promise<SurveyRecord>,
    successText: string,
  ) => {
    if (!selectedSurvey) {
      return;
    }

    setActionLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const updated =
        await action(
          selectedSurvey.id,
        );

      setSelectedSurvey(updated);

      setSurveys((current) =>
        current.map((item) =>
          item.id === updated.id
            ? updated
            : item,
        ),
      );

      setSuccessMessage(successText);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to perform survey action.',
      );
    } finally {
      setActionLoading(false);
    }
  };

  const handleComplete =
    async () => {
      if (!selectedSurvey) {
        return;
      }

      if (!measuredArea.trim()) {
        setError(
          'Measured area is required to complete the survey.',
        );
        return;
      }

      setActionLoading(true);
      setError(null);
      setSuccessMessage(null);

      try {
        const payload = {
          measured_area_sq_m:
            measuredArea.trim(),
          conducted_at:
            conductedAt
              ? new Date(
                  conductedAt,
                ).toISOString()
              : null,
        };

        const updated =
          await completeSurvey(
            selectedSurvey.id,
            payload,
          );

        setSelectedSurvey(updated);

        setSurveys((current) =>
          current.map((item) =>
            item.id === updated.id
              ? updated
              : item,
          ),
        );

        setMeasuredArea('');
        setConductedAt('');

        setSuccessMessage(
          'Survey completed successfully.',
        );
      } catch (requestError) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : 'Unable to complete survey.',
        );
      } finally {
        setActionLoading(false);
      }
    };

  const handleSelectSurvey =
    async (survey: SurveyRecord) => {
      setSelectedSurvey(survey);
      setError(null);
      setSuccessMessage(null);

      await refreshSelectedSurvey(
        survey.id,
      );
    };

  const totalPages =
    Math.max(
      1,
      Math.ceil(
        total / PAGE_SIZE,
      ),
    );

  const currentPage =
    Math.floor(
      offset / PAGE_SIZE,
    ) + 1;

  const hasPreviousPage =
    offset > 0;

  const hasNextPage =
    offset + PAGE_SIZE < total;

  const areaDifferenceText =
    useMemo(() => {
      if (
        !selectedSurvey ||
        selectedSurvey.area_difference_sq_m ===
          null
      ) {
        return '—';
      }

      return `${formatNumber(
        selectedSurvey.area_difference_sq_m,
      )} sq m`;
    }, [selectedSurvey]);

  const areaDifferencePercentageText =
    useMemo(() => {
      if (
        !selectedSurvey ||
        selectedSurvey.area_difference_percentage ===
          null
      ) {
        return '—';
      }

      return `${formatNumber(
        selectedSurvey.area_difference_percentage,
      )}%`;
    }, [selectedSurvey]);

  return (
    <section className="survey-workspace">
      <style>
        {`
          .survey-workspace {
            display: flex;
            flex-direction: column;
            gap: 20px;
            padding: 24px;
            min-height: 100%;
            background: #f7f8fa;
          }

          .survey-workspace__header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 20px;
            padding: 24px;
            border: 1px solid #e5e7eb;
            border-radius: 14px;
            background: #ffffff;
          }

          .survey-workspace__eyebrow {
            margin: 0 0 6px;
            color: #64748b;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
          }

          .survey-workspace__title {
            margin: 0;
            color: #172033;
            font-size: 24px;
            line-height: 1.2;
          }

          .survey-workspace__description {
            max-width: 760px;
            margin: 8px 0 0;
            color: #64748b;
            font-size: 14px;
            line-height: 1.6;
          }

          .survey-button {
            border: 0;
            border-radius: 8px;
            padding: 10px 15px;
            font-size: 13px;
            font-weight: 700;
            cursor: pointer;
            transition:
              transform 120ms ease,
              opacity 120ms ease;
          }

          .survey-button:hover:not(:disabled) {
            transform: translateY(-1px);
          }

          .survey-button:disabled {
            cursor: not-allowed;
            opacity: 0.55;
          }

          .survey-button--primary {
            color: #ffffff;
            background: #1f5f46;
          }

          .survey-button--secondary {
            color: #334155;
            background: #e2e8f0;
          }

          .survey-button--danger {
            color: #ffffff;
            background: #b42318;
          }

          .survey-button--success {
            color: #ffffff;
            background: #16794a;
          }

          .survey-button--warning {
            color: #ffffff;
            background: #a15c00;
          }

          .survey-alert {
            padding: 12px 15px;
            border-radius: 9px;
            font-size: 13px;
            line-height: 1.5;
          }

          .survey-alert--error {
            color: #8b1e1e;
            border: 1px solid #fecaca;
            background: #fef2f2;
          }

          .survey-alert--success {
            color: #166534;
            border: 1px solid #bbf7d0;
            background: #f0fdf4;
          }

          .survey-toolbar {
            display: grid;
            grid-template-columns:
              minmax(180px, 1fr)
              minmax(180px, 1fr)
              minmax(180px, 1fr)
              auto;
            gap: 12px;
            align-items: end;
            padding: 18px;
            border: 1px solid #e5e7eb;
            border-radius: 14px;
            background: #ffffff;
          }

          .survey-field {
            display: flex;
            flex-direction: column;
            gap: 6px;
          }

          .survey-field label {
            color: #475569;
            font-size: 12px;
            font-weight: 700;
          }

          .survey-field input,
          .survey-field select,
          .survey-field textarea {
            width: 100%;
            box-sizing: border-box;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            padding: 9px 10px;
            color: #172033;
            background: #ffffff;
            font: inherit;
            font-size: 13px;
            outline: none;
          }

          .survey-field textarea {
            min-height: 90px;
            resize: vertical;
          }

          .survey-field input:focus,
          .survey-field select:focus,
          .survey-field textarea:focus {
            border-color: #1f5f46;
            box-shadow:
              0 0 0 2px
              rgba(31, 95, 70, 0.1);
          }

          .survey-layout {
            display: grid;
            grid-template-columns:
              minmax(0, 1.35fr)
              minmax(360px, 0.85fr);
            gap: 20px;
            align-items: start;
          }

          .survey-panel {
            min-width: 0;
            overflow: hidden;
            border: 1px solid #e5e7eb;
            border-radius: 14px;
            background: #ffffff;
          }

          .survey-panel__header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            padding: 16px 18px;
            border-bottom: 1px solid #e5e7eb;
          }

          .survey-panel__title {
            margin: 0;
            color: #172033;
            font-size: 15px;
          }

          .survey-panel__meta {
            color: #64748b;
            font-size: 12px;
          }

          .survey-table-wrapper {
            overflow-x: auto;
          }

          .survey-table {
            width: 100%;
            border-collapse: collapse;
            min-width: 760px;
          }

          .survey-table th {
            padding: 11px 13px;
            color: #64748b;
            background: #f8fafc;
            border-bottom: 1px solid #e5e7eb;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.04em;
            text-align: left;
            text-transform: uppercase;
          }

          .survey-table td {
            padding: 13px;
            color: #334155;
            border-bottom: 1px solid #eef2f7;
            font-size: 13px;
            vertical-align: middle;
          }

          .survey-table tbody tr {
            cursor: pointer;
          }

          .survey-table tbody tr:hover {
            background: #f8fafc;
          }

          .survey-table tbody tr.selected {
            background: #f0fdf4;
          }

          .survey-reference {
            color: #172033;
            font-weight: 750;
          }

          .survey-subtext {
            margin-top: 3px;
            color: #94a3b8;
            font-size: 11px;
          }

          .survey-status {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 4px 8px;
            color: #475569;
            background: #e2e8f0;
            font-size: 11px;
            font-weight: 800;
            white-space: nowrap;
          }

          .survey-status--planned {
            color: #475569;
            background: #e2e8f0;
          }

          .survey-status--progress {
            color: #075985;
            background: #e0f2fe;
          }

          .survey-status--completed {
            color: #166534;
            background: #dcfce7;
          }

          .survey-status--review {
            color: #854d0e;
            background: #fef9c3;
          }

          .survey-status--verified {
            color: #166534;
            background: #bbf7d0;
          }

          .survey-status--cancelled {
            color: #991b1b;
            background: #fee2e2;
          }

          .survey-empty {
            padding: 44px 20px;
            color: #64748b;
            text-align: center;
            font-size: 13px;
          }

          .survey-pagination {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            padding: 14px 18px;
            border-top: 1px solid #e5e7eb;
          }

          .survey-pagination__info {
            color: #64748b;
            font-size: 12px;
          }

          .survey-pagination__actions {
            display: flex;
            gap: 8px;
          }

          .survey-detail {
            padding: 18px;
          }

          .survey-detail__reference {
            margin: 0;
            color: #172033;
            font-size: 20px;
          }

          .survey-detail__status {
            margin-top: 8px;
          }

          .survey-detail__grid {
            display: grid;
            grid-template-columns:
              repeat(2, minmax(0, 1fr));
            gap: 14px;
            margin-top: 20px;
          }

          .survey-detail__item {
            padding: 12px;
            border: 1px solid #eef2f7;
            border-radius: 9px;
            background: #f8fafc;
          }

          .survey-detail__label {
            color: #64748b;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.04em;
          }

          .survey-detail__value {
            margin-top: 5px;
            color: #172033;
            font-size: 13px;
            font-weight: 650;
            overflow-wrap: anywhere;
          }

          .survey-detail__section {
            margin-top: 20px;
            padding-top: 18px;
            border-top: 1px solid #e5e7eb;
          }

          .survey-detail__section-title {
            margin: 0 0 12px;
            color: #334155;
            font-size: 13px;
            font-weight: 800;
          }

          .survey-actions {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
          }

          .survey-create {
            padding: 20px;
            border-top: 1px solid #e5e7eb;
          }

          .survey-create__grid {
            display: grid;
            grid-template-columns:
              repeat(2, minmax(0, 1fr));
            gap: 14px;
          }

          .survey-create__full {
            grid-column: 1 / -1;
          }

          .survey-form-actions {
            display: flex;
            justify-content: flex-end;
            gap: 8px;
            margin-top: 16px;
          }

          .survey-loading {
            padding: 28px;
            color: #64748b;
            text-align: center;
            font-size: 13px;
          }

          .survey-muted {
            color: #94a3b8;
          }

          @media (max-width: 1100px) {
            .survey-layout {
              grid-template-columns: 1fr;
            }

            .survey-toolbar {
              grid-template-columns:
                repeat(2, minmax(0, 1fr));
            }
          }

          @media (max-width: 720px) {
            .survey-workspace {
              padding: 14px;
            }

            .survey-workspace__header {
              flex-direction: column;
            }

            .survey-toolbar {
              grid-template-columns: 1fr;
            }

            .survey-detail__grid,
            .survey-create__grid {
              grid-template-columns: 1fr;
            }

            .survey-create__full {
              grid-column: auto;
            }

            .survey-pagination {
              flex-direction: column;
              align-items: stretch;
            }

            .survey-pagination__actions {
              justify-content: stretch;
            }

            .survey-pagination__actions .survey-button {
              flex: 1;
            }
          }
        `}
      </style>

      <header className="survey-workspace__header">
        <div>
          <p className="survey-workspace__eyebrow">
            AA-006 · Land Acquisition
          </p>

          <h1 className="survey-workspace__title">
            Survey & Measurement
          </h1>

          <p className="survey-workspace__description">
            Manage field surveys, measurements,
            review workflow and verification for
            acquisition-linked parcels.
          </p>
        </div>

        <button
          type="button"
          className="survey-button survey-button--primary"
          onClick={() => {
            setShowCreateForm(
              (current) => !current,
            );
            setError(null);
            setSuccessMessage(null);
          }}
        >
          {showCreateForm
            ? 'Close Form'
            : 'New Survey'}
        </button>
      </header>

      {error && (
        <div className="survey-alert survey-alert--error">
          {error}
        </div>
      )}

      {successMessage && (
        <div className="survey-alert survey-alert--success">
          {successMessage}
        </div>
      )}

      {showCreateForm && (
        <form
          className="survey-panel survey-create"
          onSubmit={handleCreate}
        >
          <div className="survey-panel__header">
            <div>
              <h2 className="survey-panel__title">
                Create Survey Record
              </h2>

              <span className="survey-panel__meta">
                A survey must reference an existing
                acquisition case and parcel.
              </span>
            </div>
          </div>

          <div className="survey-create__grid">
            <div className="survey-field">
              <label htmlFor="survey-case-id">
                Acquisition Case ID
              </label>

              <input
                id="survey-case-id"
                value={
                  form.acquisition_case_id
                }
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    acquisition_case_id:
                      event.target.value,
                  }))
                }
                placeholder="UUID"
                required
              />
            </div>

            <div className="survey-field">
              <label htmlFor="survey-parcel-id">
                Parcel ID
              </label>

              <input
                id="survey-parcel-id"
                value={form.parcel_id}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    parcel_id:
                      event.target.value,
                  }))
                }
                placeholder="UUID"
                required
              />
            </div>

            <div className="survey-field">
              <label htmlFor="survey-reference">
                Survey Reference
              </label>

              <input
                id="survey-reference"
                value={
                  form.survey_reference
                }
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    survey_reference:
                      event.target.value,
                  }))
                }
                placeholder="e.g. SUR-2026-001"
                maxLength={100}
                required
              />
            </div>

            <div className="survey-field">
              <label htmlFor="survey-recorded-area">
                Recorded Area (sq m)
              </label>

              <input
                id="survey-recorded-area"
                type="number"
                min="0.0001"
                step="0.0001"
                value={
                  form.recorded_area_sq_m
                }
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    recorded_area_sq_m:
                      event.target.value,
                  }))
                }
                placeholder="0.0000"
                required
              />
            </div>

            <div className="survey-field">
              <label htmlFor="survey-type">
                Survey Type
              </label>

              <select
                id="survey-type"
                value={form.survey_type}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    survey_type:
                      event.target.value as SurveyType,
                  }))
                }
              >
                {SURVEY_TYPES.map(
                  (surveyType) => (
                    <option
                      key={surveyType}
                      value={surveyType}
                    >
                      {formatLabel(
                        surveyType,
                      )}
                    </option>
                  ),
                )}
              </select>
            </div>

            <div className="survey-field">
              <label htmlFor="survey-method">
                Survey Method
              </label>

              <select
                id="survey-method"
                value={form.survey_method}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    survey_method:
                      event.target.value as SurveyMethod,
                  }))
                }
              >
                {SURVEY_METHODS.map(
                  (surveyMethod) => (
                    <option
                      key={surveyMethod}
                      value={surveyMethod}
                    >
                      {formatLabel(
                        surveyMethod,
                      )}
                    </option>
                  ),
                )}
              </select>
            </div>

            <div className="survey-field">
              <label htmlFor="survey-scheduled-at">
                Scheduled At
              </label>

              <input
                id="survey-scheduled-at"
                type="datetime-local"
                value={
                  form.scheduled_at
                }
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    scheduled_at:
                      event.target.value,
                  }))
                }
              />
            </div>

            <div className="survey-field">
              <label htmlFor="survey-surveyor">
                Surveyor User ID
              </label>

              <input
                id="survey-surveyor"
                value={
                  form.surveyor_user_id
                }
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    surveyor_user_id:
                      event.target.value,
                  }))
                }
                placeholder="Optional UUID"
              />
            </div>

            <div className="survey-field survey-create__full">
              <label htmlFor="survey-notes">
                Notes
              </label>

              <textarea
                id="survey-notes"
                value={form.notes}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    notes:
                      event.target.value,
                  }))
                }
                placeholder="Survey instructions or field notes"
              />
            </div>
          </div>

          <div className="survey-form-actions">
            <button
              type="button"
              className="survey-button survey-button--secondary"
              onClick={() => {
                setForm(INITIAL_FORM);
                setShowCreateForm(false);
              }}
              disabled={saving}
            >
              Cancel
            </button>

            <button
              type="submit"
              className="survey-button survey-button--primary"
              disabled={saving}
            >
              {saving
                ? 'Creating...'
                : 'Create Survey'}
            </button>
          </div>
        </form>
      )}

      <div className="survey-toolbar">
        <div className="survey-field">
          <label htmlFor="survey-case-filter">
            Acquisition Case ID
          </label>

          <input
            id="survey-case-filter"
            value={caseFilter}
            onChange={(event) => {
              setOffset(0);
              setCaseFilter(
                event.target.value,
              );
            }}
            placeholder="Filter by case UUID"
          />
        </div>

        <div className="survey-field">
          <label htmlFor="survey-parcel-filter">
            Parcel ID
          </label>

          <input
            id="survey-parcel-filter"
            value={parcelFilter}
            onChange={(event) => {
              setOffset(0);
              setParcelFilter(
                event.target.value,
              );
            }}
            placeholder="Filter by parcel UUID"
          />
        </div>

        <div className="survey-field">
          <label htmlFor="survey-status-filter">
            Status
          </label>

          <select
            id="survey-status-filter"
            value={statusFilter}
            onChange={(event) => {
              setOffset(0);
              setStatusFilter(
                event.target.value,
              );
            }}
          >
            <option value="">
              All statuses
            </option>

            {SURVEY_STATUSES.map(
              (status) => (
                <option
                  key={status}
                  value={status}
                >
                  {formatLabel(status)}
                </option>
              ),
            )}
          </select>
        </div>

        <button
          type="button"
          className="survey-button survey-button--secondary"
          onClick={() => {
            setOffset(0);
            void loadSurveys();
          }}
          disabled={loading}
        >
          {loading
            ? 'Refreshing...'
            : 'Refresh'}
        </button>
      </div>

      <div className="survey-layout">
        <section className="survey-panel">
          <div className="survey-panel__header">
            <h2 className="survey-panel__title">
              Survey Records
            </h2>

            <span className="survey-panel__meta">
              {total} total
            </span>
          </div>

          {loading ? (
            <div className="survey-loading">
              Loading survey records...
            </div>
          ) : surveys.length === 0 ? (
            <div className="survey-empty">
              No survey records found.
            </div>
          ) : (
            <>
              <div className="survey-table-wrapper">
                <table className="survey-table">
                  <thead>
                    <tr>
                      <th>Reference</th>
                      <th>Type</th>
                      <th>Method</th>
                      <th>Status</th>
                      <th>Recorded Area</th>
                      <th>Measured Area</th>
                      <th>Conducted</th>
                    </tr>
                  </thead>

                  <tbody>
                    {surveys.map(
                      (survey) => (
                        <tr
                          key={survey.id}
                          className={
                            selectedSurvey?.id ===
                            survey.id
                              ? 'selected'
                              : ''
                          }
                          onClick={() =>
                            void handleSelectSurvey(
                              survey,
                            )
                          }
                        >
                          <td>
                            <div className="survey-reference">
                              {
                                survey.survey_reference
                              }
                            </div>

                            <div className="survey-subtext">
                              {survey.id}
                            </div>
                          </td>

                          <td>
                            {formatLabel(
                              survey.survey_type,
                            )}
                          </td>

                          <td>
                            {formatLabel(
                              survey.survey_method,
                            )}
                          </td>

                          <td>
                            <span
                              className={statusClass(
                                survey.status,
                              )}
                            >
                              {formatLabel(
                                survey.status,
                              )}
                            </span>
                          </td>

                          <td>
                            {formatNumber(
                              survey.recorded_area_sq_m,
                            )}{' '}
                            sq m
                          </td>

                          <td>
                            {formatNumber(
                              survey.measured_area_sq_m,
                            )}{' '}
                            {survey.measured_area_sq_m
                              ? 'sq m'
                              : ''}
                          </td>

                          <td>
                            {formatDateTime(
                              survey.conducted_at,
                            )}
                          </td>
                        </tr>
                      ),
                    )}
                  </tbody>
                </table>
              </div>

              <div className="survey-pagination">
                <span className="survey-pagination__info">
                  Page {currentPage} of{' '}
                  {totalPages}
                </span>

                <div className="survey-pagination__actions">
                  <button
                    type="button"
                    className="survey-button survey-button--secondary"
                    disabled={
                      !hasPreviousPage ||
                      loading
                    }
                    onClick={() =>
                      setOffset(
                        Math.max(
                          0,
                          offset -
                            PAGE_SIZE,
                        ),
                      )
                    }
                  >
                    Previous
                  </button>

                  <button
                    type="button"
                    className="survey-button survey-button--secondary"
                    disabled={
                      !hasNextPage ||
                      loading
                    }
                    onClick={() =>
                      setOffset(
                        offset +
                          PAGE_SIZE,
                      )
                    }
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )}
        </section>

        <aside className="survey-panel">
          <div className="survey-panel__header">
            <h2 className="survey-panel__title">
              Survey Details
            </h2>

            {detailLoading && (
              <span className="survey-panel__meta">
                Loading...
              </span>
            )}
          </div>

          {!selectedSurvey ? (
            <div className="survey-empty">
              Select a survey record to view its
              details and available workflow
              actions.
            </div>
          ) : (
            <div className="survey-detail">
              <h3 className="survey-detail__reference">
                {
                  selectedSurvey.survey_reference
                }
              </h3>

              <div className="survey-detail__status">
                <span
                  className={statusClass(
                    selectedSurvey.status,
                  )}
                >
                  {formatLabel(
                    selectedSurvey.status,
                  )}
                </span>
              </div>

              <div className="survey-detail__grid">
                <div className="survey-detail__item">
                  <div className="survey-detail__label">
                    Survey ID
                  </div>

                  <div className="survey-detail__value">
                    {selectedSurvey.id}
                  </div>
                </div>

                <div className="survey-detail__item">
                  <div className="survey-detail__label">
                    Acquisition Case
                  </div>

                  <div className="survey-detail__value">
                    {
                      selectedSurvey.acquisition_case_id
                    }
                  </div>
                </div>

                <div className="survey-detail__item">
                  <div className="survey-detail__label">
                    Parcel
                  </div>

                  <div className="survey-detail__value">
                    {
                      selectedSurvey.parcel_id
                    }
                  </div>
                </div>

                <div className="survey-detail__item">
                  <div className="survey-detail__label">
                    Survey Type
                  </div>

                  <div className="survey-detail__value">
                    {formatLabel(
                      selectedSurvey.survey_type,
                    )}
                  </div>
                </div>

                <div className="survey-detail__item">
                  <div className="survey-detail__label">
                    Survey Method
                  </div>

                  <div className="survey-detail__value">
                    {formatLabel(
                      selectedSurvey.survey_method,
                    )}
                  </div>
                </div>

                <div className="survey-detail__item">
                  <div className="survey-detail__label">
                    Surveyor
                  </div>

                  <div className="survey-detail__value">
                    {selectedSurvey.surveyor_user_id ??
                      'Not assigned'}
                  </div>
                </div>

                <div className="survey-detail__item">
                  <div className="survey-detail__label">
                    Scheduled
                  </div>

                  <div className="survey-detail__value">
                    {formatDateTime(
                      selectedSurvey.scheduled_at,
                    )}
                  </div>
                </div>

                <div className="survey-detail__item">
                  <div className="survey-detail__label">
                    Conducted
                  </div>

                  <div className="survey-detail__value">
                    {formatDateTime(
                      selectedSurvey.conducted_at,
                    )}
                  </div>
                </div>

                <div className="survey-detail__item">
                  <div className="survey-detail__label">
                    Recorded Area
                  </div>

                  <div className="survey-detail__value">
                    {formatNumber(
                      selectedSurvey.recorded_area_sq_m,
                    )}{' '}
                    sq m
                  </div>
                </div>

                <div className="survey-detail__item">
                  <div className="survey-detail__label">
                    Measured Area
                  </div>

                  <div className="survey-detail__value">
                    {formatNumber(
                      selectedSurvey.measured_area_sq_m,
                    )}{' '}
                    {selectedSurvey.measured_area_sq_m
                      ? 'sq m'
                      : ''}
                  </div>
                </div>

                <div className="survey-detail__item">
                  <div className="survey-detail__label">
                    Area Difference
                  </div>

                  <div className="survey-detail__value">
                    {areaDifferenceText}
                  </div>
                </div>

                <div className="survey-detail__item">
                  <div className="survey-detail__label">
                    Difference %
                  </div>

                  <div className="survey-detail__value">
                    {
                      areaDifferencePercentageText
                    }
                  </div>
                </div>
              </div>

              {selectedSurvey.notes && (
                <div className="survey-detail__section">
                  <h4 className="survey-detail__section-title">
                    Notes
                  </h4>

                  <div className="survey-detail__value">
                    {selectedSurvey.notes}
                  </div>
                </div>
              )}

              <div className="survey-detail__section">
                <h4 className="survey-detail__section-title">
                  Workflow Actions
                </h4>

                <div className="survey-actions">
                  {canStart(
                    selectedSurvey.status,
                  ) && (
                    <button
                      type="button"
                      className="survey-button survey-button--primary"
                      disabled={
                        actionLoading
                      }
                      onClick={() =>
                        void executeAction(
                          startSurvey,
                          'Survey started successfully.',
                        )
                      }
                    >
                      Start Survey
                    </button>
                  )}

                  {canReview(
                    selectedSurvey.status,
                  ) && (
                    <button
                      type="button"
                      className="survey-button survey-button--warning"
                      disabled={
                        actionLoading
                      }
                      onClick={() =>
                        void executeAction(
                          reviewSurvey,
                          'Survey sent for review.',
                        )
                      }
                    >
                      Send for Review
                    </button>
                  )}

                  {canVerify(
                    selectedSurvey.status,
                  ) && (
                    <button
                      type="button"
                      className="survey-button survey-button--success"
                      disabled={
                        actionLoading
                      }
                      onClick={() =>
                        void executeAction(
                          verifySurvey,
                          'Survey verified successfully.',
                        )
                      }
                    >
                      Verify Survey
                    </button>
                  )}

                  {canCancel(
                    selectedSurvey.status,
                  ) && (
                    <button
                      type="button"
                      className="survey-button survey-button--danger"
                      disabled={
                        actionLoading
                      }
                      onClick={() => {
                        const confirmed =
                          window.confirm(
                            'Cancel this survey record?',
                          );

                        if (confirmed) {
                          void executeAction(
                            cancelSurvey,
                            'Survey cancelled successfully.',
                          );
                        }
                      }}
                    >
                      Cancel Survey
                    </button>
                  )}
                </div>
              </div>

              {canComplete(
                selectedSurvey.status,
              ) && (
                <div className="survey-detail__section">
                  <h4 className="survey-detail__section-title">
                    Complete Measurement
                  </h4>

                  <div className="survey-field">
                    <label htmlFor="measured-area">
                      Measured Area (sq m)
                    </label>

                    <input
                      id="measured-area"
                      type="number"
                      min="0.0001"
                      step="0.0001"
                      value={measuredArea}
                      onChange={(event) =>
                        setMeasuredArea(
                          event.target.value,
                        )
                      }
                      placeholder="Enter measured area"
                    />
                  </div>

                  <div
                    className="survey-field"
                    style={{
                      marginTop: '12px',
                    }}
                  >
                    <label htmlFor="conducted-at">
                      Conducted At
                    </label>

                    <input
                      id="conducted-at"
                      type="datetime-local"
                      value={conductedAt}
                      onChange={(event) =>
                        setConductedAt(
                          event.target.value,
                        )
                      }
                    />
                  </div>

                  <div
                    className="survey-form-actions"
                    style={{
                      justifyContent:
                        'flex-start',
                    }}
                  >
                    <button
                      type="button"
                      className="survey-button survey-button--primary"
                      disabled={
                        actionLoading
                      }
                      onClick={() =>
                        void handleComplete()
                      }
                    >
                      {actionLoading
                        ? 'Saving...'
                        : 'Complete Measurement'}
                    </button>
                  </div>
                </div>
              )}

              {selectedSurvey.verified_at && (
                <div className="survey-detail__section">
                  <h4 className="survey-detail__section-title">
                    Verification
                  </h4>

                  <div className="survey-detail__grid">
                    <div className="survey-detail__item">
                      <div className="survey-detail__label">
                        Verified By
                      </div>

                      <div className="survey-detail__value">
                        {
                          selectedSurvey.verified_by_user_id
                        }
                      </div>
                    </div>

                    <div className="survey-detail__item">
                      <div className="survey-detail__label">
                        Verified At
                      </div>

                      <div className="survey-detail__value">
                        {formatDateTime(
                          selectedSurvey.verified_at,
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </aside>
      </div>
    </section>
  );
}