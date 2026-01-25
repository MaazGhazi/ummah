"use client";
import { useRef, useState, useEffect, useCallback, useMemo } from "react";
import GlowingButton from "@/components/ui/GlowingButton";
import { SparklesCore } from "@/components/ui/SparklesCore";

interface EditedSection {
  start: number; // in seconds
  end: number;   // in seconds
}

interface VideoPlayerProps {
  videoUrl: string;
  onReset: () => void;
  editedSections?: EditedSection[];
}

export default function VideoPlayer({ videoUrl, onReset, editedSections = [] }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const progressRef = useRef<HTMLDivElement>(null);
  const controlsTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastTimeUpdateRef = useRef<number>(0);
  
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [controlsVisible, setControlsVisible] = useState(true);
  const [hoverTime, setHoverTime] = useState<number | null>(null);
  const [hoverPosition, setHoverPosition] = useState(0);

  // Controls visibility: always show when paused, auto-hide when playing
  const showControls = !isPlaying || controlsVisible;

  // Generate test sections (middle 20% of video) when duration is loaded
  const highlightedSections = useMemo(() => {
    if (duration > 0 && editedSections.length === 0) {
      // For testing: highlight the middle 20% of the video
      const middleStart = duration * 0.4;
      const middleEnd = duration * 0.6;
      return [{ start: middleStart, end: middleEnd }];
    }
    return editedSections;
  }, [duration, editedSections]);

  const handleDownload = useCallback(() => {
    const link = document.createElement('a');
    link.href = videoUrl;
    link.download = 'filtered-video.mp4';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [videoUrl]);

  // Format time as MM:SS
  const formatTime = useCallback((time: number) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  }, []);

  // Video event handlers
  const handleLoadedMetadata = useCallback(() => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
    }
  }, []);

  // Throttled time update to reduce state changes
  const handleTimeUpdate = useCallback(() => {
    if (videoRef.current) {
      const now = Date.now();
      // Only update every 250ms to reduce re-renders
      if (now - lastTimeUpdateRef.current > 250) {
        setCurrentTime(videoRef.current.currentTime);
        lastTimeUpdateRef.current = now;
      }
    }
  }, []);

  const togglePlay = useCallback(() => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  }, [isPlaying]);

  const handleProgressClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (progressRef.current && videoRef.current) {
      const rect = progressRef.current.getBoundingClientRect();
      const pos = (e.clientX - rect.left) / rect.width;
      videoRef.current.currentTime = pos * duration;
      setCurrentTime(pos * duration);
    }
  }, [duration]);

  const handleProgressHover = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (progressRef.current && duration > 0) {
      const rect = progressRef.current.getBoundingClientRect();
      const pos = (e.clientX - rect.left) / rect.width;
      const time = Math.max(0, Math.min(pos * duration, duration));
      setHoverTime(time);
      setHoverPosition(e.clientX - rect.left);
    }
  }, [duration]);

  const handleProgressLeave = useCallback(() => {
    setHoverTime(null);
  }, []);

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    if (videoRef.current) {
      videoRef.current.volume = newVolume;
    }
    setIsMuted(newVolume === 0);
  };

  const toggleMute = () => {
    if (videoRef.current) {
      if (isMuted) {
        videoRef.current.volume = volume || 1;
        setIsMuted(false);
      } else {
        videoRef.current.volume = 0;
        setIsMuted(true);
      }
    }
  };

  const toggleFullscreen = () => {
    const container = videoRef.current?.parentElement?.parentElement;
    if (!container) return;

    if (!isFullscreen) {
      if (container.requestFullscreen) {
        container.requestFullscreen();
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
    }
    setIsFullscreen(!isFullscreen);
  };

  const handleVideoEnd = () => {
    setIsPlaying(false);
  };

  // Hide controls after inactivity (only when playing)
  useEffect(() => {
    if (!isPlaying) return;
    
    if (controlsTimeoutRef.current) {
      clearTimeout(controlsTimeoutRef.current);
    }
    
    controlsTimeoutRef.current = setTimeout(() => setControlsVisible(false), 3000);
    return () => {
      if (controlsTimeoutRef.current) {
        clearTimeout(controlsTimeoutRef.current);
      }
    };
  }, [isPlaying, currentTime]);

  const handleMouseMove = () => {
    setControlsVisible(true);
  };

  // Calculate progress percentage
  const progressPercent = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <div className="w-full flex flex-col items-center">
      {/* Custom Video Player */}
      <div 
        className="relative bg-black rounded-xl overflow-hidden border border-gray-800 group w-full max-w-5xl"
        onMouseMove={handleMouseMove}
      >
        {/* Video Element */}
        <video
          ref={videoRef}
          src={videoUrl}
          className="w-full aspect-video cursor-pointer"
          onClick={togglePlay}
          onLoadedMetadata={handleLoadedMetadata}
          onTimeUpdate={handleTimeUpdate}
          onEnded={handleVideoEnd}
        />

        {/* Play/Pause Overlay */}
        {!isPlaying && (
          <div 
            className="absolute inset-0 flex items-center justify-center bg-black/30 cursor-pointer"
            onClick={togglePlay}
          >
            <div className="w-20 h-20 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center hover:bg-white/30 transition-colors">
              <svg className="w-10 h-10 text-white ml-1" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
            </div>
          </div>
        )}

        {/* Controls */}
        <div 
          className={`absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4 transition-opacity duration-300 ${
            showControls ? 'opacity-100' : 'opacity-0'
          }`}
        >
          {/* Progress Bar */}
          <div 
            ref={progressRef}
            className="relative h-2 bg-gray-600 rounded-full cursor-pointer mb-4 group/progress"
            onClick={handleProgressClick}
            onMouseMove={handleProgressHover}
            onMouseLeave={handleProgressLeave}
          >
            {/* Edited Sections Highlights */}
            {highlightedSections.map((section, index) => (
              <div
                key={index}
                className="absolute h-full bg-gradient-to-r from-indigo-500/60 to-sky-500/60 rounded-full"
                style={{
                  left: `${(section.start / duration) * 100}%`,
                  width: `${((section.end - section.start) / duration) * 100}%`,
                }}
              />
            ))}
            
            {/* Progress Fill */}
            <div 
              className="absolute h-full bg-indigo-500 rounded-full"
              style={{ width: `${progressPercent}%` }}
            />
            
            {/* Progress Handle */}
            <div 
              className="absolute top-1/2 -translate-y-1/2 w-4 h-4 bg-white rounded-full shadow-lg opacity-0 group-hover/progress:opacity-100 transition-opacity"
              style={{ left: `calc(${progressPercent}% - 8px)` }}
            />

            {/* Time Preview on Hover */}
            {hoverTime !== null && (
              <div 
                className="absolute bottom-6 transform -translate-x-1/2 pointer-events-none"
                style={{ left: hoverPosition }}
              >
                <div className="bg-gray-900 rounded-lg px-3 py-2 shadow-xl border border-gray-700">
                  <div className="text-center text-white text-sm font-medium">
                    {formatTime(hoverTime)}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Control Buttons */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {/* Play/Pause Button */}
              <button onClick={togglePlay} className="text-white hover:text-indigo-400 transition-colors cursor-pointer">
                {isPlaying ? (
                  <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
                  </svg>
                ) : (
                  <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                )}
              </button>

              {/* Volume Controls */}
              <div className="flex items-center gap-2">
                <button onClick={toggleMute} className="text-white hover:text-indigo-400 transition-colors cursor-pointer">
                  {isMuted || volume === 0 ? (
                    <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z" />
                    </svg>
                  ) : (
                    <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z" />
                    </svg>
                  )}
                </button>
                {/* Custom Volume Slider with fill */}
                <div className="relative w-20 h-1 bg-gray-600 rounded-full">
                  <div 
                    className="absolute h-full bg-gradient-to-r from-indigo-500 to-sky-500 rounded-full"
                    style={{ width: `${(isMuted ? 0 : volume) * 100}%` }}
                  />
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={isMuted ? 0 : volume}
                    onChange={handleVolumeChange}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  />
                  <div 
                    className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full shadow-lg pointer-events-none"
                    style={{ left: `calc(${(isMuted ? 0 : volume) * 100}% - 6px)` }}
                  />
                </div>
              </div>

              {/* Time Display */}
              <span className="text-white text-sm">
                {formatTime(currentTime)} / {formatTime(duration)}
              </span>
            </div>

            <div className="flex items-center gap-4">
              {/* Edited Sections Legend */}
              {highlightedSections.length > 0 && (
                <div className="flex items-center gap-2 text-sm text-gray-400">
                  <div className="w-3 h-3 bg-gradient-to-r from-indigo-500 to-sky-500 rounded" />
                  <span>Edited</span>
                </div>
              )}

              {/* Fullscreen Button */}
              <button onClick={toggleFullscreen} className="text-white hover:text-indigo-400 transition-colors cursor-pointer">
                {isFullscreen ? (
                  <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z" />
                  </svg>
                ) : (
                  <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z" />
                  </svg>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Sparkles under video player */}
      <div className="relative h-12 w-full">
        <SparklesCore
          id="video-sparkles"
          background="transparent"
          minSize={0.4}
          maxSize={1}
          particleDensity={80}
          className="w-full h-full"
          particleColor="#0ea5e9"
        />
      </div>

      <div className="flex justify-center gap-6 mt-4">
        <GlowingButton onClick={handleDownload} iconOnly>
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
        </GlowingButton>
        <GlowingButton onClick={onReset} iconOnly>
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </GlowingButton>
      </div>
    </div>
  );
}
