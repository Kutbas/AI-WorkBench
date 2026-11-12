/** 后端 API 封装：token 注入、401 统一跳登录、错误信息提取。 */

const TOKEN_KEY = 'aiwb_token'

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) ?? ''
}

export function setToken(token: string): void {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  const token = getToken()
  if (token) headers.set('X-Auth-Token', token)
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const resp = await fetch(path, { ...options, headers })
  if (resp.status === 401) {
    // 登录接口的 401 自带"口令错误"等后端信息，优先透出
    let detail = '未授权，请先登录'
    try {
      const data = (await resp.json()) as { detail?: string }
      if (data?.detail) detail = String(data.detail)
    } catch {
      /* 非 JSON 错误体 */
    }
    setToken('')
    window.dispatchEvent(new CustomEvent('aiwb:unauthorized'))
    throw new ApiError(detail, 401)
  }
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`
    try {
      const data = (await resp.json()) as { detail?: string }
      if (data?.detail) detail = String(data.detail)
    } catch {
      /* 非 JSON 错误体，保留默认信息 */
    }
    throw new ApiError(detail, resp.status)
  }
  return (await resp.json()) as T
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) => request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
  postForm: <T>(path: string, form: FormData) => request<T>(path, { method: 'POST', body: form }),
}

// ---------- 类型 ----------

export interface ImageGenTask {
  name: string
  status: 'pending' | 'running' | 'done' | 'failed' | 'interrupted'
  error: string | null
  images?: { filename: string; cos_url?: string; cos_key?: string; upload_error?: string }[]
}

/** SoMark 子任务在 ImageGenTask 基础上多两个结果字段 */
export type SoMarkTask = ImageGenTask & { stem?: string; stats?: Record<string, number> }

export interface Job {
  id: string
  type: 'imagegen' | 'somark'
  status: 'running' | 'done' | 'partial' | 'failed' | 'interrupted'
  created_at: string
  params: Record<string, unknown>
  tasks: SoMarkTask[]
}

export interface AppConfig {
  dmxapi: { base_url: string; api_key: string }
  imagegen: {
    model: string
    size: string
    quality: string
    n: number
    output_format: string
    moderation: string
    background: string
  }
  cos: { secret_id: string; secret_key: string; bucket: string; region: string; prefix: string }
  access_token: string
}
