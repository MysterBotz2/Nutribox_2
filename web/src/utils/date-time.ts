export function formatLocalDateTime(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

export function localDateInputValue(value = new Date()): string {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function dateFromInput(value: string): Date {
  return new Date(`${value}T12:00:00`)
}

export function mondayForDate(value: string): string {
  const date = dateFromInput(value)
  date.setDate(date.getDate() - ((date.getDay() + 6) % 7))
  return localDateInputValue(date)
}

export function shiftWeek(weekStart: string, days: number): string {
  const date = dateFromInput(weekStart)
  date.setDate(date.getDate() + days)
  return localDateInputValue(date)
}
