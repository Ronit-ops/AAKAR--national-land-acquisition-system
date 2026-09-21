export interface AuditEvent {
  id: string;
  actor_user_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  result: string;
  details: Record<string, unknown> | null;
  created_at: string;
}

export interface AuditEventListResponse {
  items: AuditEvent[];
  total: number;
  offset: number;
  limit: number;
}