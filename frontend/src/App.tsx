import { useState, useEffect } from 'react'
import { Activity } from 'lucide-react'
import axios from 'axios'
import { HealthStatus } from './components/HealthStatus'
import { FileUpload } from './components/FileUpload'
import { JobTable } from './components/JobTable'
import type { HealthStatus as HealthStatusType, JobStatus, UploadResult } from './types'
import { useJobStatusPolling } from './hooks/useJobStatusPolling'

function App() {
  const [files, setFiles] = useState<File[]>([])
  // Map job_id -> filename for display purposes (in-memory only)
  const [jobIdToFilename, setJobIdToFilename] = useState<Record<string, string>>({})
  const [jobStatuses, setJobStatuses] = useState<Record<string, JobStatus>>({})
  const [isUploading, setIsUploading] = useState(false)
  const [healthStatus, setHealthStatus] = useState<HealthStatusType | null>(null)
  const [isCheckingHealth, setIsCheckingHealth] = useState(true)

  // Health check effect
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await axios.get('/api/health')
        setHealthStatus(response.data)
      } catch {
        setHealthStatus({
          status: 'unhealthy',
          ollama_available: false,
          message: 'Failed to connect to backend server'
        })
      } finally {
        setIsCheckingHealth(false)
      }
    }

    checkHealth()
    
    // Check health every 30 seconds
    const interval = setInterval(checkHealth, 30000)
    
    return () => clearInterval(interval)
  }, [])

  // Poll job statuses every 30s
  useJobStatusPolling(setJobStatuses, 30000)

  // Trim filename mapping to known job IDs from status
  useEffect(() => {
    setJobIdToFilename(prev => {
      const next: Record<string, string> = {}
      for (const jobId of Object.keys(jobStatuses)) {
        if (prev[jobId]) next[jobId] = prev[jobId]
      }
      return next
    })
  }, [jobStatuses])

  // Auto-download when a job completes, then mark as downloaded
  const [downloadInProgress, setDownloadInProgress] = useState<Record<string, boolean>>({})

  useEffect(() => {
    const triggerDownload = async (jobId: string, originalFilename: string) => {
      try {
        setDownloadInProgress(prev => ({ ...prev, [jobId]: true }))

        // Prefer server-provided output filename when available
        const serverFilename = jobStatuses[jobId]?.output_filename
        const csvFilename = serverFilename
          ? serverFilename
          : (originalFilename.toLowerCase().endsWith('.pdf')
              ? originalFilename.slice(0, -4) + '.csv'
              : originalFilename + '.csv')

        const url = `/api/download/${encodeURIComponent(csvFilename)}`
        const response = await axios.get(url, { responseType: 'blob' })

        const blobUrl = window.URL.createObjectURL(new Blob([response.data], { type: 'text/csv' }))
        const link = document.createElement('a')
        link.href = blobUrl
        link.setAttribute('download', csvFilename)
        document.body.appendChild(link)
        link.click()
        link.parentNode?.removeChild(link)
        window.URL.revokeObjectURL(blobUrl)

        // Mark job as downloaded on the server
        await axios.post(`/api/set-downloaded/${encodeURIComponent(jobId)}`)

        // Optimistically update local status
        setJobStatuses(prev => ({
          ...prev,
          [jobId]: prev[jobId] ? { ...prev[jobId], status: 'downloaded' } as JobStatus : prev[jobId]
        }))
      } catch (e) {
        if (import.meta.env.DEV) console.error('Auto-download failed for job', jobId, e)
      } finally {
        setDownloadInProgress(prev => ({ ...prev, [jobId]: false }))
      }
    }

    for (const jobId of Object.keys(jobStatuses)) {
      const status = jobStatuses[jobId]?.status
      if (status === 'completed' && !downloadInProgress[jobId]) {
        const originalFilename = jobIdToFilename[jobId]
        if (originalFilename) {
          triggerDownload(jobId, originalFilename)
        }
      }
    }
  }, [jobStatuses, jobIdToFilename, downloadInProgress])

  const handleUpload = async () => {
    if (files.length === 0) return

    setIsUploading(true)
    const formData = new FormData()
    files.forEach(file => formData.append('files', file))

    try {
      const response = await axios.post('/api/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
      const results: UploadResult[] = response.data.results
      // Capture any new job_id -> filename mappings
      const mappings: Record<string, string> = {}
      for (const r of results) {
        if (r.job_id) {
          mappings[r.job_id] = r.filename
        }
      }
      if (Object.keys(mappings).length > 0) {
        setJobIdToFilename(prev => ({ ...prev, ...mappings }))
      }
      // Immediately refresh job statuses after upload
      try {
        const statuses = await axios.get<Record<string, JobStatus>>('/api/status')
        setJobStatuses(statuses.data)
      } catch (e) {
        if (import.meta.env.DEV) console.debug('Failed to refresh job statuses', e)
      }
      setFiles([])
    } catch (error) {
      console.error('Upload error:', error)
    } finally {
      setIsUploading(false)
    }
  }

  const isUploadDisabled = isCheckingHealth || !healthStatus?.ollama_available

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <Activity className="h-8 w-8 text-blue-600" />
              <h1 className="text-xl font-semibold text-gray-900">
                Confirmation Parser
              </h1>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Upload and Health */}
          <div className="lg:col-span-1 space-y-6">
            <HealthStatus healthStatus={healthStatus} />
            <FileUpload
              files={files}
              onFilesChange={setFiles}
              onUpload={handleUpload}
              isUploading={isUploading}
              isDisabled={isUploadDisabled}
            />
          </div>

          {/* Right Column - Job Table */}
          <div className="lg:col-span-2">
            <JobTable jobStatuses={jobStatuses} jobIdToFilename={jobIdToFilename} />
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
