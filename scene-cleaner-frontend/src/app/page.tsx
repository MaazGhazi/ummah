"use client";

import { useState, useCallback, useRef } from "react";
import {
  Upload,
  Download,
  AlertCircle,
  X,
  Film,
  ArrowRight,
  RotateCcw,
} from "lucide-react";

type ProcessingState = "idle" | "uploading" | "processing" | "complete" | "error";

interface FilterOption {
  id: string;
  label: string;
  description: string;
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
      label: "Visual content",
      description: "Detect and replace explicit scenes",
      enabled: true,
      available: true,
    },
    {
      id: "filter_profanity",
      label: "Profanity",
      description: "Mute or bleep explicit language",
      enabled: false,
      available: false,
    },
    {
      id: "filter_music",
      label: "Music",
      description: "Remove or replace background music",
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
      setError("Enable at least one filter");
      return;
    }

    setState("uploading");
    setProgress(0);
    setStatusMessage("Uploading");
    setError("");
    setDownloadUrl(null);

    const formData = new FormData();
    formData.append("video", file);

    filters.forEach((f) => {
      formData.append(f.id, f.enabled.toString());
    });

    try {
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
      setStatusMessage("Analyzing video");

      const response = await fetch("http://localhost:5000/api/process", {
        method: "POST",
        body: formData,
      });

      clearInterval(uploadInterval);

      const contentType = response.headers.get("content-type") || "";

      if (contentType.includes("application/json")) {
        const data = await response.json();

        if (!response.ok || !data.success) {
          throw new Error(data.error || "Processing failed");
        }

        let videoUrl = data.video_url;
        if (videoUrl.startsWith("/api/")) {
          videoUrl = `http://localhost:5000${videoUrl}`;
        }

        setProgress(100);
        setDownloadUrl(videoUrl);
        setDownloadFilename(data.filename || `${file.name.replace(/\.[^/.]+$/, "")}_clean.mp4`);
        setTimestamps(data.timestamps || []);
        setState("complete");
        setStatusMessage(
          `${data.replacements_successful || 0} scene${(data.replacements_successful || 0) === 1 ? "" : "s"} replaced`
        );
      } else {
        if (!response.ok) {
          throw new Error("Processing failed");
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);

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
        setStatusMessage("Done");
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
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const seekToTimestamp = (seconds: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = seconds;
      videoRef.current.play();
    }
  };

  const getSeverityDot = (severity: string) => {
    switch (severity.toLowerCase()) {
      case "heavy":
      case "severe":
        return "#c47a6a";
      case "moderate":
        return "#d4a574";
      default:
        return "#7a7a76";
    }
  };

  const downloadVideo = () => {
    if (!downloadUrl) return;
    if (downloadUrl.startsWith("blob:")) {
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = downloadFilename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } else {
      window.open(downloadUrl, "_blank");
    }
  };

  const activeFilterCount = filters.filter((f) => f.enabled).length;

  return (
    <main className="min-h-screen flex flex-col">
      {/* Top bar */}
      <header className="w-full px-6 md:px-10 py-6 flex items-center justify-between">
        <div className="flex items-baseline gap-2">
          <span className="font-serif italic text-2xl tracking-tight">halalcut</span>
          <span className="text-[11px] text-[var(--muted-2)] font-mono uppercase tracking-widest">
            v0.1
          </span>
        </div>
        <div className="flex items-center gap-2 text-[11px] font-mono uppercase tracking-widest text-[var(--muted)]">
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              state === "idle" || state === "complete"
                ? "bg-[var(--success)]"
                : state === "error"
                ? "bg-[var(--error)]"
                : "bg-[var(--accent)]"
            }`}
          />
          {state === "idle" && "ready"}
          {state === "uploading" && "uploading"}
          {state === "processing" && "processing"}
          {state === "complete" && "complete"}
          {state === "error" && "error"}
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 md:px-10 pb-16">
        <div className="w-full max-w-[620px]">
          {/* Title block */}
          <div className="mb-14">
            <h1 className="font-serif text-5xl md:text-6xl leading-[1.05] tracking-tight mb-4">
              Scene cleaner for <em className="italic">films</em>.
            </h1>
            <p className="text-[var(--muted)] text-[15px] leading-relaxed max-w-[440px]">
              Upload a film. We detect inappropriate scenes and replace them with
              continuity-matched footage. The rest of the film stays untouched.
            </p>
          </div>

          {/* Panel */}
          <div className="hairline rounded-md bg-[var(--surface)]">
            {state === "idle" && (
              <div className="p-6 md:p-8">
                {/* Upload zone */}
                <div
                  className={`upload-zone rounded-sm p-10 cursor-pointer ${
                    dragOver ? "drag-over" : ""
                  }`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => !file && fileInputRef.current?.click()}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="video/*"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                  {file ? (
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 min-w-0">
                        <Film className="w-4 h-4 text-[var(--accent)] flex-shrink-0" />
                        <div className="min-w-0">
                          <p className="text-[14px] truncate">{file.name}</p>
                          <p className="text-[11px] font-mono uppercase tracking-wider text-[var(--muted)] mt-0.5">
                            {formatFileSize(file.size)}
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setFile(null);
                        }}
                        className="text-[var(--muted)] hover:text-[var(--foreground)] flex-shrink-0 ml-4"
                        aria-label="Remove file"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-3 py-2">
                      <Upload className="w-5 h-5 text-[var(--muted)]" />
                      <p className="text-[14px] text-[var(--foreground)]">
                        Drop a video here, or click to select
                      </p>
                      <p className="text-[11px] font-mono uppercase tracking-wider text-[var(--muted-2)]">
                        mp4 · mov · avi · mkv — up to 2gb
                      </p>
                    </div>
                  )}
                </div>

                {/* Filters */}
                <div className="mt-8">
                  <div className="flex items-baseline justify-between mb-3">
                    <h3 className="text-[11px] font-mono uppercase tracking-widest text-[var(--muted)]">
                      Filters
                    </h3>
                    <span className="text-[11px] font-mono text-[var(--muted-2)]">
                      {activeFilterCount} active
                    </span>
                  </div>
                  <div>
                    {filters.map((filter, i) => (
                      <button
                        key={filter.id}
                        onClick={() => toggleFilter(filter.id)}
                        disabled={!filter.available}
                        className={`w-full flex items-center gap-4 py-4 text-left ${
                          i !== 0 ? "border-t border-[var(--border)]" : ""
                        } ${!filter.available ? "opacity-40 cursor-not-allowed" : "cursor-pointer"}`}
                      >
                        <span
                          className={`check ${
                            filter.enabled && filter.available ? "on" : ""
                          }`}
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-[14px]">{filter.label}</span>
                            {!filter.available && (
                              <span className="text-[10px] font-mono uppercase tracking-wider text-[var(--muted-2)]">
                                soon
                              </span>
                            )}
                          </div>
                          <p className="text-[12px] text-[var(--muted)] mt-0.5">
                            {filter.description}
                          </p>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                {error && (
                  <div className="mt-6 flex items-center gap-2 text-[13px] text-[var(--error)]">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    <p>{error}</p>
                  </div>
                )}

                {/* Action row */}
                <div className="mt-8 flex items-center justify-between">
                  <p className="text-[11px] font-mono uppercase tracking-widest text-[var(--muted-2)]">
                    {file ? "ready to process" : "awaiting file"}
                  </p>
                  <button
                    onClick={processVideo}
                    disabled={!file}
                    className="btn btn-primary"
                  >
                    Process
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {(state === "uploading" || state === "processing") && (
              <div className="p-6 md:p-8">
                <div className="flex items-baseline justify-between mb-6">
                  <p className="text-[14px]">
                    {statusMessage}
                    <span className="blink ml-0.5">_</span>
                  </p>
                  <span className="text-[11px] font-mono tabular-nums text-[var(--muted)]">
                    {progress.toString().padStart(2, "0")}%
                  </span>
                </div>
                <div className="progress-track">
                  <div
                    className="progress-fill"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <p className="mt-6 text-[12px] text-[var(--muted)] leading-relaxed">
                  Processing runs server-side. This can take several minutes
                  depending on film length — you can leave this tab open.
                </p>
                {file && (
                  <div className="mt-6 pt-6 border-t border-[var(--border)] flex items-center justify-between">
                    <span className="text-[11px] font-mono uppercase tracking-wider text-[var(--muted)] truncate">
                      {file.name}
                    </span>
                    <span className="text-[11px] font-mono text-[var(--muted-2)] ml-4 flex-shrink-0">
                      {formatFileSize(file.size)}
                    </span>
                  </div>
                )}
              </div>
            )}

            {state === "complete" && (
              <div>
                {/* Video */}
                {downloadUrl && (
                  <div className="bg-black">
                    <video
                      ref={videoRef}
                      src={downloadUrl}
                      controls
                      className="w-full max-h-[440px] object-contain"
                      preload="metadata"
                    />
                  </div>
                )}

                <div className="p-6 md:p-8">
                  <div className="flex items-baseline justify-between mb-6">
                    <div>
                      <p className="text-[14px]">{statusMessage}</p>
                      <p className="text-[11px] font-mono uppercase tracking-wider text-[var(--muted-2)] mt-1">
                        {downloadFilename}
                      </p>
                    </div>
                    <span className="text-[11px] font-mono uppercase tracking-widest text-[var(--success)]">
                      done
                    </span>
                  </div>

                  {timestamps.length > 0 && (
                    <div className="mb-6">
                      <div className="flex items-baseline justify-between mb-2">
                        <h3 className="text-[11px] font-mono uppercase tracking-widest text-[var(--muted)]">
                          Scenes replaced
                        </h3>
                        <span className="text-[11px] font-mono text-[var(--muted-2)]">
                          {timestamps.length}
                        </span>
                      </div>
                      <div className="hairline rounded-sm max-h-[240px] overflow-y-auto">
                        {timestamps.map((ts, idx) => (
                          <button
                            key={idx}
                            onClick={() => seekToTimestamp(ts.start)}
                            className="ts-row"
                          >
                            <span
                              className="sev-dot"
                              style={{ background: getSeverityDot(ts.severity) }}
                            />
                            <span className="min-w-0">
                              <span className="font-mono text-[12px] text-[var(--foreground)]">
                                {formatTime(ts.start)} – {formatTime(ts.end)}
                              </span>
                              <span className="text-[12px] text-[var(--muted)] ml-3">
                                {ts.issue}
                              </span>
                            </span>
                            <span className="text-[10px] font-mono uppercase tracking-wider text-[var(--muted-2)]">
                              {ts.severity}
                            </span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="flex gap-3">
                    <button onClick={resetState} className="btn btn-ghost flex-1">
                      <RotateCcw className="w-4 h-4" />
                      New video
                    </button>
                    <button onClick={downloadVideo} className="btn btn-primary flex-1">
                      <Download className="w-4 h-4" />
                      Download
                    </button>
                  </div>
                </div>
              </div>
            )}

            {state === "error" && (
              <div className="p-6 md:p-8">
                <div className="flex items-baseline justify-between mb-4">
                  <p className="text-[14px]">Processing failed</p>
                  <span className="text-[11px] font-mono uppercase tracking-widest text-[var(--error)]">
                    error
                  </span>
                </div>
                <p className="text-[13px] text-[var(--muted)] leading-relaxed mb-8">
                  {error}
                </p>
                <button onClick={resetState} className="btn btn-ghost w-full">
                  <RotateCcw className="w-4 h-4" />
                  Try again
                </button>
              </div>
            )}
          </div>

          {/* Footer line */}
          <div className="mt-10 flex items-center justify-between text-[11px] font-mono uppercase tracking-widest text-[var(--muted-2)]">
            <span>frame-accurate · continuity-matched</span>
            <span>built for film</span>
          </div>
        </div>
      </div>
    </main>
  );
}
