import { File } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "./ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "./ui/table";
import { Badge } from "./ui/badge";
import { Progress } from "./ui/progress";
import type { JobStatus } from "../types";

interface JobTableProps {
  jobStatuses: Record<string, JobStatus>;
  jobIdToFilename: Record<string, string>;
}

export function JobTable({ jobStatuses, jobIdToFilename }: JobTableProps) {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case "downloaded":
        return (
          <Badge variant="default" className="bg-blue-100 text-blue-700">
            Downloaded
          </Badge>
        );
      case "completed":
        return (
          <Badge variant="default" className="bg-green-100 text-green-700">
            Completed
          </Badge>
        );
      case "failed":
        return <Badge variant="destructive">Failed</Badge>;
      case "processing":
        return <Badge variant="secondary">Processing</Badge>;
      default:
        return <Badge variant="outline">Pending</Badge>;
    }
  };

  const getProgressValue = (jobId: string) => {
    const job = jobStatuses[jobId];
    if (!job) return 0;
    if (job.status === "completed" || job.status === "downloaded") return 100;
    if (job.status === "processing") {
      return (job.processed_pages / job.total_pages) * 100;
    }
    return 0;
  };

  const jobIds = Object.keys(jobStatuses)
  if (jobIds.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <File className="h-5 w-5" />
            Job Queue
          </CardTitle>
          <CardDescription>No jobs have been submitted yet</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-gray-500">
            <File className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p>Upload files to see job status</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <File className="h-5 w-5" />
          Job Queue
        </CardTitle>
        <CardDescription>
          Track the status of your file processing jobs
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>File</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Progress</TableHead>
              <TableHead className="text-right">Time</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {jobIds.map((jobId) => {
              const jobStatus = jobStatuses[jobId]
              const filename = jobIdToFilename[jobId] ?? jobId
              const currentStatus = jobStatus?.status ?? 'processing'

              return (
                <TableRow key={jobId}>
                  <TableCell className="font-medium">
                    <span className="truncate max-w-[200px]">
                      {filename}
                    </span>
                  </TableCell>
                  <TableCell>{getStatusBadge(currentStatus)}</TableCell>
                  <TableCell>
                    {jobStatus && (jobStatus.status === "processing" || jobStatus.status === "completed") ? (
                      <div className="space-y-1">
                        <Progress
                          value={getProgressValue(jobId)}
                          className="h-2"
                        />
                        <div className="text-xs text-gray-500">
                          {jobStatus.processed_pages} / {jobStatus.total_pages}{" "}
                          pages
                        </div>
                      </div>
                    ) : (
                      <span className="text-sm text-gray-500">-</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    {typeof jobStatus?.total_time === 'number' && jobStatus.total_time > 0
                      ? `${jobStatus.total_time.toFixed(2)}s`
                      : jobStatus?.status === 'processing'
                        ? '—'
                        : '-'}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
