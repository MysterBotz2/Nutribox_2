import type { TargetStatusResponse } from '../api/types'
import { formatNutrient, formatPercent, nutrientLabels, type NutrientKey } from '../utils/format-nutrition'

const nutrientKeys: NutrientKey[] = ['calories', 'protein_g', 'carbohydrates_g', 'fat_g', 'fiber_g']

function remainingLabel(key: NutrientKey, value: string | null | undefined): string {
  if (value === null || value === undefined) return 'Not configured'
  return value.startsWith('-') ? `Above configured target by ${formatNutrient(key, value.slice(1))}` : `${formatNutrient(key, value)} remaining`
}

export function TargetComparison({ status }: { status: TargetStatusResponse }) {
  if (!status.targets) return <p className="state-message info">No nutrition targets configured.</p>
  return <div className="target-list">{nutrientKeys.filter((key) => status.targets?.[key] != null).map((key) => {
    const percent = status.percent_of_target?.[key]
    const fill = percent == null ? 0 : Math.min(100, Math.max(0, Number(percent)))
    return <article className="target-row" key={key}><div className="target-row-heading"><h3>{nutrientLabels[key]}</h3><strong>{formatPercent(percent)}</strong></div><p>Consumed: {formatNutrient(key, status.consumed[key])} · Target: {formatNutrient(key, status.targets?.[key])}</p><p>{remainingLabel(key, status.remaining?.[key])}</p><div className="progress-track" aria-label={`${nutrientLabels[key]} target progress`}><div className="progress-fill" style={{ width: `${fill}%` }} /></div></article>
  })}</div>
}
