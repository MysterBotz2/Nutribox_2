import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { progressApi } from '../api/progress'
import { queryKeys } from '../api/query-keys'
import { DailyNutritionChart } from '../components/DailyNutritionChart'
import { NutrientTotals } from '../components/NutrientTotals'
import { StateMessage } from '../components/StateMessage'
import { TargetComparison } from '../components/TargetComparison'
import { localDateInputValue, mondayForDate, shiftWeek } from '../utils/date-time'
import { getBrowserTimezone } from '../utils/timezone'

const timezone = getBrowserTimezone()
const summaryOptions = [7, 30, 90]

export function ProgressPage() {
  const [selectedDate, setSelectedDate] = useState(localDateInputValue())
  const [weekStart, setWeekStart] = useState(mondayForDate(selectedDate))
  const [days, setDays] = useState(30)
  const today = useQuery({ queryKey: queryKeys.todayProgress(timezone), queryFn: () => progressApi.getToday(timezone) })
  const daily = useQuery({ queryKey: queryKeys.dailyProgress(selectedDate, timezone), queryFn: () => progressApi.getDaily(selectedDate, timezone) })
  const weekly = useQuery({ queryKey: queryKeys.weeklyProgress(weekStart, timezone), queryFn: () => progressApi.getWeekly(weekStart, timezone) })
  const summary = useQuery({ queryKey: queryKeys.progressSummary(days, timezone), queryFn: () => progressApi.getSummary(days, timezone) })
  const targets = useQuery({ queryKey: queryKeys.targetStatus(timezone), queryFn: () => progressApi.getTargetStatus(timezone) })
  return <div className="page-stack"><header className="page-header"><p className="eyebrow">Progress</p><h1>Nutrition progress</h1><p className="muted">Backend-authoritative analytics · {timezone}</p></header>
    <section className="card"><h2>Today</h2>{today.isPending ? <StateMessage>Loading today’s progress…</StateMessage> : today.isError ? <StateMessage kind="error">Unable to load today’s progress.</StateMessage> : <><p>{today.data.date} · {today.data.meal_count} meals recorded</p><NutrientTotals totals={today.data.totals} /></>}</section>
    <section className="card"><div className="section-heading"><div><h2>Daily progress</h2><p>View a requested local calendar date.</p></div><label className="compact-label">Date<input type="date" value={selectedDate} onChange={(event) => { setSelectedDate(event.target.value); setWeekStart(mondayForDate(event.target.value)) }} /></label></div>{daily.isPending ? <StateMessage>Loading daily progress…</StateMessage> : daily.isError ? <StateMessage kind="error">Unable to load daily progress.</StateMessage> : <><p>{daily.data.meal_count} meals recorded on {daily.data.date}</p><NutrientTotals totals={daily.data.totals} /></>}</section>
    <section className="card"><div className="section-heading"><div><h2>Weekly progress</h2><p>Monday through Sunday · {weekStart}</p></div><div className="inline-actions"><button type="button" className="secondary-button" aria-label="Previous week" onClick={() => setWeekStart(shiftWeek(weekStart, -7))}>Previous</button><button type="button" aria-label="Next week" onClick={() => setWeekStart(shiftWeek(weekStart, 7))}>Next</button></div></div>{weekly.isPending ? <StateMessage>Loading weekly progress…</StateMessage> : weekly.isError ? <StateMessage kind="error">Unable to load weekly progress.</StateMessage> : <><p>{weekly.data.week_start} to {weekly.data.week_end} · {weekly.data.meal_count} meals recorded</p><NutrientTotals totals={weekly.data.totals} /><DailyNutritionChart daily={weekly.data.daily} /></>}</section>
    <section className="card"><div className="section-heading"><div><h2>Rolling summary</h2><p>Daily average is supplied by the backend across all calendar days in the selected period.</p></div><label className="compact-label">Period<select value={days} onChange={(event) => setDays(Number(event.target.value))}>{summaryOptions.map((option) => <option value={option} key={option}>{option} days</option>)}</select></label></div>{summary.isPending ? <StateMessage>Loading rolling summary…</StateMessage> : summary.isError ? <StateMessage kind="error">Unable to load rolling summary.</StateMessage> : <><p>{summary.data.period_start} to {summary.data.period_end} · {summary.data.meal_count} meals · {summary.data.days_with_meals} days with meals</p><h3>Total</h3><NutrientTotals totals={summary.data.totals} /><h3>Daily average</h3><NutrientTotals totals={summary.data.daily_average} /><DailyNutritionChart daily={summary.data.daily} /></>}</section>
    <section className="card"><h2>Configured target comparison</h2>{targets.isPending ? <StateMessage>Loading target comparison…</StateMessage> : targets.isError ? <StateMessage kind="error">Unable to load target comparison.</StateMessage> : <TargetComparison status={targets.data} />}</section>
  </div>
}
