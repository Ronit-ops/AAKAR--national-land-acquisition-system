import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  getAuditEvent,
  listAuditEvents,
} from '../lib/api';
import type { AuditEvent } from '../types/audit';

const PAGE_SIZE = 25;

function formatDateTime(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return 'Unavailable';
  }

  return date.toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

function formatDate(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return 'Unavailable';
  }

  return date.toLocaleDateString(undefined, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

function formatTime(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return 'Unavailable';
  }

  return date.toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatLabel(value: string): string {
  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatEntityId(value: string | null): string {
  return value ?? '—';
}

function formatContextValue(value: unknown): string {
  if (value === null || value === undefined) {
    return '—';
  }

  if (typeof value === 'object') {
    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return '[Unable to display value]';
    }
  }

  return String(value);
}

function isSuccessfulResult(result: string): boolean {
  return result.toLowerCase() === 'success';
}

interface AuditResultBadgeProps {
  result: string;
}

function AuditResultBadge({
  result,
}: AuditResultBadgeProps) {
  const success = isSuccessfulResult(result);

  return (
    <span
      className={
        success
          ? 'audit-result-badge audit-result-badge-success'
          : 'audit-result-badge audit-result-badge-error'
      }
    >
      <span className="audit-result-dot" />
      {formatLabel(result)}
    </span>
  );
}

interface AuditEventDetailProps {
  event: AuditEvent;
}

function AuditEventDetail({
  event,
}: AuditEventDetailProps) {
  const detailEntries = event.details
    ? Object.entries(event.details)
    : [];

  return (
    <div className="audit-detail-card">
      <div className="audit-detail-header">
        <div className="audit-detail-title-group">
          <span className="audit-detail-icon">
            A
          </span>

          <div>
            <p className="audit-section-label">
              EVENT DETAILS
            </p>

            <h2>
              {formatLabel(event.action)}
            </h2>

            <p className="audit-detail-subtitle">
              {formatLabel(event.entity_type)}
            </p>
          </div>
        </div>

        <AuditResultBadge result={event.result} />
      </div>

      <div className="audit-detail-divider" />

      <div className="audit-detail-grid">
        <div className="audit-detail-field">
          <span>Event ID</span>
          <strong className="audit-mono">
            {event.id}
          </strong>
        </div>

        <div className="audit-detail-field">
          <span>Timestamp</span>
          <strong>
            {formatDateTime(event.created_at)}
          </strong>
        </div>

        <div className="audit-detail-field">
          <span>Actor</span>
          <strong>
            {event.actor_user_id ?? 'System'}
          </strong>
        </div>

        <div className="audit-detail-field">
          <span>Entity type</span>
          <strong>
            {formatLabel(event.entity_type)}
          </strong>
        </div>

        <div className="audit-detail-field">
          <span>Entity ID</span>
          <strong className="audit-mono">
            {formatEntityId(event.entity_id)}
          </strong>
        </div>

        <div className="audit-detail-field">
          <span>Result</span>
          <strong>
            {formatLabel(event.result)}
          </strong>
        </div>
      </div>

      <section className="audit-context-section">
        <div className="audit-context-header">
          <div>
            <p className="audit-section-label">
              RECORDED CONTEXT
            </p>

            <h3>Event context</h3>
          </div>

          <span className="audit-context-count">
            {detailEntries.length}{' '}
            {detailEntries.length === 1
              ? 'field'
              : 'fields'}
          </span>
        </div>

        {detailEntries.length === 0 ? (
          <div className="audit-no-context">
            <div className="audit-no-context-icon">
              —
            </div>

            <div>
              <strong>
                No additional context
              </strong>

              <p>
                This event was recorded without
                additional context fields.
              </p>
            </div>
          </div>
        ) : (
          <dl className="audit-context-list">
            {detailEntries.map(([key, value]) => (
              <div
                className="audit-context-item"
                key={key}
              >
                <dt>
                  {formatLabel(key)}
                </dt>

                <dd>
                  <code>
                    {formatContextValue(value)}
                  </code>
                </dd>
              </div>
            ))}
          </dl>
        )}
      </section>
    </div>
  );
}

function AuditHistoryWorkspace() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [selectedEvent, setSelectedEvent] =
    useState<AuditEvent | null>(null);

  const [search, setSearch] = useState('');
  const [action, setAction] = useState('');
  const [entityType, setEntityType] = useState('');
  const [result, setResult] = useState('');
  const [startAt, setStartAt] = useState('');
  const [endAt, setEndAt] = useState('');

  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);

  const [loading, setLoading] = useState(true);
  const [loadingDetails, setLoadingDetails] =
    useState(false);
  const [error, setError] = useState('');
  const [detailsError, setDetailsError] =
    useState('');

  const totalPages = Math.max(
    1,
    Math.ceil(total / PAGE_SIZE),
  );

  const currentPage =
    Math.floor(offset / PAGE_SIZE) + 1;

  const localDateRangeInvalid = useMemo(() => {
    if (!startAt || !endAt) {
      return false;
    }

    return (
      new Date(startAt).getTime() >
      new Date(endAt).getTime()
    );
  }, [startAt, endAt]);

  const actionOptions = useMemo(
    () =>
      Array.from(
        new Set(
          events.map((event) => event.action),
        ),
      ).sort(),
    [events],
  );

  const entityTypeOptions = useMemo(
    () =>
      Array.from(
        new Set(
          events.map(
            (event) => event.entity_type,
          ),
        ),
      ).sort(),
    [events],
  );

  const loadEvents = useCallback(async () => {
    if (localDateRangeInvalid) {
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await listAuditEvents({
        search: search.trim() || undefined,
        action: action || undefined,
        entity_type:
          entityType || undefined,
        result: result || undefined,
        start_at: startAt
          ? new Date(startAt).toISOString()
          : undefined,
        end_at: endAt
          ? new Date(endAt).toISOString()
          : undefined,
        offset,
        limit: PAGE_SIZE,
      });

      setEvents(response.items);
      setTotal(response.total);

      if (
        selectedEvent &&
        !response.items.some(
          (event) =>
            event.id === selectedEvent.id,
        )
      ) {
        setSelectedEvent(null);
      }
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to load audit history.',
      );
    } finally {
      setLoading(false);
    }
  }, [
    action,
    endAt,
    entityType,
    localDateRangeInvalid,
    offset,
    result,
    search,
    selectedEvent,
    startAt,
  ]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadEvents();
    }, 250);

    return () => {
      window.clearTimeout(timer);
    };
  }, [loadEvents]);

  const handleSearchChange = (
    value: string,
  ) => {
    setSearch(value);
    setOffset(0);
    setSelectedEvent(null);
  };

  const handleActionChange = (
    value: string,
  ) => {
    setAction(value);
    setOffset(0);
    setSelectedEvent(null);
  };

  const handleEntityTypeChange = (
    value: string,
  ) => {
    setEntityType(value);
    setOffset(0);
    setSelectedEvent(null);
  };

  const handleResultChange = (
    value: string,
  ) => {
    setResult(value);
    setOffset(0);
    setSelectedEvent(null);
  };

  const handleStartAtChange = (
    value: string,
  ) => {
    setStartAt(value);
    setOffset(0);
    setSelectedEvent(null);
  };

  const handleEndAtChange = (
    value: string,
  ) => {
    setEndAt(value);
    setOffset(0);
    setSelectedEvent(null);
  };

  const clearFilters = () => {
    setSearch('');
    setAction('');
    setEntityType('');
    setResult('');
    setStartAt('');
    setEndAt('');
    setOffset(0);
    setSelectedEvent(null);
    setDetailsError('');
  };

  const handleSelectEvent = async (
    eventId: string,
  ) => {
    setSelectedEvent(null);
    setDetailsError('');
    setLoadingDetails(true);

    try {
      const event = await getAuditEvent(eventId);
      setSelectedEvent(event);
    } catch (requestError) {
      setDetailsError(
        requestError instanceof Error
          ? requestError.message
          : 'Unable to load audit event details.',
      );
    } finally {
      setLoadingDetails(false);
    }
  };

  const hasActiveFilters =
    Boolean(search) ||
    Boolean(action) ||
    Boolean(entityType) ||
    Boolean(result) ||
    Boolean(startAt) ||
    Boolean(endAt);

  return (
    <section className="management-shell audit-shell">
      <div className="audit-page-header">
        <div>
          <p className="audit-section-label">
            IDENTITY & ADMINISTRATION
          </p>

          <h1>
            Audit & Activity History
          </h1>

          <p className="audit-page-description">
            Review important AAKAR system actions,
            actors, records, results, and recorded
            context.
          </p>
        </div>

        <div className="audit-readonly-badge">
          <span className="audit-readonly-dot" />
          Read only
        </div>
      </div>

      <div className="audit-stat-row">
        <div className="audit-stat-card">
          <span className="audit-stat-label">
            TOTAL EVENTS
          </span>

          <strong>
            {total.toLocaleString()}
          </strong>

          <span>
            Recorded system activity
          </span>
        </div>

        <div className="audit-stat-card">
          <span className="audit-stat-label">
            CURRENT PAGE
          </span>

          <strong>
            {currentPage}
            <small>
              {' '}
              / {totalPages}
            </small>
          </strong>

          <span>
            {PAGE_SIZE} events per page
          </span>
        </div>

        <div className="audit-stat-card audit-stat-card-muted">
          <span className="audit-stat-label">
            AUDIT MODE
          </span>

          <strong>
            Immutable
          </strong>

          <span>
            Records cannot be changed here
          </span>
        </div>
      </div>

      <section className="audit-filter-card">
        <div className="audit-filter-header">
          <div>
            <p className="audit-section-label">
              AUDIT SEARCH
            </p>

            <h2>
              Filter activity
            </h2>
          </div>

          {hasActiveFilters && (
            <button
              type="button"
              className="audit-clear-button"
              onClick={clearFilters}
            >
              Clear filters
            </button>
          )}
        </div>

        <div className="audit-filter-grid">
          <label className="audit-search-field">
            <span>Search activity</span>

            <div className="audit-input-wrapper">
              <span className="audit-input-icon">
                ⌕
              </span>

              <input
                type="search"
                placeholder="Search action, entity type, or result..."
                value={search}
                onChange={(event) =>
                  handleSearchChange(
                    event.target.value,
                  )
                }
              />
            </div>
          </label>

          <label>
            <span>Action</span>

            <select
              value={action}
              onChange={(event) =>
                handleActionChange(
                  event.target.value,
                )
              }
            >
              <option value="">
                All actions
              </option>

              {actionOptions.map((option) => (
                <option
                  value={option}
                  key={option}
                >
                  {formatLabel(option)}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span>Entity type</span>

            <select
              value={entityType}
              onChange={(event) =>
                handleEntityTypeChange(
                  event.target.value,
                )
              }
            >
              <option value="">
                All entity types
              </option>

              {entityTypeOptions.map(
                (option) => (
                  <option
                    value={option}
                    key={option}
                  >
                    {formatLabel(option)}
                  </option>
                ),
              )}
            </select>
          </label>

          <label>
            <span>Result</span>

            <select
              value={result}
              onChange={(event) =>
                handleResultChange(
                  event.target.value,
                )
              }
            >
              <option value="">
                All results
              </option>

              <option value="success">
                Success
              </option>

              <option value="error">
                Error
              </option>
            </select>
          </label>

          <label className="audit-date-field">
            <span>From</span>

            <input
              type="datetime-local"
              value={startAt}
              onChange={(event) =>
                handleStartAtChange(
                  event.target.value,
                )
              }
            />
          </label>

          <label className="audit-date-field">
            <span>To</span>

            <input
              type="datetime-local"
              value={endAt}
              onChange={(event) =>
                handleEndAtChange(
                  event.target.value,
                )
              }
            />
          </label>
        </div>

        {localDateRangeInvalid && (
          <div
            className="audit-validation-message"
            role="alert"
          >
            <strong>
              Invalid date range
            </strong>

            <span>
              The start date and time must be earlier
              than or equal to the end date and time.
            </span>
          </div>
        )}
      </section>

      <div className="audit-layout">
        <section className="audit-events-panel">
          <div className="audit-panel-heading">
            <div>
              <p className="audit-section-label">
                ACTIVITY LOG
              </p>

              <h2>
                System events
              </h2>
            </div>

            <span className="audit-event-count">
              {total.toLocaleString()}{' '}
              {total === 1
                ? 'event'
                : 'events'}
            </span>
          </div>

          {error && (
            <div
              className="audit-error-state"
              role="alert"
            >
              <strong>
                Unable to load audit history
              </strong>

              <p>{error}</p>
            </div>
          )}

          {loading ? (
            <div className="audit-loading-state">
              <div className="audit-loading-spinner" />

              <strong>
                Loading audit history
              </strong>

              <p>
                Retrieving activity from the secure
                AAKAR API.
              </p>
            </div>
          ) : events.length === 0 ? (
            <div className="audit-empty-state">
              <div className="audit-empty-icon">
                A
              </div>

              <strong>
                No audit events found
              </strong>

              <p>
                Try changing your search text or
                activity filters.
              </p>

              {hasActiveFilters && (
                <button
                  type="button"
                  className="audit-clear-button"
                  onClick={clearFilters}
                >
                  Clear filters
                </button>
              )}
            </div>
          ) : (
            <div className="audit-event-list">
              {events.map((event) => {
                const isSelected =
                  selectedEvent?.id ===
                  event.id;

                return (
                  <button
                    type="button"
                    key={event.id}
                    className={
                      isSelected
                        ? 'audit-event-item audit-event-item-active'
                        : 'audit-event-item'
                    }
                    onClick={() => {
                      void handleSelectEvent(
                        event.id,
                      );
                    }}
                  >
                    <span className="audit-event-indicator">
                      <span />
                    </span>

                    <span className="audit-event-content">
                      <span className="audit-event-top">
                        <strong className="audit-action">
                          {formatLabel(
                            event.action,
                          )}
                        </strong>

                        <AuditResultBadge
                          result={event.result}
                        />
                      </span>

                      <span className="audit-event-middle">
                        <span>
                          {formatLabel(
                            event.entity_type,
                          )}
                        </span>

                        {event.entity_id && (
                          <>
                            <span className="audit-meta-separator">
                              •
                            </span>

                            <span className="audit-mono">
                              {event.entity_id}
                            </span>
                          </>
                        )}
                      </span>

                      <span className="audit-event-bottom">
                        <span>
                          {event.actor_user_id
                            ? `Actor · ${event.actor_user_id}`
                            : 'Actor · System'}
                        </span>

                        <span className="audit-meta-separator">
                          •
                        </span>

                        <span>
                          {formatDate(
                            event.created_at,
                          )}
                        </span>

                        <span>
                          {formatTime(
                            event.created_at,
                          )}
                        </span>
                      </span>
                    </span>

                    <span className="audit-event-chevron">
                      →
                    </span>
                  </button>
                );
              })}
            </div>
          )}

          <div className="audit-pagination">
            <div>
              <span>
                Showing{' '}
                <strong>
                  {total === 0
                    ? 0
                    : offset + 1}
                </strong>{' '}
               –{' '}
                <strong>
                  {Math.min(
                    offset + PAGE_SIZE,
                    total,
                  )}
                </strong>{' '}
                of{' '}
                <strong>
                  {total.toLocaleString()}
                </strong>
              </span>
            </div>

            <div className="audit-pagination-actions">
              <button
                type="button"
                className="audit-pagination-button"
                disabled={
                  offset === 0 ||
                  loading
                }
                onClick={() =>
                  setOffset(
                    (currentOffset) =>
                      Math.max(
                        0,
                        currentOffset -
                          PAGE_SIZE,
                      ),
                  )
                }
              >
                ← Previous
              </button>

              <span className="audit-page-indicator">
                {currentPage} / {totalPages}
              </span>

              <button
                type="button"
                className="audit-pagination-button"
                disabled={
                  offset + PAGE_SIZE >=
                    total ||
                  loading ||
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
                Next →
              </button>
            </div>
          </div>
        </section>

        <section className="audit-detail-panel">
          {loadingDetails && (
            <div className="audit-loading-state audit-detail-loading">
              <div className="audit-loading-spinner" />

              <strong>
                Loading event details
              </strong>

              <p>
                Fetching the selected audit event.
              </p>
            </div>
          )}

          {!loadingDetails &&
            detailsError && (
              <div
                className="audit-error-state"
                role="alert"
              >
                <strong>
                  Unable to load event details
                </strong>

                <p>
                  {detailsError}
                </p>
              </div>
            )}

          {!loadingDetails &&
            !detailsError &&
            !selectedEvent && (
              <div className="audit-detail-placeholder">
                <div className="audit-placeholder-icon">
                  A
                </div>

                <p className="audit-section-label">
                  EVENT INSPECTOR
                </p>

                <strong>
                  Select an audit event
                </strong>

                <p>
                  Choose an activity record to inspect
                  its actor, entity, result, timestamp,
                  and recorded context.
                </p>
              </div>
            )}

          {!loadingDetails &&
            !detailsError &&
            selectedEvent && (
              <AuditEventDetail
                event={selectedEvent}
              />
            )}
        </section>
      </div>

      <div className="audit-readonly-note">
        <div className="audit-readonly-note-icon">
          ✓
        </div>

        <div>
          <strong>
            Read-only audit record
          </strong>

          <p>
            Audit history is immutable from this
            workspace. Recorded events cannot be
            created, edited, or deleted here.
          </p>
        </div>
      </div>
    </section>
  );
}

export default AuditHistoryWorkspace;