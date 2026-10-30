/**
 * 统一请求封装
 * ------------------------------------------------------------
 * 教材和第一课背词接口始终调用后端。
 * 仿写与报告仍通过 USE_MOCK 使用演示数据。
 */

import type { ApiResult } from '@/types'

/** 尚未接入后端的仿写和报告模块使用演示数据。 */
export const USE_MOCK = true

/** 后端基地址，来自 .env 的 VITE_API_BASE，默认同源 /api */
export const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'

/** 请求失败时抛出，视图层统一 catch 后展示 */
export class ApiError extends Error {
  constructor(
    public code: number | string,
    message: string,
    public status?: number
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/**
 * 发起请求并解包 ApiResult<T>
 * @example const data = await http<Mainline>('/study/mainline')
 */
export async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  if (init?.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  })

  const payload = (await res.json().catch(() => null)) as ApiResult<T> | null
  if (!res.ok) {
    throw new ApiError(
      payload?.code ?? res.status,
      payload?.message ?? `请求失败：${res.status} ${res.statusText}`,
      res.status
    )
  }

  if (!payload) throw new ApiError(res.status, '后端返回了无法读取的数据')
  if (payload.code !== 0) throw new ApiError(payload.code, payload.message)
  return payload.data
}

/**
 * mock 分支的统一包装：模拟网络延迟（150ms），
 * 让加载态在开发阶段就能被看到，避免上线后才发现没做 loading。
 */
export async function mockDelay<T>(data: T, ms = 150): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(data), ms))
}

/** 简易深拷贝，避免组件直接改到 mock 常量 */
export function clone<T>(data: T): T {
  return JSON.parse(JSON.stringify(data)) as T
}
