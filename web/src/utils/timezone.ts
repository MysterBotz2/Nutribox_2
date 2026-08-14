const UTC = 'UTC'

export function getBrowserTimezone(): string {
  try {
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone
    return timezone && timezone.trim() ? timezone : UTC
  } catch {
    return UTC
  }
}
