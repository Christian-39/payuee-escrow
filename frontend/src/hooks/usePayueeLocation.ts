import { useState, useEffect, useCallback } from 'react';
import api from '../lib/api';

export interface City {
  state: string;
  city: string;
  ward: string;
  latitude: number;
  longitude: number;
  display: string;
}

export interface UsePayueeLocationReturn {
  states: string[];
  cities: City[];
  selectedState: string | null;
  selectedCity: City | null;
  loadingStates: boolean;
  loadingCities: boolean;
  locationError: string | null;
  fetchStates: () => Promise<void>;
  fetchCities: (state: string) => Promise<void>;
  setSelectedState: (state: string | null) => void;
  setSelectedCity: (city: City | null) => void;
}

export function usePayueeLocation(): UsePayueeLocationReturn {
  const [states, setStates] = useState<string[]>([]);
  const [cities, setCities] = useState<City[]>([]);
  const [selectedState, setSelectedState] = useState<string | null>(null);
  const [selectedCity, setSelectedCity] = useState<City | null>(null);
  const [loadingStates, setLoadingStates] = useState(false);
  const [loadingCities, setLoadingCities] = useState(false);
  const [locationError, setLocationError] = useState<string | null>(null);

  const fetchStates = useCallback(async () => {
    setLoadingStates(true);
    setLocationError(null);
    try {
      const response = await api.get('/payments/location/states/');
      if (response.data.success) {
        setStates(response.data.states || []);
      } else {
        setLocationError(response.data.error || 'Failed to load states');
      }
    } catch (err: any) {
      setLocationError(err.response?.data?.error || 'Failed to load states');
    } finally {
      setLoadingStates(false);
    }
  }, []);

  const fetchCities = useCallback(async (state: string) => {
    setLoadingCities(true);
    setLocationError(null);
    setCities([]);
    setSelectedCity(null);
    try {
      const response = await api.get(`/payments/location/cities/?state=${encodeURIComponent(state)}`);
      if (response.data.success) {
        setCities(response.data.cities || []);
      } else {
        setLocationError(response.data.error || 'Failed to load cities');
      }
    } catch (err: any) {
      setLocationError(err.response?.data?.error || 'Failed to load cities');
    } finally {
      setLoadingCities(false);
    }
  }, []);

  useEffect(() => {
    fetchStates();
  }, [fetchStates]);

  useEffect(() => {
    if (selectedState) {
      fetchCities(selectedState);
    } else {
      setCities([]);
      setSelectedCity(null);
    }
  }, [selectedState, fetchCities]);

  return {
    states,
    cities,
    selectedState,
    selectedCity,
    loadingStates,
    loadingCities,
    locationError,
    fetchStates,
    fetchCities,
    setSelectedState,
    setSelectedCity,
  };
}