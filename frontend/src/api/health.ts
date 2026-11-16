import { request } from './http'

export interface Health {
  status: string
  database: {
    vendor: string
    name: string
    version: string
  }
}

export function fetchHealth(): Promise<Health> {
  return request<Health>('/api/health/')
}
