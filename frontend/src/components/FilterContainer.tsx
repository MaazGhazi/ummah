"use client";

export interface Filter {
  id: string;
  name: string;
  enabled: boolean;
}

export interface FilterContainerProps {
  filters: Filter[];
  onFiltersChange: (filters: Filter[]) => void;
}

export default function FilterContainer({ filters, onFiltersChange }: FilterContainerProps) {
  const toggleFilter = (id: string) => {
    const updatedFilters = filters.map((filter) =>
      filter.id === id ? { ...filter, enabled: !filter.enabled } : filter
    );
    onFiltersChange(updatedFilters);
  };

  return (
    <div className="p-4 bg-gray-900 rounded-xl border border-gray-800 w-fit mx-auto">
      <h2 className="text-lg font-semibold mb-3">Content Filters</h2>
      <div className="flex flex-wrap gap-3">
        {filters.map((filter) => (
          <button
            key={filter.id}
            onClick={() => toggleFilter(filter.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-300 border cursor-pointer ${
              filter.enabled
                ? "bg-indigo-500/20 border-indigo-500 text-white"
                : "bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-600"
            }`}
          >
            {filter.name}
          </button>
        ))}
      </div>
    </div>
  );
}

// Default filters for initialization
export const defaultFilters: Filter[] = [
  {
    id: "music",
    name: "Music",
    enabled: true,
  },
  {
    id: "profanity",
    name: "Profanity",
    enabled: false,
  },
  {
    id: "nudity",
    name: "Nudity/Sexual",
    enabled: false,
  },
];
