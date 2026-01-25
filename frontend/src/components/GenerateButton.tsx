"use client";
import GlowingButton from "@/components/ui/GlowingButton";

interface GenerateButtonProps {
  onClick: () => void;
  disabled: boolean;
}

export default function GenerateButton({ onClick, disabled }: GenerateButtonProps) {
  return (
    <div className="flex justify-center pt-4">
      <GlowingButton onClick={onClick} disabled={disabled}>
        Generate
      </GlowingButton>
    </div>
  );
}
