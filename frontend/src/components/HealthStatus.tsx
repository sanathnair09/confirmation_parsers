import { Card, CardContent } from './ui/card'
import { Badge } from './ui/badge'

interface HealthStatusProps {
  healthStatus: {
    status: string
    ollama_available: boolean
    message: string
  } | null
}

export function HealthStatus({ healthStatus }: HealthStatusProps) {
  if (!healthStatus) return null

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-medium text-gray-900">
              System Status
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              {healthStatus.message}
            </p>
          </div>
          <Badge 
            variant={healthStatus.ollama_available ? "default" : "destructive"}
            className="ml-auto"
          >
            {healthStatus.ollama_available ? 'Online' : 'Offline'}
          </Badge>
        </div>
      </CardContent>
    </Card>
  )
} 