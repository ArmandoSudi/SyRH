import type { AuditAction } from '@/features/audit/api/audit'

const dateTime = new Intl.DateTimeFormat('fr-FR', {
  dateStyle: 'short',
  timeStyle: 'medium',
  timeZone: 'Africa/Kinshasa',
})
const dateOnly = new Intl.DateTimeFormat('fr-FR', { dateStyle: 'short', timeZone: 'UTC' })

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/
const ISO_DATE_TIME = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/

/** Date and time of an entry, in Kinshasa time. */
export function formatDateTime(iso: string): string {
  return dateTime.format(new Date(iso))
}

/** A stored old or new value, as an auditor reads it. */
export function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? 'Oui' : 'Non'
  if (typeof value === 'object' && 'libelle' in value) return String(value.libelle)
  if (typeof value === 'string') {
    if (ISO_DATE.test(value)) return dateOnly.format(new Date(`${value}T00:00:00Z`))
    if (ISO_DATE_TIME.test(value)) return formatDateTime(value)
  }
  return String(value)
}

export const ACTION_SEVERITY: Record<AuditAction, 'success' | 'info' | 'danger'> = {
  creation: 'success',
  modification: 'info',
  suppression: 'danger',
}

export const ACTION_OPTIONS: { value: AuditAction; label: string }[] = [
  { value: 'creation', label: 'Création' },
  { value: 'modification', label: 'Modification' },
  { value: 'suppression', label: 'Suppression' },
]
