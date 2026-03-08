import Cookies from 'js-cookie'

function authHeaders(json = true): Record<string, string> {
  const token = Cookies.get('access_token')
  return {
    ...(json ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    const detail = (body as { detail?: unknown }).detail
    const message =
      typeof detail === 'string'
        ? detail
        : typeof detail === 'object' && detail !== null && 'message' in detail
          ? String((detail as { message: unknown }).message)
          : res.statusText
    const err = new Error(message) as Error & { status: number; body: unknown }
    err.status = res.status
    err.body = body
    throw err
  }
  if (res.status === 204 || res.headers.get('content-length') === '0') {
    return undefined as T
  }
  return res.json() as Promise<T>
}

export const api = {
  get<T>(path: string): Promise<T> {
    return fetch(path, { headers: authHeaders() }).then((r) => handleResponse<T>(r))
  },

  post<T>(path: string, body?: unknown): Promise<T> {
    return fetch(path, {
      method: 'POST',
      headers: authHeaders(body !== undefined && !(body instanceof FormData)),
      body:
        body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
    }).then((r) => handleResponse<T>(r))
  },

  uploadRecipeImage<T>(path: string, file: File): Promise<T> {
    const form = new FormData()
    form.append('file', file)
    return this.post<T>(path, form)
  },

  put<T>(path: string, body?: unknown): Promise<T> {
    return fetch(path, {
      method: 'PUT',
      headers: authHeaders(),
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }).then((r) => handleResponse<T>(r))
  },

  delete<T>(path: string): Promise<T> {
    return fetch(path, { method: 'DELETE', headers: authHeaders() }).then((r) =>
      handleResponse<T>(r),
    )
  },
}
