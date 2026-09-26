import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react';

import {
  activateAcquisitionCase,
  cancelAcquisitionCase,
  closeAcquisitionCase,
  createAcquisitionCase,
  getAcquisitionCase,
  holdAcquisitionCase,
  listAcquisitionCaseStageHistory,
  listAcquisitionCases,
  listLandRequirements,
  resumeAcquisitionCase,
  transitionAcquisitionCaseStage,
  updateAcquisitionCase,
} from '../lib/api';

import type {
  AcquisitionCase,
  AcquisitionCaseListResponse,
  AcquisitionCaseLegalFramework,
  AcquisitionCaseLegalRoute,
  AcquisitionCaseAcquisitionMethod,
  AcquisitionCaseStage,
  AcquisitionCaseStageHistory,
  AcquisitionCaseStatus,
  CreateAcquisitionCaseRequest,
  UpdateAcquisitionCaseRequest,
} from '../types/acquisitionCases';

import type {
  LandRequirement,
} from '../types/landRequirements';

import '../App.css';

type Props = {
  permissions: Set<string>;
};

const STATUS_OPTIONS: AcquisitionCaseStatus[] = [
  'DRAFT',
  'ACTIVE',
  'ON_HOLD',
  'CANCELLED',
  'CLOSED',
];

const STAGE_OPTIONS: AcquisitionCaseStage[] = [
  'INITIATION',
  'SIA',
  'PRELIMINARY_NOTIFICATION',
  'OBJECTIONS_AND_HEARING',
  'DECLARATION',
  'R_AND_R',
  'CLAIMS_AND_ENQUIRY',
  'COMPENSATION_DETERMINATION',
  'AWARD',
  'COMPENSATION_AND_RR',
  'POSSESSION',
  'VESTING',
  'HANDOVER',
];

const LEGAL_FRAMEWORK_OPTIONS: AcquisitionCaseLegalFramework[] = [
  'RFCTLARR_2013',
  'SPECIAL_CENTRAL_ACT',
  'STATE_LAW',
  'OTHER',
];

const LEGAL_ROUTE_OPTIONS: AcquisitionCaseLegalRoute[] = [
  'RFCTLARR_STANDARD',
  'RFCTLARR_URGENT',
  'SPECIAL_ACT_ROUTE',
  'STATE_SPECIFIC_ROUTE',
  'NEGOTIATED_PURCHASE',
];

const ACQUISITION_METHOD_OPTIONS: AcquisitionCaseAcquisitionMethod[] = [
  'COMPULSORY_ACQUISITION',
  'CONSENT_BASED',
  'NEGOTIATED_PURCHASE',
];

function humanize(value: string): string {
  return value
    .toLowerCase()
    .split('_')
    .map(
      (part) =>
        part.charAt(0).toUpperCase() +
        part.slice(1),
    )
    .join(' ');
}

function formatDate(value: string | null): string {
  if (!value) {
    return '—';
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return 'Unavailable';
  }

  return date.toLocaleString();
}

function statusClass(
  status: AcquisitionCaseStatus,
): string {
  return `aakar-case-status aakar-case-status-${status.toLowerCase()}`;
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return 'Something went wrong. Please try again.';
}

const initialCreateForm: CreateAcquisitionCaseRequest = {
  land_requirement_id: '',
  case_number: '',
  legal_framework: 'RFCTLARR_2013',
  legal_route: 'RFCTLARR_STANDARD',
  acquisition_method: 'COMPULSORY_ACQUISITION',
  responsible_authority_id: null,
  assigned_user_id: null,
  description: null,
};

