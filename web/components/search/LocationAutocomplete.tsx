"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

const POSTCODES_IO_URL =
  process.env.NEXT_PUBLIC_POSTCODES_IO_URL ?? "https://api.postcodes.io";

interface PostcodeResult {
  postcode: string;
  latitude: number;
  longitude: number;
  admin_district: string | null;
}

export function LocationAutocomplete() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [query, setQuery] = useState(searchParams.get("location") ?? "");
  const [suggestions, setSuggestions] = useState<PostcodeResult[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const listRef = useRef<HTMLUListElement>(null);

  const fetchSuggestions = useCallback(async (input: string) => {
    if (input.length < 2) {
      setSuggestions([]);
      setIsOpen(false);
      return;
    }

    try {
      const response = await fetch(
        `${POSTCODES_IO_URL}/postcodes/${encodeURIComponent(input)}/autocomplete`,
      );
      if (!response.ok) return;

      const data = (await response.json()) as {
        result: string[] | null;
      };

      if (!data.result || data.result.length === 0) {
        setSuggestions([]);
        setIsOpen(false);
        return;
      }

      // Fetch full postcode data for lat/lng
      const lookupResponse = await fetch(`${POSTCODES_IO_URL}/postcodes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ postcodes: data.result.slice(0, 5) }),
      });

      if (!lookupResponse.ok) return;

      const lookupData = (await lookupResponse.json()) as {
        result: Array<{
          result: PostcodeResult | null;
        }>;
      };

      const results = lookupData.result
        .map((r) => r.result)
        .filter((r): r is PostcodeResult => r !== null);

      setSuggestions(results);
      setIsOpen(results.length > 0);
      setActiveIndex(-1);
    } catch {
      // Silently fail — postcode lookup is non-critical
    }
  }, []);

  const handleInput = useCallback(
    (value: string) => {
      setQuery(value);
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => fetchSuggestions(value), 200);
    },
    [fetchSuggestions],
  );

  const selectSuggestion = useCallback(
    (suggestion: PostcodeResult) => {
      setQuery(suggestion.postcode);
      setIsOpen(false);
      setSuggestions([]);

      const params = new URLSearchParams(searchParams.toString());
      params.set("lat", String(suggestion.latitude));
      params.set("lng", String(suggestion.longitude));
      params.set("location", suggestion.postcode);
      params.delete("page");
      router.push(`/search?${params.toString()}`);
    },
    [searchParams, router],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!isOpen) return;

      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          setActiveIndex((prev) =>
            prev < suggestions.length - 1 ? prev + 1 : prev,
          );
          break;
        case "ArrowUp":
          e.preventDefault();
          setActiveIndex((prev) => (prev > 0 ? prev - 1 : -1));
          break;
        case "Enter":
          e.preventDefault();
          if (activeIndex >= 0 && suggestions[activeIndex]) {
            selectSuggestion(suggestions[activeIndex]);
          }
          break;
        case "Escape":
          setIsOpen(false);
          break;
      }
    },
    [isOpen, activeIndex, suggestions, selectSuggestion],
  );

  // Close dropdown on outside click
  useEffect(() => {
    const handler = () => setIsOpen(false);
    document.addEventListener("click", handler);
    return () => document.removeEventListener("click", handler);
  }, []);

  const activeDescendant =
    activeIndex >= 0 ? `location-option-${activeIndex}` : undefined;

  return (
    <div className="relative" onClick={(e) => e.stopPropagation()}>
      <label htmlFor="location-input" className="sr-only">
        Location
      </label>
      <input
        id="location-input"
        type="text"
        role="combobox"
        aria-label="Enter postcode or city"
        aria-expanded={isOpen}
        aria-autocomplete="list"
        aria-controls="location-listbox"
        aria-activedescendant={activeDescendant}
        placeholder="Enter postcode or city"
        value={query}
        onChange={(e) => handleInput(e.target.value)}
        onKeyDown={handleKeyDown}
        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      {isOpen && suggestions.length > 0 && (
        <ul
          id="location-listbox"
          ref={listRef}
          role="listbox"
          className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md border border-gray-200 bg-white shadow-lg"
        >
          {suggestions.map((s, i) => (
            <li
              key={s.postcode}
              id={`location-option-${i}`}
              role="option"
              aria-selected={i === activeIndex}
              onClick={() => selectSuggestion(s)}
              className={`cursor-pointer px-3 py-2 text-sm ${
                i === activeIndex ? "bg-blue-50 text-blue-700" : "text-gray-700"
              } hover:bg-gray-50`}
            >
              <span className="font-medium">{s.postcode}</span>
              {s.admin_district && (
                <span className="ml-2 text-gray-500">
                  {s.admin_district}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
