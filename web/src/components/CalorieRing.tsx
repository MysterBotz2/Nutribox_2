import type { CSSProperties } from 'react'
import { formatNutrient } from '../utils/format-nutrition'

export function CalorieRing({ calories, target }: { calories: string; target: string | null | undefined }) {
  const consumed = Number(calories); const goal = target === null || target === undefined ? null : Number(target)
  const progress = goal && goal > 0 ? Math.min(100, Math.max(0, consumed / goal * 100)) : 0
  const remaining = goal === null ? null : Math.max(0, goal - consumed)
  return <div className="calorie-ring" style={{ '--ring-angle': `${progress * 3.6}deg` } as CSSProperties}><div className="calorie-ring-center"><strong>{goal === null ? formatNutrient('calories', calories) : formatNutrient('calories', String(remaining))}</strong><span>{goal === null ? 'kcal recorded' : 'kcal left'}</span></div></div>
}
