'use client'

/**
 * Returns the active runtime environment name and indicator.
 * Displays 'LOCAL' or 'DEVELOPMENT' when running on localhost / dev instances,
 * reserving 'PROD' strictly for genuine remote production deployments.
 *
 * NOTE: Hostname inspection is strictly a presentation label control and is NEVER
 * used as an authorization or access control mechanism.
 */
export function getRuntimeEnvironment(): {
  name: string
  isProd: boolean
} {
  if (typeof window !== 'undefined') {
    const host = window.location.hostname.toLowerCase()
    // Local development addresses (standalone or containerized)
    if (
      host === 'localhost' ||
      host === '127.0.0.1' ||
      host === '0.0.0.0' ||
      host === 'host.docker.internal' ||
      host.endsWith('.local') ||
      host.startsWith('192.168.') ||
      host.startsWith('10.') ||
      host.startsWith('172.')
    ) {
      return {
        name: 'LOCAL',
        isProd: false
      }
    }
  }

  const envVar = (process.env.NEXT_PUBLIC_ENVIRONMENT || '').trim().toUpperCase()
  if (envVar === 'PRODUCTION' || envVar === 'PROD') {
    return { name: 'PROD', isProd: true }
  }
  if (envVar === 'STAGING') {
    return { name: 'STAGING', isProd: false }
  }

  return { name: 'LOCAL', isProd: false }
}
