import { request } from './http'

export interface User {
  id: number
  username: string
  first_name: string
  last_name: string
  email: string
}

export function login(username: string, password: string): Promise<User> {
  return request<User>('/api/auth/login/', { method: 'POST', body: { username, password } })
}

export function logout(): Promise<void> {
  return request('/api/auth/logout/', { method: 'POST' })
}

/** The signed-in user. A 401 here just means "nobody is signed in". */
export function fetchMe(): Promise<User> {
  return request<User>('/api/auth/me/', { notifyUnauthorized: false })
}

export function changePassword(oldPassword: string, newPassword: string): Promise<void> {
  return request('/api/auth/password/', {
    method: 'POST',
    body: { old_password: oldPassword, new_password: newPassword },
  })
}
