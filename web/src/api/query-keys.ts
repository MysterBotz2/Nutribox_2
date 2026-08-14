export const queryKeys = {
  currentUser: ['auth', 'current-user'] as const,
  profile: ['profile'] as const,
  targets: ['targets'] as const,
  todayProgress: (timezone: string) => ['progress', 'today', timezone] as const,
  targetStatus: (timezone: string) => ['progress', 'target-status', timezone] as const,
  recentMeals: ['meals', 'recent'] as const,
  mealsList: (limit: number, offset: number) => ['meals', 'list', limit, offset] as const,
  mealDetail: (mealId: number) => ['meals', 'detail', mealId] as const,
  dailyProgress: (date: string, timezone: string) => ['progress', 'daily', date, timezone] as const,
  weeklyProgress: (weekStart: string, timezone: string) => ['progress', 'weekly', weekStart, timezone] as const,
  progressSummary: (days: number, timezone: string) => ['progress', 'summary', days, timezone] as const,
  scanAnalysis: ['scan', 'analysis'] as const,
}
