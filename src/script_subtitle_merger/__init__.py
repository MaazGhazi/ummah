"""
Script-Subtitle Merger Package

Provides tools for parsing and merging movie scripts with subtitle files
to create timestamped datasets with scene context.
"""

from .srt_parser import (
    SubtitleEntry,
    parse_srt,
    get_cleaned_entries,
    clean_subtitle_text,
    time_to_ms,
    ms_to_time,
)

from .script_parser import (
    ScriptScene,
    ScriptElement,
    ElementType,
    parse_script,
    get_all_dialogue,
    get_scene_by_number,
)

from .merger import (
    MergedEntry,
    MergedDataset,
    ScriptSubtitleMerger,
    merge_script_and_subtitles,
    get_default_output_path,
    OUTPUT_DIR,
    FUZZY_LIB,
)

# Lazy import for LLM validator (requires openai package)
def __getattr__(name):
    if name in ("LLMValidator", "validate_merged_json"):
        from .llm_validator import LLMValidator, validate_merged_json
        return LLMValidator if name == "LLMValidator" else validate_merged_json
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    # SRT Parser
    "SubtitleEntry",
    "parse_srt",
    "get_cleaned_entries",
    "clean_subtitle_text",
    "time_to_ms",
    "ms_to_time",
    # Script Parser
    "ScriptScene",
    "ScriptElement",
    "ElementType",
    "parse_script",
    "get_all_dialogue",
    "get_scene_by_number",
    # Merger
    "MergedEntry",
    "MergedDataset",
    "ScriptSubtitleMerger",
    "merge_script_and_subtitles",
    "get_default_output_path",
    "OUTPUT_DIR",
    "FUZZY_LIB",
    # LLM Validator (lazy loaded)
    "LLMValidator",
    "validate_merged_json",
]
