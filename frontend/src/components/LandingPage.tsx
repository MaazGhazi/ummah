"use client";
import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { SparklesCore } from "@/components/ui/SparklesCore";

const LandingPage = () => {
  const router = useRouter();
  const [isTransitioning, setIsTransitioning] = useState(false);

  const handleGetStarted = () => {
    // Start fade out transition
    setIsTransitioning(true);
    
    // Navigate to main page after fade out completes
    setTimeout(() => {
      router.push("/main");
    }, 800);
  };

  return (
    <section className="min-h-screen flex flex-col items-center justify-center bg-black text-white overflow-hidden relative">
      {/* Title */}
      <h1 
        className={`md:text-7xl text-5xl lg:text-9xl font-bold text-center text-white relative z-20 transition-all duration-700 ease-out ${
          isTransitioning ? "opacity-0 -translate-y-10" : "opacity-100 translate-y-0"
        }`}
      >
        Ummah
      </h1>

      {/* Sparkles Container - Only underneath the title */}
      <div 
        className={`w-[40rem] h-40 relative transition-all duration-700 ease-out ${
          isTransitioning ? "opacity-0 -translate-y-10" : "opacity-100 translate-y-0"
        }`}
      >
        {/* Glowing Underline Gradients */}
        <div className="absolute inset-x-20 top-0 bg-gradient-to-r from-transparent via-indigo-500 to-transparent h-[2px] w-3/4 blur-sm" />
        <div className="absolute inset-x-20 top-0 bg-gradient-to-r from-transparent via-indigo-500 to-transparent h-px w-3/4" />
        <div className="absolute inset-x-60 top-0 bg-gradient-to-r from-transparent via-sky-500 to-transparent h-[5px] w-1/4 blur-sm" />
        <div className="absolute inset-x-60 top-0 bg-gradient-to-r from-transparent via-sky-500 to-transparent h-px w-1/4" />

        {/* Sparkles Core Component */}
        <SparklesCore
          background="transparent"
          minSize={0.4}
          maxSize={1}
          particleDensity={1200}
          className="w-full h-full"
          particleColor="#FFFFFF"
        />

        {/* Radial Gradient to prevent sharp edges */}
        <div 
          className="absolute inset-0 w-full h-full bg-black"
          style={{
            maskImage: "radial-gradient(350px 200px at top, transparent 20%, white)"
          }}
        />
      </div>

      {/* Description and Button */}
      <div 
        className={`relative z-10 flex flex-col items-center justify-center mt-24 transition-all duration-700 ease-out ${
          isTransitioning ? "opacity-0 translate-y-10" : "opacity-100 translate-y-0"
        }`}
      >
        <p className="text-xl text-gray-300 mb-8 text-center max-w-md px-4">
          Filter and process your videos with ease
        </p>
        <button
          onClick={handleGetStarted}
          className="relative flex items-center justify-center isolate group cursor-pointer"
        >
          {/* Outer glow layer 1 */}
          <div className="absolute z-[-1] overflow-hidden h-full w-full max-h-[70px] max-w-[220px] rounded-xl blur-[3px] 
                        before:absolute before:content-[''] before:z-[-2] before:w-[999px] before:h-[999px] before:bg-no-repeat before:top-1/2 before:left-1/2 before:-translate-x-1/2 before:-translate-y-1/2 before:rotate-60
                        before:bg-[conic-gradient(#000,#4f46e5_5%,#000_38%,#000_50%,#0ea5e9_60%,#000_87%)] before:transition-all before:duration-2000
                        group-hover:before:rotate-[-120deg]">
          </div>
          
          {/* Inner glow layers */}
          <div className="absolute z-[-1] overflow-hidden h-full w-full max-h-[65px] max-w-[218px] rounded-xl blur-[3px] 
                        before:absolute before:content-[''] before:z-[-2] before:w-[600px] before:h-[600px] before:bg-no-repeat before:top-1/2 before:left-1/2 before:-translate-x-1/2 before:-translate-y-1/2 before:rotate-[82deg]
                        before:bg-[conic-gradient(rgba(0,0,0,0),#3730a3,rgba(0,0,0,0)_10%,rgba(0,0,0,0)_50%,#0284c7,rgba(0,0,0,0)_60%)] before:transition-all before:duration-2000
                        group-hover:before:rotate-[-98deg]">
          </div>
          <div className="absolute z-[-1] overflow-hidden h-full w-full max-h-[65px] max-w-[218px] rounded-xl blur-[3px] 
                        before:absolute before:content-[''] before:z-[-2] before:w-[600px] before:h-[600px] before:bg-no-repeat before:top-1/2 before:left-1/2 before:-translate-x-1/2 before:-translate-y-1/2 before:rotate-[82deg]
                        before:bg-[conic-gradient(rgba(0,0,0,0),#3730a3,rgba(0,0,0,0)_10%,rgba(0,0,0,0)_50%,#0284c7,rgba(0,0,0,0)_60%)] before:transition-all before:duration-2000
                        group-hover:before:rotate-[-98deg]">
          </div>

          {/* Bright accent layer */}
          <div className="absolute z-[-1] overflow-hidden h-full w-full max-h-[63px] max-w-[216px] rounded-lg blur-[2px] 
                        before:absolute before:content-[''] before:z-[-2] before:w-[600px] before:h-[600px] before:bg-no-repeat before:top-1/2 before:left-1/2 before:-translate-x-1/2 before:-translate-y-1/2 before:rotate-[83deg]
                        before:bg-[conic-gradient(rgba(0,0,0,0)_0%,#a5b4fc,rgba(0,0,0,0)_8%,rgba(0,0,0,0)_50%,#7dd3fc,rgba(0,0,0,0)_58%)] before:brightness-140
                        before:transition-all before:duration-2000 group-hover:before:rotate-[-97deg]">
          </div>

          {/* Inner border layer */}
          <div className="absolute z-[-1] overflow-hidden h-full w-full max-h-[59px] max-w-[214px] rounded-xl blur-[0.5px] 
                        before:absolute before:content-[''] before:z-[-2] before:w-[600px] before:h-[600px] before:bg-no-repeat before:top-1/2 before:left-1/2 before:-translate-x-1/2 before:-translate-y-1/2 before:rotate-70
                        before:bg-[conic-gradient(#1c191c,#4f46e5_5%,#1c191c_14%,#1c191c_50%,#0ea5e9_60%,#1c191c_64%)] before:brightness-130
                        before:transition-all before:duration-2000 group-hover:before:rotate-[-110deg]">
          </div>

          {/* Button content */}
          <div className="relative">
            <div className="bg-[#010201] border-none w-[210px] h-[56px] rounded-lg text-white px-6 text-lg flex items-center justify-center font-semibold transition-all duration-300 group-hover:bg-[#0a0a0a]">
              Get Started
            </div>
            {/* Glow accent */}
            <div className="pointer-events-none w-[30px] h-[20px] absolute bg-[#0ea5e9] top-[10px] left-[5px] blur-2xl opacity-80 transition-all duration-2000 group-hover:opacity-0"></div>
          </div>
        </button>
      </div>
    </section>
  );
};

export default LandingPage;
