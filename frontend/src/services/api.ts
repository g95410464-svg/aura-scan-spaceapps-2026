export type Field = { code: string; value: number; unit: string | null; confidence?: number; provenance?: string };
export type Indicator = { code: string; label: string; units: string[] };
export type Device = { id: string; label: string; fields: string[]; required: string[]; indicators: Indicator[] };
export type Source = { id: string; title: string; organization: string; url: string; summary: string; application: string };
export type Capture = { id: string; created_at: string; is_demo: boolean; image_url: string; device_type: string; fields: Field[]; warnings: string[]; recognition: string; engine: string; subject_alias?: string | null };
export type LiveReading = { id: string; session_id: string; capture_id: string; subject_alias: string; device_type: string; is_demo: boolean; created_at: string; readings: Field[]; status: string };
export type LiveFrame = { sequence: number; status: string; count: number; target: number; fields: Field[]; message: string; is_demo: boolean; recording: LiveReading | null; quality?: {width:number;height:number;sharpness:number;brightness:number;bright_fraction?:number}; warnings?:string[] };
export type Measurement = { id: string; capture_id: string; created_at: string; measured_at: string | null; subject_alias: string; device_type: string; is_demo: boolean; readings: Field[]; symptoms: string; assessment: { findings: string[]; next_steps: string[]; limitation: string; trends: { code: string; delta: number; unit: string }[] } };
export type HealthContext = { subject_alias: string; is_demo: boolean; environment: string; sleep_hours: number | null; mood: string; symptoms: string; medical_notes: string; red_flags: string[]; created_at?: string };
export type AssistantMetric = { code: string; label: string; value: number; unit: string; record_id: string; device_type: string; confirmed_at: string; measured_at: string | null; delta: number | null; previous_id: string | null; series: { value: number; confirmed_at: string; measured_at: string | null }[] };
export type AssistantSnapshot = { automatic_readings: LiveReading[]; subject_alias: string; is_demo: boolean; status: string; status_label: string; answer: string; record_count: number; context: HealthContext | null; metrics: AssistantMetric[]; observations: string[]; recommendations: { id: string; title: string; action: string; reason: string; source_ids: string[]; priority: string }[]; missing_data: string[]; timeline: { id: string; kind: string; created_at: string; measured_at?: string | null; title: string; notes: string; medical_notes?: string; sleep_hours?: number | null; mood?: string; environment?: string; red_flags?: string[]; readings?: Field[] }[]; sources: Source[]; limitation: string };
let csrf = '';
export function setCsrf(value: string) { csrf = value; }
let session: Promise<{ csrf: string; expires_at: number }> | null = null;
export function resetSession() { session = null; csrf = ''; }
export function ensureSession() {
  // Share the bootstrap request, including React StrictMode's double mount.
  if (!session) session = request<{ csrf: string; expires_at: number }>('/session')
    .then(result => { setCsrf(result.csrf); return result; })
    .catch(error => { session = null; throw error; });
  return session;
}
export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  if (csrf && options.method && options.method !== 'GET') headers.set('X-CSRF-Token', csrf);
  let response: Response;
  try { response = await fetch(`/api${path}`, { ...options, headers, credentials: 'same-origin' }); }
  catch { throw new Error('No se pudo conectar. Comprueba tu conexión y vuelve a intentarlo.'); }
  if (!response.ok) {
    if (response.status === 401) window.dispatchEvent(new Event('aura-session-expired'));
    const data = await response.json().catch(() => ({}));
    const message = typeof data.detail === 'string' ? data.detail : Array.isArray(data.detail) ? data.detail.map((v: { msg: string }) => v.msg).join(' · ') : 'No se pudo completar la solicitud.';
    throw new Error(message);
  }
  return response.status === 204 ? undefined as T : response.json();
}
