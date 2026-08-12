import type { NutrientTotals as NutrientTotalsType } from '../api/types'
import { formatNutrient, nutrientLabels, type NutrientKey } from '../utils/format-nutrition'

const nutrientKeys: NutrientKey[] = ['calories', 'protein_g', 'carbohydrates_g', 'fat_g', 'fiber_g']

export function NutrientTotals({ totals }: { totals: NutrientTotalsType }) {
  return <dl className="nutrient-grid">
    {nutrientKeys.map((key) => <div key={key}><dt>{nutrientLabels[key]}</dt><dd>{formatNutrient(key, totals[key])}</dd></div>)}
  </dl>
}
