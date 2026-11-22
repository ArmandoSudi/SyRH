import type { Unite } from '@/features/referentiels/api/referentiels'

export interface NoeudUnite {
  key: string
  label: string
  data: number
  children?: NoeudUnite[]
}

/** The units open on a day as a tree for the Service filter (agent list D12). */
export function arbreUnites(unites: Unite[]): NoeudUnite[] {
  const ids = new Set(unites.map((u) => u.id))
  const byParent = new Map<number | null, Unite[]>()
  for (const unite of unites) {
    const parent = unite.parent !== null && ids.has(unite.parent) ? unite.parent : null
    byParent.set(parent, [...(byParent.get(parent) ?? []), unite])
  }
  const build = (parent: number | null): NoeudUnite[] =>
    (byParent.get(parent) ?? [])
      .sort((a, b) => a.code.localeCompare(b.code))
      .map((unite) => {
        const children = build(unite.id)
        return {
          key: String(unite.id),
          label: `${unite.code} — ${unite.nom}`,
          data: unite.id,
          ...(children.length ? { children } : {}),
        }
      })
  return build(null)
}
