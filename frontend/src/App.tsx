import { useState, useEffect, useRef } from 'react'
import { Button } from './components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card'
import { Progress } from './components/ui/progress'
import { Upload, File, Download, CheckCircle, AlertCircle } from 'lucide-react'
import axios from 'axios'

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

function App() {
  const [files, setFiles] = useState<File[]>([])
  const [uploadResults, setUploadResults] = useState<UploadResult[]>([])
  const [jobStatuses, setJobStatuses] = useState<Record<string, JobStatus>>({})
  const [isUploading, setIsUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const wsRef = useRef<WebSocket | null>(null)

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



  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(event.target.files || [])
    setFiles(selectedFiles)
  }

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
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    } catch (error) {
      console.error('Upload error:', error)
    } finally {
      setIsUploading(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-500" />
      default:
        return <File className="h-4 w-4 text-blue-500" />
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-2xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              PDF Upload Tool
            </CardTitle>
            <CardDescription>
              Upload multiple PDF confirmation files to process them automatically
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* File Upload Section */}
            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".pdf"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                <Button
                  onClick={() => fileInputRef.current?.click()}
                  variant="outline"
                  className="flex items-center gap-2"
                >
                  <Upload className="h-4 w-4" />
                  Select PDF Files
                </Button>
                {files.length > 0 && (
                  <span className="text-sm text-gray-600">
                    {files.length} file(s) selected
                  </span>
                )}
              </div>

              {files.length > 0 && (
                <div className="space-y-2">
                  {files.map((file, index) => (
                    <div key={index} className="flex items-center gap-2 text-sm">
                      <File className="h-4 w-4 text-gray-500" />
                      {file.name}
                    </div>
                  ))}
                  <Button
                    onClick={handleUpload}
                    disabled={isUploading}
                    className="w-full"
                  >
                    {isUploading ? 'Uploading...' : 'Upload Files'}
                  </Button>
                </div>
              )}
            </div>

            {/* Upload Results */}
            {uploadResults.length > 0 && (
              <div className="space-y-3">
                <h3 className="font-medium">Upload Results</h3>
                <div className="space-y-2">
                  {uploadResults.map((result, index) => (
                    <div key={index} className="flex items-center gap-2 text-sm">
                      {getStatusIcon(result.status)}
                      <span className="flex-1">{result.filename}</span>
                      <span className={`text-xs px-2 py-1 rounded ${
                        result.status === 'processing' 
                          ? 'bg-blue-100 text-blue-700' 
                          : 'bg-red-100 text-red-700'
                      }`}>
                        {result.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Job Progress */}
            {Object.keys(jobStatuses).length > 0 && (
              <div className="space-y-3">
                <h3 className="font-medium">Processing Status</h3>
                <div className="space-y-3">
                  {Object.entries(jobStatuses).map(([jobId, status]) => (
                    <div key={jobId} className="space-y-2">
                      <div className="flex items-center gap-2 text-sm">
                        {getStatusIcon(status.status)}
                        <span>Job {jobId}</span>
                        <span className={`text-xs px-2 py-1 rounded ${
                          status.status === 'completed' 
                            ? 'bg-green-100 text-green-700'
                            : status.status === 'failed'
                            ? 'bg-red-100 text-red-700'
                            : 'bg-blue-100 text-blue-700'
                        }`}>
                          {status.status}
                        </span>
                      </div>
                      {status.status === 'processing' && (
                        <div className="space-y-1">
                          <Progress 
                            value={(status.processed_pages / status.total_pages) * 100} 
                            className="h-2"
                          />
                          <div className="text-xs text-gray-500">
                            {status.processed_pages} / {status.total_pages} pages
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default App
