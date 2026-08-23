import { formatNutrient, nutrientLabels, type NutrientKey } from '../utils/format-nutrition'

type Macro = Extract<NutrientKey, 'protein_g' | 'carbohydrates_g' | 'fat_g'>
export function MacroBar({ nutrient, value, target }: { nutrient: Macro; value: string; target: string | null | undefined }) {
  const targetNumber = target === null || target === undefined ? null : Number(target)
  const progress = targetNumber && targetNumber > 0 ? Math.min(100, Number(value) / targetNumber * 100) : 0
  return <div className={`macro-bar macro-${nutrient}`}><div><span>{nutrientLabels[nutrient]}</span><strong>{formatNutrient(nutrient, value)}</strong></div><div className="macro-track"><i style={{ width: `${progress}%` }} /></div></div>
}
