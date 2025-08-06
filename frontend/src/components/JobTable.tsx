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

interface UploadResult {
  filename: string;
  status: "processing" | "failed";
  reason?: string;
  job_id?: string;
}

interface JobStatus {
  total_pages: number;
  processed_pages: number;
  status: "processing" | "completed" | "failed";
}

interface JobTableProps {
  uploadResults: UploadResult[];
  jobStatuses: Record<string, JobStatus>;
}

export function JobTable({ uploadResults, jobStatuses }: JobTableProps) {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return (
          <Badge variant="default" className="bg-green-100 text-green-700">
            Downloaded
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
    if (job.status === "completed") return 100;
    if (job.status === "processing") {
      return (job.processed_pages / job.total_pages) * 100;
    }
    return 0;
  };

  if (uploadResults.length === 0) {
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
            </TableRow>
          </TableHeader>
          <TableBody>
            {uploadResults.map((result, index) => {
              const jobId = result.job_id;
              const jobStatus = jobId ? jobStatuses[jobId] : null;
              const currentStatus = jobStatus?.status || result.status;

              return (
                <TableRow key={index}>
                  <TableCell className="font-medium">
                    <span className="truncate max-w-[200px]">
                      {result.filename}
                    </span>
                  </TableCell>
                  <TableCell>{getStatusBadge(currentStatus)}</TableCell>
                  <TableCell>
                    {jobStatus &&
                    (jobStatus.status === "processing" ||
                      jobStatus.status === "completed") ? (
                      <div className="space-y-1">
                        <Progress
                          value={getProgressValue(jobId!)}
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
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
