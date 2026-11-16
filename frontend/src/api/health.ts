export interface Health {
  status: string
  database: {
    vendor: string
    name: string
    version: string
  }
}

export async function fetchHealth(): Promise<Health> {
  const response = await fetch('/api/health/')
  if (!response.ok) {
    throw new Error(`API responded with HTTP ${response.status}`)
  }
  return response.json()
}
