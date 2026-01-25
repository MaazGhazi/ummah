"use client";
import { useRef, useState } from "react";

interface FileInputProps {
  onFileSelect: (file: File) => void;
  selectedFile: File | null;
}

export default function FileInput({ onFileSelect, selectedFile }: FileInputProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type === "video/mp4") {
      onFileSelect(file);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file && file.type === "video/mp4") {
      onFileSelect(file);
    }
  };

  return (
    <div
      onClick={handleClick}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`p-8 bg-gray-900 rounded-xl border-2 border-dashed cursor-pointer transition-all duration-300 ${
        isDragging
          ? "border-indigo-500 bg-indigo-500/10"
          : selectedFile
          ? "border-indigo-500 bg-gradient-to-r from-indigo-500/10 to-sky-500/10"
          : "border-gray-700 hover:border-gray-500"
      }`}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept="video/mp4"
        onChange={handleFileChange}
        className="hidden"
      />
      
      <div className="flex flex-col items-center justify-center py-8">
        {selectedFile ? (
          <>
            <svg
              className="w-12 h-12 text-indigo-500 mb-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
            <p className="text-white font-medium">{selectedFile.name}</p>
            <p className="text-gray-400 text-sm mt-1">
              {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
            </p>
            <p className="text-indigo-400 text-sm mt-4">Click to change file</p>
          </>
        ) : (
          <>
            <svg
              className="w-12 h-12 text-gray-500 mb-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            <p className="text-gray-300 font-medium">Drag and drop your video here</p>
            <p className="text-gray-500 text-sm mt-2">or click to browse</p>
            <p className="text-gray-600 text-xs mt-4">Supports MP4 files only</p>
          </>
        )}
      </div>
    </div>
  );
}
