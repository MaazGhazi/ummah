"use client";

import { useState, useCallback, useRef } from "react";
import {
  Upload,
  Video,
  Shield,
  Sparkles,
  Download,
  AlertCircle,
  CheckCircle2,
  Loader2,
  X,
  Film,
  Music,
  MessageSquareWarning,
  Eye,
} from "lucide-react";

type ProcessingState = "idle" | "uploading" | "processing" | "complete" | "error";

interface FilterOption {
  id: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  enabled: boolean;
  available: boolean;
}

interface Timestamp {
  start: number;
  end: number;
  issue: string;
  severity: string;
}

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [state, setState] = useState<ProcessingState>("idle");
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState("");
  const [error, setError] = useState("");
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [downloadFilename, setDownloadFilename] = useState("");
  const [timestamps, setTimestamps] = useState<Timestamp[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  const [filters, setFilters] = useState<FilterOption[]>([
    {
      id: "filter_sexual_nudity",
      label: "Visual Content",
      description: "Detect and replace inappropriate visual scenes",
      icon: <Eye className="w-5 h-5" />,
      enabled: true,
      available: true,
    },
    {
      id: "filter_profanity",
      label: "Profanity",
      description: "Mute or bleep explicit language",
      icon: <MessageSquareWarning className="w-5 h-5" />,
      enabled: false,
      available: false,
    },
    {
      id: "filter_music",
      label: "Music",
      description: "Remove or replace background music",
      icon: <Music className="w-5 h-5" />,
      enabled: false,
      available: false,
    },
  ]);

  const toggleFilter = (id: string) => {
    setFilters((prev) =>
      prev.map((f) =>
        f.id === id && f.available ? { ...f, enabled: !f.enabled } : f
      )
    );
  };

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.type.startsWith("video/")) {
      setFile(droppedFile);
      setError("");
    } else {
      setError("Please upload a valid video file");
    }
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setError("");
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const processVideo = async () => {
    if (!file) return;

    const enabledFilters = filters.filter((f) => f.enabled);
    if (enabledFilters.length === 0) {
      setError("Please enable at least one filter");
      return;
    }

    setState("uploading");
    setProgress(0);
    setStatusMessage("Uploading video...");
    setError("");
    setDownloadUrl(null);

    const formData = new FormData();
    formData.append("video", file);
    
    filters.forEach((f) => {
      formData.append(f.id, f.enabled.toString());
    });

    try {
      // Simulate upload progress
      const uploadInterval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 30) {
            clearInterval(uploadInterval);
            return 30;
          }
          return prev + 5;
        });
      }, 200);

      setState("processing");
      setStatusMessage("Analyzing video content...");

      const response = await fetch("http://localhost:5000/api/process", {
        method: "POST",
        body: formData,
      });

      clearInterval(uploadInterval);

      // Check if response is JSON or direct file
      const contentType = response.headers.get("content-type") || "";
      
      if (contentType.includes("application/json")) {
        // JSON response with video URL and timestamps
        const data = await response.json();

        if (!response.ok || !data.success) {
          throw new Error(data.error || "Processing failed");
        }

        // Handle both fal.ai URLs and local API URLs
        let videoUrl = data.video_url;
        if (videoUrl.startsWith("/api/")) {
          videoUrl = `http://localhost:5000${videoUrl}`;
        }
        
        setProgress(100);
        setDownloadUrl(videoUrl);
        setDownloadFilename(data.filename || `${file.name.replace(/\.[^/.]+$/, "")}_clean.mp4`);
        setTimestamps(data.timestamps || []);
        setState("complete");
        setStatusMessage(`Video processed successfully! ${data.replacements_successful || 0} scenes replaced.`);
      } else {
        // Direct file response (fallback)
        if (!response.ok) {
          throw new Error("Processing failed");
        }
        
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        
        // Get filename from Content-Disposition header
        const contentDisposition = response.headers.get("Content-Disposition");
        let filename = `${file.name.replace(/\.[^/.]+$/, "")}_clean.mp4`;
        if (contentDisposition) {
          const match = contentDisposition.match(/filename="?(.+)"?/);
          if (match) filename = match[1];
        }
        
        setProgress(100);
        setDownloadUrl(url);
        setDownloadFilename(filename);
        setTimestamps([]);
        setState("complete");
        setStatusMessage("Video processed successfully!");
      }
    } catch (err) {
      setState("error");
      setError(err instanceof Error ? err.message : "An error occurred");
      setStatusMessage("");
    }
  };

  const resetState = () => {
    setState("idle");
    setFile(null);
    setProgress(0);
    setStatusMessage("");
    setError("");
    // Revoke blob URL if it's a blob
    if (downloadUrl && downloadUrl.startsWith("blob:")) {
      URL.revokeObjectURL(downloadUrl);
    }
    setDownloadUrl(null);
    setDownloadFilename("");
    setTimestamps([]);
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const seekToTimestamp = (seconds: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = seconds;
      videoRef.current.play();
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case "heavy":
      case "severe":
        return "bg-red-500/20 text-red-400 border-red-500/30";
      case "moderate":
        return "bg-orange-500/20 text-orange-400 border-orange-500/30";
      default:
        return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30";
    }
  };

  const downloadVideo = () => {
    if (downloadUrl) {
      if (downloadUrl.startsWith("blob:")) {
        // Blob URL (demo mode) - trigger download
        const a = document.createElement("a");
        a.href = downloadUrl;
        a.download = downloadFilename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      } else {
        // fal.ai URL - open in new tab
        window.open(downloadUrl, "_blank");
      }
    }
  };

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-6 md:p-12">
      {/* Header */}
      <div className="text-center mb-12">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[var(--card)] border border-[var(--card-border)] mb-6">
          <Shield className="w-4 h-4 text-[var(--accent)]" />
          <span className="text-sm text-[var(--muted)]">AI-Powered Moderation</span>
        </div>
        <h1 className="text-4xl md:text-6xl font-bold mb-4 tracking-tight">
          Halal <span className="text-[var(--accent)]">Cuts</span>
        </h1>
        <p className="text-[var(--muted)] text-lg max-w-md mx-auto">
          Make your videos halal — AI detects and replaces inappropriate scenes seamlessly
        </p>
      </div>

      {/* Main Card */}
      <div className="w-full max-w-2xl">
        <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-2xl p-8 glow-sm">
          {state === "idle" && (
            <>
              {/* Upload Zone */}
              <div
                className={`upload-zone rounded-xl p-8 mb-6 cursor-pointer transition-all ${
                  dragOver ? "drag-over" : ""
                }`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="video/*"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                <div className="flex flex-col items-center gap-4">
                  {file ? (
                    <>
                      <div className="w-16 h-16 rounded-full bg-[var(--accent)]/10 flex items-center justify-center">
                        <Film className="w-8 h-8 text-[var(--accent)]" />
                      </div>
                      <div className="text-center">
                        <p className="font-medium mb-1">{file.name}</p>
                        <p className="text-sm text-[var(--muted)]">
                          {formatFileSize(file.size)}
                        </p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setFile(null);
                        }}
                        className="text-sm text-[var(--muted)] hover:text-[var(--foreground)] flex items-center gap-1"
                      >
                        <X className="w-4 h-4" /> Remove
                      </button>
                    </>
                  ) : (
                    <>
                      <div className="w-16 h-16 rounded-full bg-[var(--accent)]/10 flex items-center justify-center animate-float">
                        <Upload className="w-8 h-8 text-[var(--accent)]" />
                      </div>
                      <div className="text-center">
                        <p className="font-medium mb-1">
                          Drop your video here or click to browse
                        </p>
                        <p className="text-sm text-[var(--muted)]">
                          Supports MP4, MOV, AVI, MKV (up to 2GB)
                        </p>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Filter Options */}
              <div className="mb-6">
                <h3 className="text-sm font-medium text-[var(--muted)] mb-3 uppercase tracking-wider">
                  Content Filters
                </h3>
                <div className="space-y-3">
                  {filters.map((filter) => (
                    <div
                      key={filter.id}
                      className={`flex items-center justify-between p-4 rounded-lg border transition-all ${
                        filter.available
                          ? "bg-[var(--background)] border-[var(--card-border)] hover:border-[var(--accent)]/50"
                          : "bg-[var(--background)]/50 border-[var(--card-border)]/50 opacity-60"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                            filter.enabled && filter.available
                              ? "bg-[var(--accent)]/20 text-[var(--accent)]"
                              : "bg-[var(--card-border)]/50 text-[var(--muted)]"
                          }`}
                        >
                          {filter.icon}
                        </div>
                        <div>
                          <p className="font-medium flex items-center gap-2">
                            {filter.label}
                            {!filter.available && (
                              <span className="text-xs px-2 py-0.5 rounded bg-[var(--card-border)] text-[var(--muted)]">
                                Coming Soon
                              </span>
                            )}
                          </p>
                          <p className="text-sm text-[var(--muted)]">
                            {filter.description}
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={() => toggleFilter(filter.id)}
                        disabled={!filter.available}
                        className={`toggle-switch ${
                          filter.enabled && filter.available ? "active" : ""
                        } ${!filter.available ? "cursor-not-allowed" : ""}`}
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Error Message */}
              {error && (
                <div className="flex items-center gap-2 p-4 rounded-lg bg-[var(--error)]/10 border border-[var(--error)]/20 text-[var(--error)] mb-6">
                  <AlertCircle className="w-5 h-5 flex-shrink-0" />
                  <p className="text-sm">{error}</p>
                </div>
              )}

              {/* Process Button */}
              <button
                onClick={processVideo}
                disabled={!file}
                className={`w-full py-4 rounded-xl font-medium text-lg flex items-center justify-center gap-2 transition-all ${
                  file
                    ? "bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white glow"
                    : "bg-[var(--card-border)] text-[var(--muted)] cursor-not-allowed"
                }`}
              >
                <Sparkles className="w-5 h-5" />
                Process Video
              </button>
            </>
          )}

          {(state === "uploading" || state === "processing") && (
            <div className="py-8">
              <div className="flex flex-col items-center gap-6">
                <div className="relative">
                  <div className="w-24 h-24 rounded-full bg-[var(--accent)]/10 flex items-center justify-center">
                    <Video className="w-12 h-12 text-[var(--accent)]" />
                  </div>
                  <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-[var(--accent)] animate-spin-slow" />
                </div>
                <div className="text-center">
                  <p className="font-medium text-lg mb-2">{statusMessage}</p>
                  <p className="text-sm text-[var(--muted)]">
                    This may take several minutes depending on video length
                  </p>
                </div>
                <div className="w-full bg-[var(--card-border)] rounded-full h-2 overflow-hidden">
                  <div
                    className="progress-bar h-full rounded-full"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <p className="text-sm text-[var(--muted)]">{progress}% complete</p>
              </div>
            </div>
          )}

          {state === "complete" && (
            <div className="py-6">
              <div className="flex flex-col gap-5">
                <div className="flex items-center gap-3">
                  <CheckCircle2 className="w-8 h-8 text-[var(--success)]" />
                  <div>
                    <p className="font-medium text-lg">{statusMessage}</p>
                    <p className="text-sm text-[var(--muted)]">
                      Your clean video is ready
                    </p>
                  </div>
                </div>
                
                {/* Video Preview */}
                {downloadUrl && (
                  <div className="w-full rounded-xl overflow-hidden border border-[var(--card-border)] bg-black">
                    <video
                      ref={videoRef}
                      src={downloadUrl}
                      controls
                      className="w-full max-h-[400px] object-contain"
                      preload="metadata"
                    />
                  </div>
                )}
                
                {/* Detected Scenes / Timestamps */}
                {timestamps.length > 0 && (
                  <div className="w-full">
                    <h3 className="text-sm font-medium text-[var(--muted)] mb-2 uppercase tracking-wider">
                      Scenes Replaced ({timestamps.length})
                    </h3>
                    <div className="space-y-2 max-h-[200px] overflow-y-auto">
                      {timestamps.map((ts, idx) => (
                        <button
                          key={idx}
                          onClick={() => seekToTimestamp(ts.start)}
                          className={`w-full flex items-center justify-between p-3 rounded-lg border transition-all hover:scale-[1.02] ${getSeverityColor(ts.severity)}`}
                        >
                          <div className="flex items-center gap-3">
                            <span className="font-mono text-sm">
                              {formatTime(ts.start)} - {formatTime(ts.end)}
                            </span>
                            <span className="text-sm opacity-80">{ts.issue}</span>
                          </div>
                          <span className="text-xs uppercase font-medium opacity-60">
                            {ts.severity}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                
                <div className="flex gap-3 w-full">
                  <button
                    onClick={resetState}
                    className="flex-1 py-3 rounded-xl font-medium border border-[var(--card-border)] hover:bg-[var(--card-border)]/50 transition-all flex items-center justify-center gap-2"
                  >
                    Process Another
                  </button>
                  <button
                    onClick={downloadVideo}
                    className="flex-1 py-3 rounded-xl font-medium bg-[var(--success)] hover:bg-[var(--success)]/80 text-white transition-all flex items-center justify-center gap-2"
                  >
                    <Download className="w-5 h-5" />
                    Download
                  </button>
                </div>
              </div>
            </div>
          )}

          {state === "error" && (
            <div className="py-8">
              <div className="flex flex-col items-center gap-6">
                <div className="w-24 h-24 rounded-full bg-[var(--error)]/10 flex items-center justify-center">
                  <AlertCircle className="w-12 h-12 text-[var(--error)]" />
                </div>
                <div className="text-center">
                  <p className="font-medium text-lg mb-2">Processing Failed</p>
                  <p className="text-sm text-[var(--error)]">{error}</p>
                </div>
                <button
                  onClick={resetState}
                  className="w-full py-3 rounded-xl font-medium border border-[var(--card-border)] hover:bg-[var(--card-border)]/50 transition-all"
                >
                  Try Again
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer Info */}
        <div className="mt-6 text-center text-sm text-[var(--muted)]">
          <p>Powered by OpenAI Vision & fal.ai Video Generation</p>
        </div>
      </div>
    </main>
  );
}
