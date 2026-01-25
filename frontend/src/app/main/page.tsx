"use client";
import { useState, useEffect, useRef } from "react";
import FileInput from "@/components/FileInput";
import FilterContainer, { Filter, defaultFilters } from "@/components/FilterContainer";
import GenerateButton from "@/components/GenerateButton";
import ProcessLoading from "@/components/ProcessLoading";
import VideoPlayer from "@/components/VideoPlayer";
import { processVideo, FilterOptions } from "@/services/api";

type Step = "input" | "processing" | "complete";
type TransitionState = "visible" | "fading-out" | "fading-in" | "hidden";

export default function MainPage() {
  const [currentStep, setCurrentStep] = useState<Step>("input");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [pageVisible, setPageVisible] = useState(false);
  const [filters, setFilters] = useState<Filter[]>(defaultFilters);
  const [error, setError] = useState<string | null>(null);
  
  // Ref to track if processing is complete (for transition timing)
  const processingCompleteRef = useRef(false);
  
  // Transition states for each section
  const [inputTransition, setInputTransition] = useState<TransitionState>("hidden");
  const [processingTransition, setProcessingTransition] = useState<TransitionState>("hidden");
  const [completeTransition, setCompleteTransition] = useState<TransitionState>("hidden");

  // Fade in page and input section on mount
  useEffect(() => {
    const timer = setTimeout(() => {
      setPageVisible(true);
      setInputTransition("fading-in");
      setTimeout(() => setInputTransition("visible"), 50);
    }, 50);
    return () => clearTimeout(timer);
  }, []);

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setError(null);
  };

  const handleFiltersChange = (newFilters: Filter[]) => {
    setFilters(newFilters);
  };

  const transitionToComplete = (url: string) => {
    // Fade out processing section
    setProcessingTransition("fading-out");
    
    setTimeout(() => {
      setProcessingTransition("hidden");
      setVideoUrl(url);
      setCurrentStep("complete");
      
      // Fade in complete section
      setCompleteTransition("fading-in");
      setTimeout(() => setCompleteTransition("visible"), 50);
    }, 700);
  };

  const transitionToError = (errorMessage: string) => {
    // Fade out processing section
    setProcessingTransition("fading-out");
    
    setTimeout(() => {
      setProcessingTransition("hidden");
      setCurrentStep("input");
      setError(errorMessage);
      
      // Fade in input section
      setInputTransition("fading-in");
      setTimeout(() => setInputTransition("visible"), 50);
    }, 700);
  };

  const handleGenerate = async () => {
    if (!selectedFile) return;
    
    setError(null);
    processingCompleteRef.current = false;
    
    // Fade out input section
    setInputTransition("fading-out");
    
    setTimeout(async () => {
      setInputTransition("hidden");
      setCurrentStep("processing");
      
      // Fade in processing section
      setProcessingTransition("fading-in");
      setTimeout(() => setProcessingTransition("visible"), 50);
      
      // Convert filters to API format
      const filterOptions: FilterOptions = {
        music: filters.find(f => f.id === "music")?.enabled ?? false,
        profanity: filters.find(f => f.id === "profanity")?.enabled ?? false,
        nudity: filters.find(f => f.id === "nudity")?.enabled ?? false,
      };

      try {
        // Call the backend API
        const result = await processVideo(selectedFile, filterOptions);
        
        if (result.success && result.videoBlob) {
          // Create URL from the returned video blob
          const url = URL.createObjectURL(result.videoBlob);
          processingCompleteRef.current = true;
          transitionToComplete(url);
        } else {
          // Handle error
          transitionToError(result.error || "Failed to process video");
        }
      } catch (err) {
        console.error("Processing error:", err);
        transitionToError("An unexpected error occurred while processing the video");
      }
    }, 700);
  };

  const handleReset = () => {
    // Fade out complete section
    setCompleteTransition("fading-out");
    
    setTimeout(() => {
      setCompleteTransition("hidden");
      setCurrentStep("input");
      setSelectedFile(null);
      setError(null);
      
      if (videoUrl) {
        URL.revokeObjectURL(videoUrl);
        setVideoUrl(null);
      }
      
      // Fade in input section
      setInputTransition("fading-in");
      setTimeout(() => setInputTransition("visible"), 50);
    }, 700);
  };

  const getTransitionClasses = (state: TransitionState) => {
    switch (state) {
      case "visible":
        return "opacity-100 translate-y-0";
      case "fading-in":
        return "opacity-0 translate-y-4";
      case "fading-out":
        return "opacity-0 -translate-y-4";
      case "hidden":
        return "hidden";
    }
  };

  return (
    <main 
      className={`min-h-screen bg-black text-white transition-opacity duration-700 ease-out ${
        pageVisible ? "opacity-100" : "opacity-0"
      }`}
    >
      <div className="max-w-6xl mx-auto px-8 py-12">
        {/* Step 1: File Input & Filters */}
        {(currentStep === "input" || inputTransition === "fading-out") && (
          <div 
            className={`space-y-8 transition-all duration-700 ease-out ${getTransitionClasses(inputTransition)}`}
          >
            <div className="text-center mb-12">
              <h1 className="text-4xl font-bold mb-4">Setup</h1>
              <p className="text-gray-400">Upload a video and select your filters</p>
            </div>
            
            {/* Error message */}
            {error && (
              <div className="bg-red-500/20 border border-red-500 text-red-400 px-4 py-3 rounded-lg text-center">
                {error}
              </div>
            )}
            
            <FileInput onFileSelect={handleFileSelect} selectedFile={selectedFile} />
            <FilterContainer filters={filters} onFiltersChange={handleFiltersChange} />
            <GenerateButton 
              onClick={handleGenerate} 
              disabled={!selectedFile} 
            />
          </div>
        )}

        {/* Step 2: Processing Animation */}
        {(currentStep === "processing" || processingTransition === "fading-out") && (
          <div 
            className={`transition-all duration-700 ease-out ${getTransitionClasses(processingTransition)}`}
          >
            <ProcessLoading />
          </div>
        )}

        {/* Step 3: Video Player */}
        {(currentStep === "complete" || completeTransition === "fading-out") && videoUrl && (
          <div 
            className={`transition-all duration-700 ease-out ${getTransitionClasses(completeTransition)}`}
          >
            <VideoPlayer videoUrl={videoUrl} onReset={handleReset} />
          </div>
        )}
      </div>
    </main>
  );
}
