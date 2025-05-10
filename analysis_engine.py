"""
analysis_engine.py
Core engine for climate data analysis and index calculation
"""

import ee
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from enum import Enum
from dataclasses import dataclass

from data_manager import DataManager

class IndexCategory(Enum):
    """Categories of climate indices"""
    PRECIPITATION = "Precipitation"
    TEMPERATURE = "Temperature"

@dataclass
class IndexInfo:
    """Information about a climate index"""
    name: str
    category: IndexCategory
    description: str
    units: str
    requires_daily: bool = True
    min_vis_value: float = 0
    max_vis_value: float = 100
    palette: List[str] = None

class AnalysisEngine:
    """
    Core engine for climate data analysis and index calculation
    """
    
    # Define available indices
    AVAILABLE_INDICES = {
        # Precipitation indices
        "Annual total precipitation": IndexInfo(
            name="Annual total precipitation",
            category=IndexCategory.PRECIPITATION,
            description="Total precipitation over the year",
            units="mm/year",
            min_vis_value=0,
            max_vis_value=3000,
            palette=['#deebf7', '#9ecae1', '#3182bd']
        ),
        "Annual maximum 1-day precipitation": IndexInfo(
            name="Annual maximum 1-day precipitation",
            category=IndexCategory.PRECIPITATION,
            description="Maximum 1-day precipitation amount",
            units="mm/day",
            min_vis_value=0,
            max_vis_value=150,
            palette=['#deebf7', '#9ecae1', '#3182bd']
        ),
        "Number of wet days": IndexInfo(
            name="Number of wet days",
            category=IndexCategory.PRECIPITATION,
            description="Annual count of days with precipitation ≥1mm",
            units="days",
            min_vis_value=0,
            max_vis_value=365,
            palette=['#fee5d9', '#fcae91', '#fb6a4a', '#de2d26', '#a50f15']
        ),
        "Consecutive dry days": IndexInfo(
            name="Consecutive dry days",
            category=IndexCategory.PRECIPITATION,
            description="Maximum number of consecutive dry days (precipitation <1mm)",
            units="days",
            min_vis_value=0,
            max_vis_value=100,
            palette=['#fee5d9', '#fcae91', '#fb6a4a', '#de2d26', '#a50f15']
        ),
        
        # Temperature indices
        "Annual maximum temperature": IndexInfo(
            name="Annual maximum temperature",
            category=IndexCategory.TEMPERATURE,
            description="Maximum value of daily maximum temperature",
            units="°C",
            min_vis_value=-10,
            max_vis_value=45,
            palette=['#2166ac', '#67a9cf', '#f7f7f7', '#fddbc7', '#ef8a62', '#b2182b']
        ),
        "Annual minimum temperature": IndexInfo(
            name="Annual minimum temperature",
            category=IndexCategory.TEMPERATURE,
            description="Minimum value of daily minimum temperature",
            units="°C",
            min_vis_value=-30,
            max_vis_value=25,
            palette=['#2166ac', '#67a9cf', '#f7f7f7', '#fddbc7', '#ef8a62', '#b2182b']
        ),
        "Frost days": IndexInfo(
            name="Frost days",
            category=IndexCategory.TEMPERATURE,
            description="Annual count of days with minimum temperature < 0°C",
            units="days",
            min_vis_value=0,
            max_vis_value=365,
            palette=['#fee5d9', '#fcae91', '#fb6a4a', '#de2d26', '#a50f15']
        ),
        "Summer days": IndexInfo(
            name="Summer days",
            category=IndexCategory.TEMPERATURE,
            description="Annual count of days with maximum temperature > 25°C",
            units="days",
            min_vis_value=0,
            max_vis_value=365,
            palette=['#deebf7', '#9ecae1', '#3182bd']
        )
    }
    
    def __init__(self, data_manager: DataManager):
        """
        Initialize AnalysisEngine
        
        Args:
            data_manager: DataManager instance
        """
        self.data_manager = data_manager
    
    def analyze(self, geometry: ee.Geometry, start_year: int, end_year: int, 
            dataset: str, parameter: str, index: str) -> Dict[str, Any]:
        """
        Run analysis for the specified parameters with better visualization params
        
        Args:
            geometry: Earth Engine geometry defining the region
            start_year: Start year for analysis
            end_year: End year for analysis
            dataset: Dataset name (e.g., 'ERA5')
            parameter: Parameter type ('Precipitation' or 'Temperature')
            index: Index name
            
        Returns:
            Dictionary with analysis results
        """
        # Validate inputs
        if index not in self.AVAILABLE_INDICES:
            raise ValueError(f"Unknown index: {index}")
            
        if start_year > end_year:
            raise ValueError("Start year must be less than or equal to end year")
            
        # Get index info
        index_info = self.AVAILABLE_INDICES[index]
        
        # Check parameter match
        if index_info.category.value != parameter:
            raise ValueError(f"Index {index} is not a {parameter} index")
        
        # Initialize results
        results = {
            "index": index,
            "parameter": parameter,
            "dataset": dataset,
            "time_range": (start_year, end_year),
            "units": index_info.units,
            "temporal_data": [],
            "data": None,
            "vis_params": {
                "min": index_info.min_vis_value,
                "max": index_info.max_vis_value,
                "palette": index_info.palette or ['#deebf7', '#9ecae1', '#3182bd'],
                "opacity": 0.8
            }
        }
        
        # Process each year
        final_result = None
        for year in range(start_year, end_year + 1):
            # Define date range for year
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"
            
            # Calculate index for year
            try:
                result = self._calculate_index(
                    geometry=geometry,
                    start_date=start_date,
                    end_date=end_date,
                    dataset=dataset,
                    index=index
                )
                
                # Use the last year's result as the main result
                if year == end_year:
                    final_result = result
                
                # Calculate mean value for year
                mean_val = result.reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=geometry,
                    scale=1000,
                    maxPixels=1e9
                ).getInfo()
                
                # Get the first value (there should only be one)
                value = next(iter(mean_val.values()), None)
                
                if value is not None:
                    results["temporal_data"].append({
                        "year": year,
                        "value": value
                    })
            except Exception as e:
                print(f"Warning: Error processing year {year}: {str(e)}")
        
        # Set final result
        if final_result is not None:
            results["data"] = final_result.clip(geometry)
            
            # Try to calculate better min/max values from the data
            try:
                # Use percentile stretch for better visualization
                stats = final_result.reduceRegion(
                    reducer=ee.Reducer.percentile([2, 98]),
                    geometry=geometry,
                    scale=1000,
                    maxPixels=1e9
                ).getInfo()
                
                # Extract percentile values
                band_keys = list(stats.keys())
                if band_keys and len(band_keys) >= 2:
                    # Sort keys to ensure p2 comes before p98
                    band_keys.sort()
                    p2 = stats.get(band_keys[0])
                    p98 = stats.get(band_keys[1])
                    
                    # Only update if we got valid values
                    if p2 is not None and p98 is not None:
                        results["vis_params"]["min"] = p2
                        results["vis_params"]["max"] = p98
            except Exception as e:
                print(f"Warning: Could not calculate optimal visualization parameters: {str(e)}")
        
        return results
    
    def _calculate_index(self, geometry: ee.Geometry, start_date: str, 
                       end_date: str, dataset: str, index: str) -> ee.Image:
        """
        Calculate climate index for a specific date range
        
        Args:
            geometry: Earth Engine geometry defining the region
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            dataset: Dataset name
            index: Index name
            
        Returns:
            Earth Engine image with calculated index
        """
        # Get index info
        index_info = self.AVAILABLE_INDICES[index]
        
        # Get collection
        collection = self.data_manager.get_ee_collection(
            dataset_name=dataset,
            start_date=start_date,
            end_date=end_date,
            geometry=geometry
        )
        
        # Calculate index based on category
        if index_info.category == IndexCategory.PRECIPITATION:
            return self._calculate_precipitation_index(collection, dataset, index)
        elif index_info.category == IndexCategory.TEMPERATURE:
            return self._calculate_temperature_index(collection, dataset, index)
        else:
            raise ValueError(f"Unknown index category: {index_info.category}")
    
    def _calculate_precipitation_index(self, collection: ee.ImageCollection, 
                                    dataset: str, index: str) -> ee.Image:
        """
        Calculate precipitation index
        
        Args:
            collection: Earth Engine ImageCollection
            dataset: Dataset name
            index: Index name
            
        Returns:
            Earth Engine image with calculated index
        """
        precip_key = self.data_manager.get_variable_key(dataset, 'precip')
        precip_conversion = self.data_manager.get_conversion_factor(dataset, 'precip')
        
        # Calculate threshold values based on dataset's conversion factor
        mm1_threshold = ee.Number(1).divide(precip_conversion)
        
        if index == "Annual total precipitation":
            # Sum precipitation for the period
            result = collection.select(precip_key).sum()
            return result.multiply(precip_conversion)
            
        elif index == "Annual maximum 1-day precipitation":
            # Find maximum 1-day precipitation
            result = collection.select(precip_key).max()
            return result.multiply(precip_conversion)
            
        elif index == "Number of wet days":
            # Count days with precipitation >= 1mm
            result = collection.select(precip_key).map(
                lambda img: img.gt(mm1_threshold)
            ).sum()
            return result
            
        elif index == "Consecutive dry days":
            # This calculation is more complex and requires a specialized algorithm
            # For simplicity, this is a placeholder implementation
            # In a real implementation, we would calculate runs of consecutive dry days
            max_consecutive = ee.Number(30)  # Placeholder
            return ee.Image.constant(max_consecutive)
        
        else:
            raise ValueError(f"Calculation not implemented for index: {index}")
    
    def _calculate_temperature_index(self, collection: ee.ImageCollection, 
                                   dataset: str, index: str) -> ee.Image:
        """
        Calculate temperature index
        
        Args:
            collection: Earth Engine ImageCollection
            dataset: Dataset name
            index: Index name
            
        Returns:
            Earth Engine image with calculated index
        """
        tmax_key = self.data_manager.get_variable_key(dataset, 'tmax')
        tmin_key = self.data_manager.get_variable_key(dataset, 'tmin')
        temp_conversion = self.data_manager.get_conversion_factor(dataset, 'temp')
        
        # Convert threshold values based on dataset's temperature conversion
        temp0C = ee.Number(0).subtract(temp_conversion)
        temp25C = ee.Number(25).subtract(temp_conversion)
        
        if index == "Annual maximum temperature":
            # Find maximum temperature
            result = collection.select(tmax_key).max()
            return result.add(temp_conversion)
            
        elif index == "Annual minimum temperature":
            # Find minimum temperature
            result = collection.select(tmin_key).min()
            return result.add(temp_conversion)
            
        elif index == "Frost days":
            # Count days with minimum temperature < 0°C
            result = collection.select(tmin_key).map(
                lambda img: img.lt(temp0C)
            ).sum()
            return result
            
        elif index == "Summer days":
            # Count days with maximum temperature > 25°C
            result = collection.select(tmax_key).map(
                lambda img: img.gt(temp25C)
            ).sum()
            return result
        
        else:
            raise ValueError(f"Calculation not implemented for index: {index}")
    
    def get_index_info(self, index_name: str) -> Dict[str, Any]:
        """
        Get information about a climate index
        
        Args:
            index_name: Name of the index
            
        Returns:
            Dictionary with index information
            
        Raises:
            ValueError: If index_name is not found
        """
        if index_name not in self.AVAILABLE_INDICES:
            raise ValueError(f"Unknown index: {index_name}")
        
        index_info = self.AVAILABLE_INDICES[index_name]
        
        return {
            "name": index_info.name,
            "category": index_info.category.value,
            "description": index_info.description,
            "units": index_info.units,
            "requires_daily": index_info.requires_daily,
            "visualization": {
                "min": index_info.min_vis_value,
                "max": index_info.max_vis_value,
                "palette": index_info.palette
            }
        }
    
    def list_indices(self, category: Optional[str] = None) -> List[str]:
        """
        List available indices
        
        Args:
            category: Optional category filter ('Precipitation' or 'Temperature')
            
        Returns:
            List of index names
        """
        if category:
            category_enum = IndexCategory(category)
            return [name for name, info in self.AVAILABLE_INDICES.items() 
                   if info.category == category_enum]
        else:
            return list(self.AVAILABLE_INDICES.keys())
    
    def add_custom_index(self, name: str, info: Dict[str, Any]) -> bool:
        """
        Add a custom index
        
        Args:
            name: Index name
            info: Index information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create index info
            category = IndexCategory(info.get("category", "Precipitation"))
            
            index_info = IndexInfo(
                name=name,
                category=category,
                description=info.get("description", ""),
                units=info.get("units", ""),
                requires_daily=info.get("requires_daily", True),
                min_vis_value=info.get("min_vis_value", 0),
                max_vis_value=info.get("max_vis_value", 100),
                palette=info.get("palette", ['#deebf7', '#9ecae1', '#3182bd'])
            )
            
            # Add to available indices
            self.AVAILABLE_INDICES[name] = index_info
            
            return True
        except Exception as e:
            print(f"Error adding custom index: {str(e)}")
            return False