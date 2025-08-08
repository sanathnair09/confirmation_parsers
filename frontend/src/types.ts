export interface UploadResult {
  filename: string
  status: 'processing' | 'failed'
  reason?: string
  job_id?: string
}

export interface JobStatus {
  total_pages: number
  processed_pages: number
  status: 'processing' | 'completed' | 'failed' | 'downloaded'
  total_time: number
  output_filename?: string
}

export interface HealthStatus {
  status: string
  ollama_available: boolean
  message: string
}

