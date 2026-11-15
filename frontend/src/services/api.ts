export type Field = { code: string; value: number; unit: string | null; confidence?: number; provenance?: string };
export type Indicator = { code: string; label: string; units: string[] };
export type Device = { id: string; label: string; fields: string[]; required: string[]; indicators: Indicator[] };
export type Source = { id: string; title: string; organization: string; url: string; summary: string; application: string };
export type Capture = { id: string; created_at: string; is_demo: boolean; image_url: string; device_type: string; fields: Field[]; warnings: string[]; recognition: string; engine: string };
export type Measurement = { id: string; capture_id: string; created_at: string; measured_at: string | null; subject_alias: string; device_type: string; is_demo: boolean; readings: Field[]; symptoms: string; assessment: { findings: string[]; next_steps: string[]; limitation: string; trends: { code: string; delta: number; unit: string }[] } };
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
