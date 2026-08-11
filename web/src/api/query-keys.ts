export const queryKeys = {
  currentUser: ['auth', 'current-user'] as const,
  profile: ['profile'] as const,
  targets: ['targets'] as const,
  todayProgress: (timezone: string) => ['progress', 'today', timezone] as const,
  targetStatus: (timezone: string) => ['progress', 'target-status', timezone] as const,
  recentMeals: ['meals', 'recent'] as const,
}
