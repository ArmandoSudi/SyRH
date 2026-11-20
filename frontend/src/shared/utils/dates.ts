/** YYYY-MM-DD in local time (toISOString would shift to UTC). */
export function localDate(date: Date): string {
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

/** An ISO date (YYYY-MM-DD) as dd/mm/yyyy; empty values as a dash. */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const [year, month, day] = iso.split('-')
  return `${day}/${month}/${year}`
}

/** An ISO date (YYYY-MM-DD) as a local Date at midnight; empty values as null. */
export function parseDate(iso: string | null | undefined): Date | null {
  if (!iso) return null
  const [year, month, day] = iso.split('-').map(Number)
  return new Date(year!, month! - 1, day!)
}
