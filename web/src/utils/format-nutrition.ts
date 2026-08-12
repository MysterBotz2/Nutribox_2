export type NutrientKey = 'calories' | 'protein_g' | 'carbohydrates_g' | 'fat_g' | 'fiber_g'

export const nutrientLabels: Record<NutrientKey, string> = {
  calories: 'Calories',
  protein_g: 'Protein',
  carbohydrates_g: 'Carbohydrates',
  fat_g: 'Fat',
  fiber_g: 'Fiber',
}

export const nutrientUnits: Record<NutrientKey, string> = {
  calories: 'kcal',
  protein_g: 'g',
  carbohydrates_g: 'g',
  fat_g: 'g',
  fiber_g: 'g',
}

export function formatDecimal(value: string | null | undefined): string {
  if (value === null || value === undefined) return 'Not configured'
  const normalized = value.replace(/(\.\d*?[1-9])0+$|\.0+$/, '$1')
  return normalized === '-0' ? '0' : normalized
}

export function formatNutrient(key: NutrientKey, value: string | null | undefined): string {
  const formatted = formatDecimal(value)
  return formatted === 'Not configured' ? formatted : `${formatted} ${nutrientUnits[key]}`
}

export function formatPercent(value: string | null | undefined): string {
  return value === null || value === undefined ? 'Not configured' : `${formatDecimal(value)}%`
}

export function humanize(value: string): string {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}
