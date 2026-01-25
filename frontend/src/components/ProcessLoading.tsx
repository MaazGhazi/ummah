"use client";
import { useEffect, useState } from "react";

const processingSteps = [
  "Analyzing video content...",
  "Detecting scenes...",
  "Applying content filters...",
  "Processing audio...",
  "Generating filtered video...",
  "Finalizing output...",
];

interface ProcessLoadingProps {
  size?: number;
  text?: string;
}

export default function ProcessLoading({ 
  size = 140, 
  text = "Processing" 
}: ProcessLoadingProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [progress, setProgress] = useState(0);
  const letters = text.split("");

  useEffect(() => {
    // Animate progress bar
    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) return 100;
        return prev + 1;
      });
    }, 50);

    // Cycle through processing steps
    const stepInterval = setInterval(() => {
      setCurrentStep((prev) => (prev + 1) % processingSteps.length);
    }, 800);

    return () => {
      clearInterval(progressInterval);
      clearInterval(stepInterval);
    };
  }, []);

  return (
    <div className="h-[calc(100vh-6rem)] flex flex-col items-center justify-center">
      <div className="text-center max-w-md">
        {/* Animated Loader */}
        <div
          className="relative flex items-center justify-center font-inter select-none mx-auto mb-8"
          style={{ width: size, height: size }}
        >
          {/* Animated Letters */}
          {letters.map((letter, index) => (
            <span
              key={index}
              className="inline-block text-white opacity-40 animate-loaderLetter text-lg font-medium"
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              {letter}
            </span>
          ))}

          {/* Animated Circle */}
          <div className="absolute inset-0 rounded-full animate-loaderCircle"></div>
        </div>

        {/* Current step */}
        <p className="text-gray-400 mb-6 h-6 transition-all duration-300">
          {processingSteps[currentStep]}
        </p>

        {/* Progress bar - fixed width */}
        <div className="w-80 bg-gray-800 rounded-full h-2 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-indigo-500 to-sky-500 transition-all duration-100 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Progress percentage */}
        <p className="text-sm text-gray-500 mt-3">{progress}% complete</p>
      </div>

      <style jsx>{`
        @keyframes loaderCircle {
          0% {
            transform: rotate(90deg);
            box-shadow:
              0 6px 12px 0 #0ea5e9 inset,
              0 12px 18px 0 #4f46e5 inset,
              0 36px 36px 0 #3730a3 inset,
              0 0 3px 1.2px rgba(14, 165, 233, 0.3),
              0 0 6px 1.8px rgba(79, 70, 229, 0.2);
          }
          50% {
            transform: rotate(270deg);
            box-shadow:
              0 6px 12px 0 #38bdf8 inset,
              0 12px 6px 0 #6366f1 inset,
              0 24px 36px 0 #4f46e5 inset,
              0 0 3px 1.2px rgba(14, 165, 233, 0.3),
              0 0 6px 1.8px rgba(79, 70, 229, 0.2);
          }
          100% {
            transform: rotate(450deg);
            box-shadow:
              0 6px 12px 0 #7dd3fc inset,
              0 12px 18px 0 #4f46e5 inset,
              0 36px 36px 0 #3730a3 inset,
              0 0 3px 1.2px rgba(14, 165, 233, 0.3),
              0 0 6px 1.8px rgba(79, 70, 229, 0.2);
          }
        }

        @keyframes loaderLetter {
          0%,
          100% {
            opacity: 0.4;
            transform: translateY(0);
          }
          20% {
            opacity: 1;
            transform: scale(1.15);
          }
          40% {
            opacity: 0.7;
            transform: translateY(0);
          }
        }

        .animate-loaderCircle {
          animation: loaderCircle 5s linear infinite;
        }

        .animate-loaderLetter {
          animation: loaderLetter 3s infinite;
        }
      `}</style>
    </div>
  );
}
