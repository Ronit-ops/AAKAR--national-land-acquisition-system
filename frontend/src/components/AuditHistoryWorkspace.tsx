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

  return date.toLocaleString();
}

function formatLabel(value: string): string {
  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatEntityId(value: string | null): string {
  return value ?? '—';
}

interface AuditEventDetailProps {
  event: AuditEvent;
}

function AuditEventDetail({ event }: AuditEventDetailProps) {
  const detailEntries = event.details
    ? Object.entries(event.details)
    : [];

  return (
    <div className="audit-detail-card">
      <div className="audit-panel-heading">
        <div>
          <p className="roles-eyebrow">EVENT DETAILS</p>
          <h2>{formatLabel(event.action)}</h2>
        </div>

        <span
          className={
            event.result === 'success'
              ? 'audit-result audit-result-success'
              : 'audit-result audit-result-error'
          }
        >
          {formatLabel(event.result)}
        </span>
      </div>

      <div className="audit-detail-grid">
        <div className="profile-item">
          <span>Event ID</span>
          <strong>{event.id}</strong>
        </div>

        <div className="profile-item">
          <span>Timestamp</span>
          <strong>{formatDateTime(event.created_at)}</strong>
        </div>

        <div className="profile-item">
          <span>Actor</span>
          <strong>{event.actor_user_id ?? 'System'}</strong>
        </div>

        <div className="profile-item">
          <span>Entity type</span>
          <strong>{formatLabel(event.entity_type)}</strong>
        </div>

        <div className="profile-item">
          <span>Entity ID</span>
          <strong>{formatEntityId(event.entity_id)}</strong>
        </div>

        <div className="profile-item">
          <span>Result</span>
          <strong>{formatLabel(event.result)}</strong>
        </div>
      </div>

      <section className="audit-context-section">
        <div className="audit-panel-heading">
          <div>
            <p className="roles-eyebrow">CONTEXT</p>
            <h3>Event context</h3>
          </div>
        </div>

        {detailEntries.length === 0 ? (
          <div className="audit-no-context">
            No additional context was recorded for this event.
          </div>
        ) : (
          <dl className="audit-context-list">
            {detailEntries.map(([key, value]) => (
              <div className="audit-context-item" key={key}>
                <dt>{formatLabel(key)}</dt>
                <dd>
                  {typeof value === 'object'
                    ? JSON.stringify(value)
                    : String(value)}
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
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [error, setError] = useState('');
  const [detailsError, setDetailsError] = useState('');

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
        new Set(events.map((event) => event.action)),
      ).sort(),
    [events],
  );

  const entityTypeOptions = useMemo(
    () =>
      Array.from(
        new Set(events.map((event) => event.entity_type)),
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
        entity_type: entityType || undefined,
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
          (event) => event.id === selectedEvent.id,
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

  const handleSearchChange = (value: string) => {
    setSearch(value);
    setOffset(0);
    setSelectedEvent(null);
  };

  const handleActionChange = (value: string) => {
    setAction(value);
    setOffset(0);
    setSelectedEvent(null);
  };

  const handleEntityTypeChange = (value: string) => {
    setEntityType(value);
    setOffset(0);
    setSelectedEvent(null);
  };

  const handleResultChange = (value: string) => {
    setResult(value);
    setOffset(0);
    setSelectedEvent(null);
  };

  const handleStartAtChange = (value: string) => {
    setStartAt(value);
    setOffset(0);
    setSelectedEvent(null);
  };

  const handleEndAtChange = (value: string) => {
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

  const handleSelectEvent = async (eventId: string) => {
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

  return (
    <section className="management-shell audit-shell">
      <div className="management-heading">
        <div>
          <p className="roles-eyebrow">
            IDENTITY & ADMINISTRATION
          </p>

          <h1>Audit & Activity History</h1>

          <p>
            Review important AAKAR system actions, actors,
            records, results, and recorded context.
          </p>
        </div>
      </div>

      <section className="audit-filter-card">
        <div className="management-card-heading">
          <div>
            <p className="roles-eyebrow">AUDIT SEARCH</p>
            <h2>Filter activity</h2>
          </div>

          <button
            type="button"
            className="secondary-button"
            onClick={clearFilters}
          >
            Clear filters
          </button>
        </div>

        <div className="audit-filter-grid">
          <label>
            Search

            <input
              type="search"
              placeholder="Search action, entity type, or result..."
              value={search}
              onChange={(event) =>
                handleSearchChange(event.target.value)
              }
            />
          </label>

          <label>
            Action

            <select
              value={action}
              onChange={(event) =>
                handleActionChange(event.target.value)
              }
            >
              <option value="">All actions</option>

              {actionOptions.map((option) => (
                <option value={option} key={option}>
                  {formatLabel(option)}
                </option>
              ))}
            </select>
          </label>

          <label>
            Entity type

            <select
              value={entityType}
              onChange={(event) =>
                handleEntityTypeChange(event.target.value)
              }
            >
              <option value="">All entity types</option>

              {entityTypeOptions.map((option) => (
                <option value={option} key={option}>
                  {formatLabel(option)}
                </option>
              ))}
            </select>
          </label>

          <label>
            Result

            <select
              value={result}
              onChange={(event) =>
                handleResultChange(event.target.value)
              }
            >
              <option value="">All results</option>
              <option value="success">Success</option>
              <option value="error">Error</option>
            </select>
          </label>

          <label className="audit-date-field">
            From

            <input
              type="datetime-local"
              value={startAt}
              onChange={(event) =>
                handleStartAtChange(event.target.value)
              }
            />
          </label>

          <label className="audit-date-field">
            To

            <input
              type="datetime-local"
              value={endAt}
              onChange={(event) =>
                handleEndAtChange(event.target.value)
              }
            />
          </label>
        </div>

        {localDateRangeInvalid && (
          <div className="error-message" role="alert">
            The start date and time must be earlier than or
            equal to the end date and time.
          </div>
        )}
      </section>

      <div className="audit-layout">
        <section className="audit-events-panel">
          <div className="audit-panel-heading">
            <div>
              <p className="roles-eyebrow">ACTIVITY LOG</p>
              <h2>System events</h2>
            </div>

            <div className="audit-summary">
              <span>
                {total} {total === 1 ? 'event' : 'events'}
              </span>

              <span>
                Page {currentPage} of {totalPages}
              </span>
            </div>
          </div>

          {error && (
            <div className="error-message" role="alert">
              {error}
            </div>
          )}

          {loading ? (
            <div className="management-empty-state">
              <strong>Loading audit history...</strong>
              <p>
                Retrieving activity from the secure AAKAR API.
              </p>
            </div>
          ) : events.length === 0 ? (
            <div className="management-empty-state">
              <strong>No audit events found</strong>
              <p>
                Try changing the search text or activity
                filters.
              </p>
            </div>
          ) : (
            <div className="audit-event-list">
              {events.map((event) => {
                const isSelected =
                  selectedEvent?.id === event.id;

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
                      void handleSelectEvent(event.id);
                    }}
                  >
                    <span className="audit-event-indicator" />

                    <span className="audit-event-content">
                      <span className="audit-event-top">
                        <strong
                          className={
                            event.result === 'success'
                              ? 'audit-action audit-action-positive'
                              : 'audit-action audit-action-neutral'
                          }
                        >
                          {formatLabel(event.action)}
                        </strong>

                        <span
                          className={
                            event.result === 'success'
                              ? 'audit-result audit-result-success'
                              : 'audit-result audit-result-error'
                          }
                        >
                          {formatLabel(event.result)}
                        </span>
                      </span>

                      <span className="audit-event-meta">
                        {formatLabel(event.entity_type)}

                        {event.entity_id
                          ? ` · ${event.entity_id}`
                          : ''}
                      </span>

                      <span className="audit-event-entity">
                        {event.actor_user_id
                          ? `Actor: ${event.actor_user_id}`
                          : 'Actor: System'}
                        {' · '}
                        {formatDateTime(event.created_at)}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          )}

          <div className="pagination-controls">
            <button
              type="button"
              className="ghost-button"
              disabled={offset === 0 || loading}
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
                loading ||
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

        <section className="audit-detail-panel">
          {loadingDetails && (
            <div className="management-empty-state">
              <strong>Loading event details...</strong>
              <p>
                Fetching the selected audit event from the
                secure AAKAR API.
              </p>
            </div>
          )}

          {!loadingDetails && detailsError && (
            <div className="error-message" role="alert">
              {detailsError}
            </div>
          )}

          {!loadingDetails &&
            !detailsError &&
            !selectedEvent && (
              <div className="management-empty-state management-empty-state-large">
                <span className="detail-placeholder-icon">
                  A
                </span>

                <strong>Select an audit event</strong>

                <p>
                  Choose an activity record to inspect its
                  actor, entity, result, timestamp, and
                  recorded context.
                </p>
              </div>
            )}

          {!loadingDetails &&
            !detailsError &&
            selectedEvent && (
              <AuditEventDetail event={selectedEvent} />
            )}
        </section>
      </div>

      <div className="authorization-note audit-read-note">
        <span>READ ONLY</span>

        <p>
          Audit history is immutable from this workspace. The
          interface provides read-only access to recorded
          activity; audit events cannot be created, edited, or
          deleted here.
        </p>
      </div>
    </section>
  );
}

export default AuditHistoryWorkspace;