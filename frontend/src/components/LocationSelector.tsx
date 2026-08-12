import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MapPin, ChevronDown, Loader2, Navigation } from 'lucide-react';
import { usePayueeLocation } from '../hooks/usePayueeLocation';
import { useDropdownClose } from '../hooks/useDropdownClose';
import { cn } from '../lib/utils';

interface LocationSelectorProps {
  onSelect: (location: {
    state: string;
    city: string;
    ward: string;
    latitude: number;
    longitude: number;
    display: string;
  }) => void;
  className?: string;
}

export default function LocationSelector({ onSelect, className }: LocationSelectorProps) {
  const {
    states,
    cities,
    selectedState,
    selectedCity,
    loadingStates,
    loadingCities,
    error,
    setSelectedState,
    setSelectedCity,
  } = usePayueeLocation();

  const [stateOpen, setStateOpen] = useState(false);
  const [cityOpen, setCityOpen] = useState(false);
  const stateRef = useDropdownClose<HTMLDivElement>(stateOpen, () => setStateOpen(false));
  const cityRef = useDropdownClose<HTMLDivElement>(cityOpen, () => setCityOpen(false));

  const handleCitySelect = (city: typeof selectedCity) => {
    if (!city) return;
    setSelectedCity(city);
    setCityOpen(false);
    onSelect({
      state: city.state,
      city: city.city,
      ward: city.ward,
      latitude: city.latitude,
      longitude: city.longitude,
      display: city.display,
    });
  };

  return (
    <div className={cn('space-y-4', className)}>
      {error && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm rounded-xl">
          {error}
        </div>
      )}

      {/* State Selector */}
      <div className="relative" ref={stateRef}>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          State
        </label>
        <button
          onClick={() => setStateOpen(!stateOpen)}
          disabled={loadingStates}
          className={cn(
            'w-full flex items-center justify-between px-4 py-3 rounded-xl border transition-all',
            stateOpen
              ? 'border-purple-500 ring-2 ring-purple-500/20'
              : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
          )}
        >
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-gray-400" />
            <span className={selectedState ? 'text-gray-900 dark:text-white' : 'text-gray-400'}>
              {selectedState || 'Select state'}
            </span>
          </div>
          {loadingStates ? (
            <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
          ) : (
            <ChevronDown className={cn('w-4 h-4 text-gray-400 transition-transform', stateOpen && 'rotate-180')} />
          )}
        </button>

        <AnimatePresence>
          {stateOpen && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="absolute z-50 w-full mt-2 max-h-60 overflow-y-auto bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg"
            >
              {states.map((state) => (
                <button
                  key={state}
                  onClick={() => {
                    setSelectedState(state);
                    setStateOpen(false);
                    setCityOpen(false);
                  }}
                  className={cn(
                    'w-full text-left px-4 py-3 text-sm hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors',
                    selectedState === state && 'bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400'
                  )}
                >
                  {state}
                </button>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* City/Ward Selector */}
      <div className="relative" ref={cityRef}>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          City / Area
        </label>
        <button
          onClick={() => selectedState && setCityOpen(!cityOpen)}
          disabled={!selectedState || loadingCities}
          className={cn(
            'w-full flex items-center justify-between px-4 py-3 rounded-xl border transition-all',
            !selectedState && 'opacity-50 cursor-not-allowed',
            cityOpen
              ? 'border-purple-500 ring-2 ring-purple-500/20'
              : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
          )}
        >
          <div className="flex items-center gap-2">
            <Navigation className="w-4 h-4 text-gray-400" />
            <span className={selectedCity ? 'text-gray-900 dark:text-white' : 'text-gray-400'}>
              {selectedCity?.display || (selectedState ? 'Select area' : 'Select state first')}
            </span>
          </div>
          {loadingCities ? (
            <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
          ) : (
            <ChevronDown className={cn('w-4 h-4 text-gray-400 transition-transform', cityOpen && 'rotate-180')} />
          )}
        </button>

        <AnimatePresence>
          {cityOpen && selectedState && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="absolute z-50 w-full mt-2 max-h-60 overflow-y-auto bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg"
            >
              {cities.map((city, index) => (
                <button
                  key={`${city.city}-${city.ward}-${index}`}
                  onClick={() => handleCitySelect(city)}
                  className={cn(
                    'w-full text-left px-4 py-3 text-sm hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors',
                    selectedCity?.display === city.display && 'bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400'
                  )}
                >
                  <div className="font-medium">{city.display}</div>
                  <div className="text-xs text-gray-400 mt-0.5">
                    {city.latitude.toFixed(4)}, {city.longitude.toFixed(4)}
                  </div>
                </button>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Selected Location Display */}
      {selectedCity && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-xl border border-purple-100 dark:border-purple-800"
        >
          <div className="flex items-start gap-3">
            <div className="p-2 bg-purple-100 dark:bg-purple-800 rounded-lg">
              <MapPin className="w-4 h-4 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-purple-900 dark:text-purple-300">
                {selectedCity.display}
              </p>
              <p className="text-xs text-purple-600 dark:text-purple-400 mt-1">
                {selectedCity.state} • Lat: {selectedCity.latitude}, Lon: {selectedCity.longitude}
              </p>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}