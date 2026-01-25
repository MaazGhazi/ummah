"use client";
import React from "react";
import Link from "next/link";

interface GlowingButtonProps {
  href?: string;
  onClick?: () => void;
  disabled?: boolean;
  iconOnly?: boolean;
  children: React.ReactNode;
}

const GlowingButton = ({ href, onClick, disabled = false, iconOnly = false, children }: GlowingButtonProps) => {
  // Size configurations
  const sizes = iconOnly 
    ? { outer: "max-h-[60px] max-w-[60px]", inner1: "max-h-[55px] max-w-[58px]", inner2: "max-h-[53px] max-w-[56px]", inner3: "max-h-[49px] max-w-[54px]", button: "w-[50px] h-[50px]" }
    : { outer: "max-h-[70px] max-w-[220px]", inner1: "max-h-[65px] max-w-[218px]", inner2: "max-h-[63px] max-w-[216px]", inner3: "max-h-[59px] max-w-[214px]", button: "w-[210px] h-[56px]" };

  // Disabled state
  if (disabled) {
    return (
      <div className="relative flex items-center justify-center opacity-50 cursor-not-allowed">
        <div className="relative">
          <div className={`bg-[#010201] border border-gray-700 ${sizes.button} rounded-lg text-gray-500 px-6 text-lg flex items-center justify-center font-semibold`}>
            {children}
          </div>
        </div>
      </div>
    );
  }

  const buttonContent = (
    <>
      {/* Outer glow layer 1 */}
      <div className={`absolute z-[-1] overflow-hidden h-full w-full ${sizes.outer} rounded-xl blur-[3px] 
                      before:absolute before:content-[''] before:z-[-2] before:w-[999px] before:h-[999px] before:bg-no-repeat before:top-1/2 before:left-1/2 before:-translate-x-1/2 before:-translate-y-1/2 before:rotate-60
                      before:bg-[conic-gradient(#000,#4f46e5_5%,#000_38%,#000_50%,#0ea5e9_60%,#000_87%)] before:transition-all before:duration-2000
                      group-hover:before:rotate-[-120deg]`}>
      </div>
      
      {/* Inner glow layers */}
      <div className={`absolute z-[-1] overflow-hidden h-full w-full ${sizes.inner1} rounded-xl blur-[3px] 
                      before:absolute before:content-[''] before:z-[-2] before:w-[600px] before:h-[600px] before:bg-no-repeat before:top-1/2 before:left-1/2 before:-translate-x-1/2 before:-translate-y-1/2 before:rotate-[82deg]
                      before:bg-[conic-gradient(rgba(0,0,0,0),#3730a3,rgba(0,0,0,0)_10%,rgba(0,0,0,0)_50%,#0284c7,rgba(0,0,0,0)_60%)] before:transition-all before:duration-2000
                      group-hover:before:rotate-[-98deg]`}>
      </div>
      <div className={`absolute z-[-1] overflow-hidden h-full w-full ${sizes.inner1} rounded-xl blur-[3px] 
                      before:absolute before:content-[''] before:z-[-2] before:w-[600px] before:h-[600px] before:bg-no-repeat before:top-1/2 before:left-1/2 before:-translate-x-1/2 before:-translate-y-1/2 before:rotate-[82deg]
                      before:bg-[conic-gradient(rgba(0,0,0,0),#3730a3,rgba(0,0,0,0)_10%,rgba(0,0,0,0)_50%,#0284c7,rgba(0,0,0,0)_60%)] before:transition-all before:duration-2000
                      group-hover:before:rotate-[-98deg]`}>
      </div>

      {/* Bright accent layer */}
      <div className={`absolute z-[-1] overflow-hidden h-full w-full ${sizes.inner2} rounded-lg blur-[2px] 
                      before:absolute before:content-[''] before:z-[-2] before:w-[600px] before:h-[600px] before:bg-no-repeat before:top-1/2 before:left-1/2 before:-translate-x-1/2 before:-translate-y-1/2 before:rotate-[83deg]
                      before:bg-[conic-gradient(rgba(0,0,0,0)_0%,#a5b4fc,rgba(0,0,0,0)_8%,rgba(0,0,0,0)_50%,#7dd3fc,rgba(0,0,0,0)_58%)] before:brightness-140
                      before:transition-all before:duration-2000 group-hover:before:rotate-[-97deg]`}>
      </div>

      {/* Inner border layer */}
      <div className={`absolute z-[-1] overflow-hidden h-full w-full ${sizes.inner3} rounded-xl blur-[0.5px] 
                      before:absolute before:content-[''] before:z-[-2] before:w-[600px] before:h-[600px] before:bg-no-repeat before:top-1/2 before:left-1/2 before:-translate-x-1/2 before:-translate-y-1/2 before:rotate-70
                      before:bg-[conic-gradient(#1c191c,#4f46e5_5%,#1c191c_14%,#1c191c_50%,#0ea5e9_60%,#1c191c_64%)] before:brightness-130
                      before:transition-all before:duration-2000 group-hover:before:rotate-[-110deg]`}>
      </div>

      {/* Button content */}
      <div className="relative">
        <div className={`bg-[#010201] border-none ${sizes.button} rounded-lg text-white ${iconOnly ? '' : 'px-6'} text-lg flex items-center justify-center font-semibold transition-all duration-300 group-hover:bg-[#0a0a0a]`}>
          {children}
        </div>
        {/* Glow accent */}
        {!iconOnly && (
          <div className="pointer-events-none w-[30px] h-[20px] absolute bg-[#0ea5e9] top-[10px] left-[5px] blur-2xl opacity-80 transition-all duration-2000 group-hover:opacity-0"></div>
        )}
      </div>
    </>
  );

  // Link button (for navigation)
  if (href) {
    return (
      <div className="relative flex items-center justify-center isolate">
        <Link href={href} className="relative flex items-center justify-center group cursor-pointer">
          {buttonContent}
        </Link>
      </div>
    );
  }

  // Regular button (for onClick)
  return (
    <div className="relative flex items-center justify-center isolate">
      <button onClick={onClick} className="relative flex items-center justify-center group cursor-pointer">
        {buttonContent}
      </button>
    </div>
  );
};

export default GlowingButton;
