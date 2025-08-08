import { useEffect } from 'react'
import axios from 'axios'
import type { JobStatus } from '../types'

type SetJobStatuses = React.Dispatch<React.SetStateAction<Record<string, JobStatus>>>

export function useJobStatusPolling(setJobStatuses: SetJobStatuses, intervalMs: number = 10000) {
  useEffect(() => {
    let isCancelled = false

    const fetchStatuses = async () => {
      try {
        const response = await axios.get<Record<string, JobStatus>>('/api/status')
        if (!isCancelled) {
          setJobStatuses(response.data)
        }
      } catch (error) {
        // Intentionally ignore errors to keep polling simple
        if (import.meta.env.DEV) {
          console.error('Failed to fetch job statuses', error)
        }
      }
    }

    // initial fetch
    fetchStatuses()

    const id = setInterval(fetchStatuses, intervalMs)
    return () => {
      isCancelled = true
      clearInterval(id)
    }
  }, [setJobStatuses, intervalMs])
}

