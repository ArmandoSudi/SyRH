/** How the blank rules of a suspension type read on screen (exit reasons D21). */

export function dureeLibelle(mois: number | null): string {
  return mois === null ? 'Fixée par la décision' : `${mois} mois`
}

export function renouvellementsLibelle(nombre: number | null): string {
  return nombre === null ? 'Sans limite' : String(nombre)
}
