import { useState, useEffect, useRef } from 'react'
import { Activity } from 'lucide-react'
import axios from 'axios'
import { HealthStatus } from './components/HealthStatus'
import { FileUpload } from './components/FileUpload'
import { JobTable } from './components/JobTable'

interface UploadResult {
  filename: string
  status: 'processing' | 'failed'
  reason?: string
  job_id?: string
}

interface JobStatus {
  total_pages: number
  processed_pages: number
  status: 'processing' | 'completed' | 'failed'
}

interface HealthStatus {
  status: string
  ollama_available: boolean
  message: string
}

function App() {
  const [files, setFiles] = useState<File[]>([])
  const [uploadResults, setUploadResults] = useState<UploadResult[]>([])
  const [jobStatuses, setJobStatuses] = useState<Record<string, JobStatus>>({})
  const [isUploading, setIsUploading] = useState(false)
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null)
  const [isCheckingHealth, setIsCheckingHealth] = useState(true)
  const wsRef = useRef<WebSocket | null>(null)

  // Health check effect
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await axios.get('http://localhost:8000/health')
        setHealthStatus(response.data)
      } catch (error) {
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

  // WebSocket connection
  useEffect(() => {
    const connectWebSocket = () => {
      const ws = new WebSocket('ws://localhost:8000/ws')
      
      ws.onopen = () => {
        console.log('WebSocket connected')
      }

      ws.onmessage = async (event) => {
        try {
          const data = JSON.parse(event.data)
          
          if (data.event === 'file_ready') {
            // Download the file automatically
            const response = await axios.get(`http://localhost:8000/download/${data.filename}`, {
              responseType: 'blob'
            })
            
            const url = window.URL.createObjectURL(new Blob([response.data]))
            const link = document.createElement('a')
            link.href = url
            link.setAttribute('download', data.filename)
            document.body.appendChild(link)
            link.click()
            link.remove()
            window.URL.revokeObjectURL(url)
            
            console.log(`Downloaded: ${data.filename}`)
          } else if (data.event === 'job_update') {
            // Update job status from WebSocket
            setJobStatuses(prev => ({
              ...prev,
              [data.job_id]: data.status
            }))
          }
        } catch (error) {
          console.error('Error processing WebSocket message:', error)
        }
      }

      ws.onclose = () => {
        console.log('WebSocket disconnected')
        // Reconnect after 5 seconds
        setTimeout(connectWebSocket, 5000)
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }

      wsRef.current = ws
    }

    connectWebSocket()

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  const handleUpload = async () => {
    if (files.length === 0) return

    setIsUploading(true)
    const formData = new FormData()
    files.forEach(file => formData.append('files', file))

    try {
      const response = await axios.post('http://localhost:8000/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      setUploadResults(response.data.results)
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
            <JobTable 
              uploadResults={uploadResults}
              jobStatuses={jobStatuses}
            />
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