export default function AcquisitionCaseWorkspace({
  permissions,
}: Props) {
  const [cases, setCases] = useState<AcquisitionCase[]>([]);
  const [total, setTotal] = useState(0);

  const [
    approvedLandRequirements,
    setApprovedLandRequirements,
  ] = useState<LandRequirement[]>([]);

  const [selectedCase, setSelectedCase] =
    useState<AcquisitionCase | null>(null);

  const [stageHistory, setStageHistory] =
    useState<AcquisitionCaseStageHistory[]>([]);

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] =
    useState<AcquisitionCaseStatus | ''>('');
  const [stageFilter, setStageFilter] =
    useState<AcquisitionCaseStage | ''>('');
  const [frameworkFilter, setFrameworkFilter] =
    useState('');
  const [methodFilter, setMethodFilter] =
    useState('');

  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] =
    useState(false);
  const [historyLoading, setHistoryLoading] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);

  const [actionError, setActionError] =
    useState<string | null>(null);

  const [showCreate, setShowCreate] =
    useState(false);

  const [showEdit, setShowEdit] =
    useState(false);

  const [createForm, setCreateForm] =
    useState<CreateAcquisitionCaseRequest>(
      initialCreateForm,
    );

  const [editForm, setEditForm] =
    useState<UpdateAcquisitionCaseRequest>({
      expected_version: 1,
      legal_framework: 'RFCTLARR_2013',
      legal_route: null,
      acquisition_method:
        'COMPULSORY_ACQUISITION',
      responsible_authority_id: null,
      assigned_user_id: null,
      description: null,
    });

  const [targetStage, setTargetStage] =
    useState<AcquisitionCaseStage>(
      'SIA',
    );

  const [stageReason, setStageReason] =
    useState('');

  const [actionReason, setActionReason] =
    useState('');

  const canCreate =
    permissions.has('acquisition_case.create');

  const canUpdate =
    permissions.has('acquisition_case.update');

  const canActivate =
    permissions.has(
      'acquisition_case.activate',
    );

  const canHold =
    permissions.has('acquisition_case.hold');

  const canResume =
    permissions.has('acquisition_case.resume');

  const canCancel =
    permissions.has('acquisition_case.cancel');

  const canClose =
    permissions.has('acquisition_case.close');

  const canTransition =
    permissions.has(
      'acquisition_case.stage_transition',
    );

  const loadCases = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response: AcquisitionCaseListResponse =
        await listAcquisitionCases({
          search: search.trim() || undefined,
          status:
            statusFilter || undefined,
          current_stage:
            stageFilter || undefined,
          legal_framework:
            frameworkFilter || undefined,
          acquisition_method:
            methodFilter || undefined,
          offset: 0,
          limit: 50,
        });

      setCases(response.items);
      setTotal(response.total);

      if (
        selectedCase &&
        !response.items.some(
          (item) =>
            item.id === selectedCase.id,
        )
      ) {
        setSelectedCase(null);
      }
    } catch (requestError) {
      setError(
        getErrorMessage(requestError),
      );
    } finally {
      setLoading(false);
    }
  }, [
    search,
    statusFilter,
    stageFilter,
    frameworkFilter,
    methodFilter,
    selectedCase,
  ]);

  const loadApprovedLandRequirements =
    useCallback(async () => {
      try {
        const response =
          await listLandRequirements({
            status: 'APPROVED',
            offset: 0,
            limit: 100,
          });

        setApprovedLandRequirements(
          response.items,
        );
      } catch (requestError) {
        setError(
          getErrorMessage(requestError),
        );
      }
    }, []);

  const loadCaseDetail = useCallback(
    async (caseId: string) => {
      setDetailLoading(true);
      setActionError(null);

      try {
        const detail =
          await getAcquisitionCase(caseId);

        setSelectedCase(detail);

        setEditForm({
          expected_version: detail.version,
          legal_framework:
            detail.legal_framework,
          legal_route:
            detail.legal_route,
          acquisition_method:
            detail.acquisition_method,
          responsible_authority_id:
            detail.responsible_authority_id,
          assigned_user_id:
            detail.assigned_user_id,
          description:
            detail.description,
        });

        setTargetStage(
          detail.current_stage,
        );

        setStageReason('');
        setActionReason('');

        setHistoryLoading(true);

        try {
          const history =
            await listAcquisitionCaseStageHistory(
              caseId,
            );

          setStageHistory(history);
        } finally {
          setHistoryLoading(false);
        }
      } catch (requestError) {
        setActionError(
          getErrorMessage(requestError),
        );
      } finally {
        setDetailLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    void loadCases();
  }, [loadCases]);

  useEffect(() => {
    void loadApprovedLandRequirements();
  }, [loadApprovedLandRequirements]);

  const refreshSelectedCase =
    useCallback(async () => {
      if (!selectedCase) {
        return;
      }

      await loadCaseDetail(
        selectedCase.id,
      );

      await loadCases();
    }, [
      selectedCase,
      loadCaseDetail,
      loadCases,
    ]);

  const handleCreate = async (
    event: React.FormEvent,
  ) => {
    event.preventDefault();

    setActionError(null);

    if (!createForm.land_requirement_id) {
      setActionError(
        'Select an approved land requirement.',
      );
      return;
    }

    if (!createForm.case_number.trim()) {
      setActionError(
        'Case number is required.',
      );
      return;
    }

    try {
      const created =
        await createAcquisitionCase({
          ...createForm,
          case_number:
            createForm.case_number.trim(),
          description:
            createForm.description?.trim() ||
            null,
        });

      setShowCreate(false);
      setCreateForm(initialCreateForm);

      setCases((current) => [
        created,
        ...current,
      ]);

      setTotal(
        (current) => current + 1,
      );

      await loadCaseDetail(
        created.id,
      );

      await loadCases();
    } catch (requestError) {
      setActionError(
        getErrorMessage(requestError),
      );
    }
  };

  const handleUpdate = async (
    event: React.FormEvent,
  ) => {
    event.preventDefault();

    if (!selectedCase) {
      return;
    }

    setActionError(null);

    try {
      const updated =
        await updateAcquisitionCase(
          selectedCase.id,
          {
            ...editForm,
            expected_version:
              selectedCase.version,
            description:
              editForm.description?.trim() ||
              null,
          },
        );

      setSelectedCase(updated);
      setShowEdit(false);

      await loadCases();
      await loadCaseDetail(
        updated.id,
      );
    } catch (requestError) {
      setActionError(
        getErrorMessage(requestError),
      );
    }
  };

  const executeAction = async (
    action: () => Promise<unknown>,
  ) => {
    if (!selectedCase) {
      return;
    }

    setActionError(null);

    try {
      await action();
      await refreshSelectedCase();
    } catch (requestError) {
      setActionError(
        getErrorMessage(requestError),
      );
    }
  };

  const handleActivate = () => {
    if (!selectedCase) {
      return;
    }

    void executeAction(() =>
      activateAcquisitionCase(
        selectedCase.id,
        {
          expected_version:
            selectedCase.version,
        },
      ),
    );
  };

  const handleHold = () => {
    if (!selectedCase) {
      return;
    }

    const reason =
      actionReason.trim();

    if (!reason) {
      setActionError(
        'A reason is required to place a case on hold.',
      );
      return;
    }

    void executeAction(() =>
      holdAcquisitionCase(
        selectedCase.id,
        {
          expected_version:
            selectedCase.version,
          reason,
        },
      ),
    );
  };

  const handleResume = () => {
    if (!selectedCase) {
      return;
    }

    void executeAction(() =>
      resumeAcquisitionCase(
        selectedCase.id,
        {
          expected_version:
            selectedCase.version,
        },
      ),
    );
  };

  const handleCancel = () => {
    if (!selectedCase) {
      return;
    }

    const reason =
      actionReason.trim();

    if (!reason) {
      setActionError(
        'A reason is required to cancel a case.',
      );
      return;
    }

    void executeAction(() =>
      cancelAcquisitionCase(
        selectedCase.id,
        {
          expected_version:
            selectedCase.version,
          reason,
        },
      ),
    );
  };

  const handleClose = () => {
    if (!selectedCase) {
      return;
    }

    void executeAction(() =>
      closeAcquisitionCase(
        selectedCase.id,
        {
          expected_version:
            selectedCase.version,
        },
      ),
    );
  };

  const handleStageTransition = () => {
    if (!selectedCase) {
      return;
    }

    if (
      targetStage ===
      selectedCase.current_stage
    ) {
      setActionError(
        'Select a different stage.',
      );
      return;
    }

    void executeAction(() =>
      transitionAcquisitionCaseStage(
        selectedCase.id,
        {
          to_stage: targetStage,
          reason:
            stageReason.trim() || null,
          expected_version:
            selectedCase.version,
        },
      ),
    );
  };

  const allowedNextStages = useMemo(() => {
    if (!selectedCase) {
      return [];
    }

    const transitionMap: Record<
      AcquisitionCaseStage,
      AcquisitionCaseStage[]
    > = {
      INITIATION: [
        'SIA',
        'PRELIMINARY_NOTIFICATION',
      ],

      SIA: [
        'PRELIMINARY_NOTIFICATION',
      ],

      PRELIMINARY_NOTIFICATION: [
        'OBJECTIONS_AND_HEARING',
      ],

      OBJECTIONS_AND_HEARING: [
        'DECLARATION',
      ],

      DECLARATION: [
        'R_AND_R',
        'CLAIMS_AND_ENQUIRY',
      ],

      R_AND_R: [
        'CLAIMS_AND_ENQUIRY',
      ],

      CLAIMS_AND_ENQUIRY: [
        'COMPENSATION_DETERMINATION',
      ],

      COMPENSATION_DETERMINATION: [
        'AWARD',
      ],

      AWARD: [
        'COMPENSATION_AND_RR',
      ],

      COMPENSATION_AND_RR: [
        'POSSESSION',
      ],

      POSSESSION: [
        'VESTING',
      ],

      VESTING: [
        'HANDOVER',
      ],

      HANDOVER: [],
    };

    return (
      transitionMap[
        selectedCase.current_stage
      ] ?? []
    );
  }, [selectedCase]);

  const landRequirementLabel =
    useCallback(
      (landRequirementId: string) => {
        const requirement =
          approvedLandRequirements.find(
            (item) =>
              item.id ===
              landRequirementId,
          );

        if (!requirement) {
          return landRequirementId;
        }

        return `${requirement.requirement_reference} — ${requirement.purpose}`;
      },
      [approvedLandRequirements],
    );

  return (
    <section className="aakar-workspace">
      <div className="aakar-workspace-header">
        <div>
          <div className="aakar-eyebrow">
            LAND ACQUISITION OPERATIONS
          </div>

          <h1>
            Acquisition Case Management
          </h1>

          <p>
            Manage acquisition cases created from
            approved land requirements and control
            their operational lifecycle.
          </p>
        </div>

        {canCreate && (
          <button
            type="button"
            className="aakar-primary-button"
            onClick={() => {
              setActionError(null);
              setShowCreate(true);
            }}
          >
            + New Acquisition Case
          </button>
        )}
      </div>

      {error && (
        <div className="aakar-alert aakar-alert-error">
          {error}
        </div>
      )}

      {actionError && (
        <div className="aakar-alert aakar-alert-error">
          {actionError}
        </div>
      )}

      <div className="aakar-filter-panel">
        <div className="aakar-filter-field">
          <label htmlFor="case-search">
            Search
          </label>

          <input
            id="case-search"
            value={search}
            onChange={(event) =>
              setSearch(
                event.target.value,
              )
            }
            placeholder="Case number or description"
          />
        </div>

        <div className="aakar-filter-field">
          <label htmlFor="case-status">
            Status
          </label>

          <select
            id="case-status"
            value={statusFilter}
            onChange={(event) =>
              setStatusFilter(
                event.target.value as
                  | AcquisitionCaseStatus
                  | '',
              )
            }
          >
            <option value="">
              All statuses
            </option>

            {STATUS_OPTIONS.map(
              (status) => (
                <option
                  key={status}
                  value={status}
                >
                  {humanize(status)}
                </option>
              ),
            )}
          </select>
        </div>

        <div className="aakar-filter-field">
          <label htmlFor="case-stage">
            Stage
          </label>

          <select
            id="case-stage"
            value={stageFilter}
            onChange={(event) =>
              setStageFilter(
                event.target.value as
                  | AcquisitionCaseStage
                  | '',
              )
            }
          >
            <option value="">
              All stages
            </option>

            {STAGE_OPTIONS.map(
              (stage) => (
                <option
                  key={stage}
                  value={stage}
                >
                  {humanize(stage)}
                </option>
              ),
            )}
          </select>
        </div>

        <div className="aakar-filter-field">
          <label htmlFor="case-framework">
            Legal Framework
          </label>

          <select
            id="case-framework"
            value={frameworkFilter}
            onChange={(event) =>
              setFrameworkFilter(
                event.target.value,
              )
            }
          >
            <option value="">
              All frameworks
            </option>

            {LEGAL_FRAMEWORK_OPTIONS.map(
              (framework) => (
                <option
                  key={framework}
                  value={framework}
                >
                  {humanize(framework)}
                </option>
              ),
            )}
          </select>
        </div>

        <div className="aakar-filter-field">
          <label htmlFor="case-method">
            Acquisition Method
          </label>

          <select
            id="case-method"
            value={methodFilter}
            onChange={(event) =>
              setMethodFilter(
                event.target.value,
              )
            }
          >
            <option value="">
              All methods
            </option>

            {ACQUISITION_METHOD_OPTIONS.map(
              (method) => (
                <option
                  key={method}
                  value={method}
                >
                  {humanize(method)}
                </option>
              ),
            )}
          </select>
        </div>

        <button
          type="button"
          className="aakar-secondary-button"
          onClick={() => {
            setSearch('');
            setStatusFilter('');
            setStageFilter('');
            setFrameworkFilter('');
            setMethodFilter('');
          }}
        >
          Clear
        </button>
      </div>

      <div className="aakar-case-layout">
        <div className="aakar-case-list-panel">
          <div className="aakar-panel-header">
            <div>
              <strong>
                Acquisition Cases
              </strong>

              <span>
                {total} total
              </span>
            </div>

            <button
              type="button"
              className="aakar-secondary-button"
              onClick={() =>
                void loadCases()
              }
              disabled={loading}
            >
              {loading
                ? 'Refreshing…'
                : 'Refresh'}
            </button>
          </div>

          {loading &&
          cases.length === 0 ? (
            <div className="aakar-empty-state">
              Loading acquisition cases…
            </div>
          ) : cases.length === 0 ? (
            <div className="aakar-empty-state">
              <strong>
                No acquisition cases found
              </strong>

              <span>
                Create a case from an approved
                land requirement.
              </span>
            </div>
          ) : (
            <div className="aakar-case-table-wrapper">
              <table className="aakar-data-table">
                <thead>
                  <tr>
                    <th>Case</th>
                    <th>Status</th>
                    <th>Stage</th>
                    <th>Method</th>
                    <th>Framework</th>
                  </tr>
                </thead>

                <tbody>
                  {cases.map(
                    (item) => (
                      <tr
                        key={item.id}
                        className={
                          selectedCase?.id ===
                          item.id
                            ? 'aakar-table-row-selected'
                            : ''
                        }
                        onClick={() =>
                          void loadCaseDetail(
                            item.id,
                          )
                        }
                      >
                        <td>
                          <strong>
                            {
                              item.case_number
                            }
                          </strong>

                          <small>
                            {landRequirementLabel(
                              item.land_requirement_id,
                            )}
                          </small>
                        </td>

                        <td>
                          <span
                            className={statusClass(
                              item.status,
                            )}
                          >
                            {humanize(
                              item.status,
                            )}
                          </span>
                        </td>

                        <td>
                          {humanize(
                            item.current_stage,
                          )}
                        </td>

                        <td>
                          {humanize(
                            item.acquisition_method,
                          )}
                        </td>

                        <td>
                          {humanize(
                            item.legal_framework,
                          )}
                        </td>
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="aakar-case-detail-panel">
          {!selectedCase ? (
            <div className="aakar-empty-state aakar-case-detail-empty">
              <strong>
                Select an acquisition case
              </strong>

              <span>
                Case details, lifecycle actions and
                stage history will appear here.
              </span>
            </div>
          ) : detailLoading ? (
            <div className="aakar-empty-state">
              Loading case…
            </div>
          ) : (
            <>
              <div className="aakar-panel-header">
                <div>
                  <span className="aakar-eyebrow">
                    CASE
                  </span>

                  <h2>
                    {
                      selectedCase.case_number
                    }
                  </h2>

                  <span>
                    Version{' '}
                    {selectedCase.version}
                  </span>
                </div>

                {canUpdate &&
                  selectedCase.status !==
                    'CANCELLED' &&
                  selectedCase.status !==
                    'CLOSED' && (
                    <button
                      type="button"
                      className="aakar-secondary-button"
                      onClick={() =>
                        setShowEdit(true)
                      }
                    >
                      Edit
                    </button>
                  )}
              </div>

              <div className="aakar-case-summary-grid">
                <div>
                  <span>Status</span>

                  <strong>
                    {humanize(
                      selectedCase.status,
                    )}
                  </strong>
                </div>

                <div>
                  <span>
                    Current Stage
                  </span>

                  <strong>
                    {humanize(
                      selectedCase.current_stage,
                    )}
                  </strong>
                </div>

                <div>
                  <span>
                    Legal Framework
                  </span>

                  <strong>
                    {humanize(
                      selectedCase.legal_framework,
                    )}
                  </strong>
                </div>

                <div>
                  <span>
                    Acquisition Method
                  </span>

                  <strong>
                    {humanize(
                      selectedCase.acquisition_method,
                    )}
                  </strong>
                </div>

                <div>
                  <span>Opened</span>

                  <strong>
                    {formatDate(
                      selectedCase.opened_at,
                    )}
                  </strong>
                </div>

                <div>
                  <span>Closed</span>

                  <strong>
                    {formatDate(
                      selectedCase.closed_at,
                    )}
                  </strong>
                </div>
              </div>

              <div className="aakar-case-section">
                <h3>
                  Land Requirement
                </h3>

                <p>
                  {landRequirementLabel(
                    selectedCase.land_requirement_id,
                  )}
                </p>
              </div>

              {selectedCase.description && (
                <div className="aakar-case-section">
                  <h3>
                    Description
                  </h3>

                  <p>
                    {
                      selectedCase.description
                    }
                  </p>
                </div>
              )}

              <div className="aakar-case-section">
                <h3>
                  Lifecycle Actions
                </h3>

                <div className="aakar-action-grid">
                  {canActivate &&
                    selectedCase.status ===
                      'DRAFT' && (
                      <button
                        type="button"
                        className="aakar-primary-button"
                        onClick={
                          handleActivate
                        }
                      >
                        Activate
                      </button>
                    )}

                  {canHold &&
                    selectedCase.status ===
                      'ACTIVE' && (
                      <button
                        type="button"
                        className="aakar-secondary-button"
                        onClick={
                          handleHold
                        }
                      >
                        Hold
                      </button>
                    )}

                  {canResume &&
                    selectedCase.status ===
                      'ON_HOLD' && (
                      <button
                        type="button"
                        className="aakar-primary-button"
                        onClick={
                          handleResume
                        }
                      >
                        Resume
                      </button>
                    )}

                  {canCancel &&
                    ![
                      'CANCELLED',
                      'CLOSED',
                    ].includes(
                      selectedCase.status,
                    ) && (
                      <button
                        type="button"
                        className="aakar-danger-button"
                        onClick={
                          handleCancel
                        }
                      >
                        Cancel Case
                      </button>
                    )}

                  {canClose &&
                    selectedCase.status ===
                      'ACTIVE' &&
                    selectedCase.current_stage ===
                      'HANDOVER' && (
                      <button
                        type="button"
                        className="aakar-primary-button"
                        onClick={
                          handleClose
                        }
                      >
                        Close Case
                      </button>
                    )}
                </div>

                {(canHold ||
                  canCancel) &&
                  ![
                    'CANCELLED',
                    'CLOSED',
                  ].includes(
                    selectedCase.status,
                  ) && (
                    <textarea
                      value={actionReason}
                      onChange={(event) =>
                        setActionReason(
                          event.target.value,
                        )
                      }
                      placeholder="Reason for hold/cancellation"
                      rows={3}
                    />
                  )}
              </div>

              <div className="aakar-case-section">
                <h3>
                  Stage Transition
                </h3>

                {canTransition &&
                selectedCase.status ===
                  'ACTIVE' &&
                allowedNextStages.length >
                  0 ? (
                  <>
                    <div className="aakar-inline-form">
                      <select
                        value={targetStage}
                        onChange={(event) =>
                          setTargetStage(
                            event.target
                              .value as AcquisitionCaseStage,
                          )
                        }
                      >
                        {allowedNextStages.map(
                          (stage) => (
                            <option
                              key={stage}
                              value={stage}
                            >
                              {humanize(
                                stage,
                              )}
                            </option>
                          ),
                        )}
                      </select>

                      <button
                        type="button"
                        className="aakar-primary-button"
                        onClick={
                          handleStageTransition
                        }
                      >
                        Move Stage
                      </button>
                    </div>

                    <textarea
                      value={stageReason}
                      onChange={(event) =>
                        setStageReason(
                          event.target.value,
                        )
                      }
                      placeholder="Optional transition reason"
                      rows={3}
                    />
                  </>
                ) : (
                  <p className="aakar-muted">
                    No stage transition is
                    available for the current
                    case state.
                  </p>
                )}
              </div>

              <div className="aakar-case-section">
                <h3>
                  Stage History
                </h3>

                {historyLoading ? (
                  <p>
                    Loading stage history…
                  </p>
                ) : stageHistory.length ===
                  0 ? (
                  <p className="aakar-muted">
                    No stage history recorded.
                  </p>
                ) : (
                  <div className="aakar-history-list">
                    {stageHistory.map(
                      (entry) => (
                        <div
                          key={entry.id}
                          className="aakar-history-item"
                        >
                          <div>
                            <strong>
                              {humanize(
                                entry.to_stage,
                              )}
                            </strong>

                            <span>
                              {entry.from_stage
                                ? `${humanize(
                                    entry.from_stage,
                                  )} → `
                                : 'Initial → '}

                              {humanize(
                                entry.to_stage,
                              )}
                            </span>
                          </div>

                          <small>
                            {formatDate(
                              entry.changed_at,
                            )}
                          </small>

                          {entry.reason && (
                            <p>
                              {entry.reason}
                            </p>
                          )}
                        </div>
                      ),
                    )}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {showCreate && (
        <div
          className="aakar-modal-backdrop acq-modal-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (
              event.target ===
              event.currentTarget
            ) {
              setShowCreate(false);
            }
          }}
        >
          <form
            className="aakar-modal acq-create-modal"
            onSubmit={handleCreate}
          >
            <div className="aakar-modal-header acq-create-modal-header">
              <div>
                <span className="aakar-eyebrow">
                  NEW CASE
                </span>

                <h2>
                  Create Acquisition Case
                </h2>

                <p>
                  Start an acquisition case from an approved
                  land requirement.
                </p>
              </div>

              <button
                type="button"
                className="aakar-icon-button"
                onClick={() =>
                  setShowCreate(false)
                }
                aria-label="Close"
              >
                ×
              </button>
            </div>

            <div className="acq-create-modal-body">
              <section className="acq-form-section">
                <div className="acq-form-section-heading">
                  <span className="acq-form-section-number">
                    01
                  </span>

                  <div>
                    <h3>Case Identification</h3>
                    <p>
                      Select the approved land requirement and
                      assign the official case reference.
                    </p>
                  </div>
                </div>

                <div className="aakar-form-grid">
                  <div className="aakar-form-field aakar-form-field-wide">
                    <label>
                      Approved Land Requirement
                      <span className="acq-required">*</span>
                    </label>

                    <select
                      value={
                        createForm.land_requirement_id
                      }
                      onChange={(event) =>
                        setCreateForm(
                          (
                            current: CreateAcquisitionCaseRequest,
                          ) => ({
                            ...current,
                            land_requirement_id:
                              event.target.value,
                          }),
                        )
                      }
                      required
                    >
                      <option value="">
                        Select approved land requirement
                      </option>

                      {approvedLandRequirements.map(
                        (requirement) => (
                          <option
                            key={requirement.id}
                            value={requirement.id}
                          >
                            {
                              requirement.requirement_reference
                            }{' '}
                            — {requirement.purpose}
                          </option>
                        ),
                      )}
                    </select>

                    <span className="acq-field-help">
                      Only approved land requirements can be
                      converted into an acquisition case.
                    </span>
                  </div>

                  <div className="aakar-form-field">
                    <label>
                      Case Number
                      <span className="acq-required">*</span>
                    </label>

                    <input
                      value={
                        createForm.case_number
                      }
                      onChange={(event) =>
                        setCreateForm(
                          (
                            current: CreateAcquisitionCaseRequest,
                          ) => ({
                            ...current,
                            case_number:
                              event.target.value,
                          }),
                        )
                      }
                      placeholder="e.g. LA/2026/0001"
                      required
                    />

                    <span className="acq-field-help">
                      Use the official case reference issued
                      by the acquiring authority.
                    </span>
                  </div>
                </div>
              </section>

              <section className="acq-form-section">
                <div className="acq-form-section-heading">
                  <span className="acq-form-section-number">
                    02
                  </span>

                  <div>
                    <h3>Legal &amp; Acquisition Details</h3>
                    <p>
                      Define the legal framework, route and
                      acquisition method applicable to this case.
                    </p>
                  </div>
                </div>

                <div className="aakar-form-grid">
                  <div className="aakar-form-field">
                    <label>Legal Framework</label>

                    <select
                      value={
                        createForm.legal_framework
                      }
                      onChange={(event) =>
                        setCreateForm(
                          (
                            current: CreateAcquisitionCaseRequest,
                          ) => ({
                            ...current,
                            legal_framework:
                              event.target
                                .value as AcquisitionCaseLegalFramework,
                          }),
                        )
                      }
                    >
                      {LEGAL_FRAMEWORK_OPTIONS.map(
                        (framework) => (
                          <option
                            key={framework}
                            value={framework}
                          >
                            {humanize(
                              framework,
                            )}
                          </option>
                        ),
                      )}
                    </select>
                  </div>

                  <div className="aakar-form-field">
                    <label>Legal Route</label>

                    <select
                      value={
                        createForm.legal_route ??
                        ''
                      }
                      onChange={(event) =>
                        setCreateForm(
                          (
                            current: CreateAcquisitionCaseRequest,
                          ) => ({
                            ...current,
                            legal_route:
                              (
                                event.target
                                  .value ||
                                null
                              ) as
                                | AcquisitionCaseLegalRoute
                                | null,
                          }),
                        )
                      }
                    >
                      <option value="">
                        Select route
                      </option>

                      {LEGAL_ROUTE_OPTIONS.map(
                        (route) => (
                          <option
                            key={route}
                            value={route}
                          >
                            {humanize(route)}
                          </option>
                        ),
                      )}
                    </select>
                  </div>

                  <div className="aakar-form-field aakar-form-field-wide">
                    <label>Acquisition Method</label>

                    <select
                      value={
                        createForm.acquisition_method
                      }
                      onChange={(event) =>
                        setCreateForm(
                          (
                            current: CreateAcquisitionCaseRequest,
                          ) => ({
                            ...current,
                            acquisition_method:
                              event.target
                                .value as AcquisitionCaseAcquisitionMethod,
                          }),
                        )
                      }
                    >
                      {ACQUISITION_METHOD_OPTIONS.map(
                        (method) => (
                          <option
                            key={method}
                            value={method}
                          >
                            {humanize(
                              method,
                            )}
                          </option>
                        ),
                      )}
                    </select>
                  </div>
                </div>
              </section>

              <section className="acq-form-section">
                <div className="acq-form-section-heading">
                  <span className="acq-form-section-number">
                    03
                  </span>

                  <div>
                    <h3>Operational Assignment</h3>
                    <p>
                      Optionally associate the responsible
                      authority and assigned officer.
                    </p>
                  </div>
                </div>

                <div className="aakar-form-grid">
                  <div className="aakar-form-field">
                    <label>Responsible Authority ID</label>

                    <input
                      value={
                        createForm.responsible_authority_id ??
                        ''
                      }
                      onChange={(event) =>
                        setCreateForm(
                          (
                            current: CreateAcquisitionCaseRequest,
                          ) => ({
                            ...current,
                            responsible_authority_id:
                              event.target.value ||
                              null,
                          }),
                        )
                      }
                      placeholder="UUID (optional)"
                    />

                    <span className="acq-field-help">
                      Authority UUID for the responsible
                      acquisition authority.
                    </span>
                  </div>

                  <div className="aakar-form-field">
                    <label>Assigned User ID</label>

                    <input
                      value={
                        createForm.assigned_user_id ??
                        ''
                      }
                      onChange={(event) =>
                        setCreateForm(
                          (
                            current: CreateAcquisitionCaseRequest,
                          ) => ({
                            ...current,
                            assigned_user_id:
                              event.target.value ||
                              null,
                          }),
                        )
                      }
                      placeholder="UUID (optional)"
                    />

                    <span className="acq-field-help">
                      User UUID for the officer responsible
                      for operational handling.
                    </span>
                  </div>
                </div>
              </section>

              <section className="acq-form-section">
                <div className="acq-form-section-heading">
                  <span className="acq-form-section-number">
                    04
                  </span>

                  <div>
                    <h3>Case Description</h3>
                    <p>
                      Add a concise operational note for officers
                      working on the case.
                    </p>
                  </div>
                </div>

                <div className="aakar-form-grid">
                  <div className="aakar-form-field aakar-form-field-wide">
                    <label>Description</label>

                    <textarea
                      value={
                        createForm.description ??
                        ''
                      }
                      onChange={(event) =>
                        setCreateForm(
                          (
                            current: CreateAcquisitionCaseRequest,
                          ) => ({
                            ...current,
                            description:
                              event.target.value,
                          }),
                        )
                      }
                      rows={4}
                      placeholder="Describe the acquisition case, project context or important operational notes."
                    />
                  </div>
                </div>
              </section>
            </div>

            <div className="aakar-modal-actions acq-create-modal-footer">
              <div className="acq-footer-note">
                <span className="acq-footer-dot" />
                Case will be created in <strong>Draft</strong> status.
              </div>

              <div className="acq-footer-actions">
                <button
                  type="button"
                  className="aakar-secondary-button"
                  onClick={() =>
                    setShowCreate(false)
                  }
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="aakar-primary-button"
                >
                  Create Case
                </button>
              </div>
            </div>
          </form>
        </div>
      )}

      {showEdit &&
        selectedCase && (
          <div
            className="aakar-modal-backdrop"
            role="presentation"
            onMouseDown={(event) => {
              if (
                event.target ===
                event.currentTarget
              ) {
                setShowEdit(false);
              }
            }}
          >
            <form
              className="aakar-modal"
              onSubmit={handleUpdate}
            >
              <div className="aakar-modal-header">
                <div>
                  <span className="aakar-eyebrow">
                    EDIT CASE
                  </span>

                  <h2>
                    {
                      selectedCase.case_number
                    }
                  </h2>
                </div>

                <button
                  type="button"
                  className="aakar-icon-button"
                  onClick={() =>
                    setShowEdit(false)
                  }
                  aria-label="Close"
                >
                  ×
                </button>
              </div>

              <div className="aakar-form-grid">
                <div className="aakar-form-field">
                  <label>
                    Legal Framework
                  </label>

                  <select
                    value={
                      editForm.legal_framework
                    }
                    onChange={(event) =>
                      setEditForm(
                        (
                          current: UpdateAcquisitionCaseRequest,
                        ) => ({
                          ...current,
                          legal_framework:
                            event.target
                              .value as AcquisitionCaseLegalFramework,
                        }),
                      )
                    }
                  >
                    {LEGAL_FRAMEWORK_OPTIONS.map(
                      (framework) => (
                        <option
                          key={framework}
                          value={framework}
                        >
                          {humanize(
                            framework,
                          )}
                        </option>
                      ),
                    )}
                  </select>
                </div>

                <div className="aakar-form-field">
                  <label>
                    Legal Route
                  </label>

                  <select
                    value={
                      editForm.legal_route ??
                      ''
                    }
                    onChange={(event) =>
                      setEditForm(
                        (
                          current: UpdateAcquisitionCaseRequest,
                        ) => ({
                          ...current,
                          legal_route:
                            (
                              event.target
                                .value ||
                              null
                            ) as
                              | AcquisitionCaseLegalRoute
                              | null,
                        }),
                      )
                    }
                  >
                    <option value="">
                      None
                    </option>

                    {LEGAL_ROUTE_OPTIONS.map(
                      (route) => (
                        <option
                          key={route}
                          value={route}
                        >
                          {humanize(route)}
                        </option>
                      ),
                    )}
                  </select>
                </div>

                <div className="aakar-form-field">
                  <label>
                    Acquisition Method
                  </label>

                  <select
                    value={
                      editForm.acquisition_method
                    }
                    onChange={(event) =>
                      setEditForm(
                        (
                          current: UpdateAcquisitionCaseRequest,
                        ) => ({
                          ...current,
                          acquisition_method:
                            event.target
                              .value as AcquisitionCaseAcquisitionMethod,
                        }),
                      )
                    }
                  >
                    {ACQUISITION_METHOD_OPTIONS.map(
                      (method) => (
                        <option
                          key={method}
                          value={method}
                        >
                          {humanize(
                            method,
                          )}
                        </option>
                      ),
                    )}
                  </select>
                </div>

                <div className="aakar-form-field">
                  <label>
                    Responsible Authority ID
                  </label>

                  <input
                    value={
                      editForm.responsible_authority_id ??
                      ''
                    }
                    onChange={(event) =>
                      setEditForm(
                        (
                          current: UpdateAcquisitionCaseRequest,
                        ) => ({
                          ...current,
                          responsible_authority_id:
                            event.target.value ||
                            null,
                        }),
                      )
                    }
                    placeholder="UUID (optional)"
                  />
                </div>

                <div className="aakar-form-field">
                  <label>
                    Assigned User ID
                  </label>

                  <input
                    value={
                      editForm.assigned_user_id ??
                      ''
                    }
                    onChange={(event) =>
                      setEditForm(
                        (
                          current: UpdateAcquisitionCaseRequest,
                        ) => ({
                          ...current,
                          assigned_user_id:
                            event.target.value ||
                            null,
                        }),
                      )
                    }
                    placeholder="UUID (optional)"
                  />
                </div>

                <div className="aakar-form-field aakar-form-field-wide">
                  <label>
                    Description
                  </label>

                  <textarea
                    value={
                      editForm.description ??
                      ''
                    }
                    onChange={(event) =>
                      setEditForm(
                        (
                          current: UpdateAcquisitionCaseRequest,
                        ) => ({
                          ...current,
                          description:
                            event.target.value,
                        }),
                      )
                    }
                    rows={4}
                  />
                </div>
              </div>

              <div className="aakar-modal-actions">
                <button
                  type="button"
                  className="aakar-secondary-button"
                  onClick={() =>
                    setShowEdit(false)
                  }
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="aakar-primary-button"
                >
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        )}
    </section>
  );
}