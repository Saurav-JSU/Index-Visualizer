"""
data_manager.py
Manages climate datasets and their configurations
"""

import ee
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import json
import os

@dataclass
class DatasetConfig:
    """Configuration for a climate dataset"""
    id: str
    precip_key: str
    tmax_key: str
    tmin_key: str
    precip_conversion: float
    temp_conversion: float
    start_year: int
    end_year: int = datetime.now().year
    display_name: str = ""
    description: str = ""
    region_coverage: str = ""
    spatial_resolution: str = ""
    temporal_resolution: str = "daily"

class DataManager:
    """
    Manages climate datasets and their configurations
    """
    
    def __init__(self):
        """Initialize DataManager with default datasets"""
        self.datasets = {}
        self._initialize_default_datasets()
        self._load_custom_datasets()
    
    def _initialize_default_datasets(self):
        """Initialize default dataset configurations"""
        self.datasets = {
            "ERA5": DatasetConfig(
                id="ECMWF/ERA5_LAND/DAILY_AGGR",
                precip_key="total_precipitation_sum",
                tmax_key="temperature_2m_max",
                tmin_key="temperature_2m_min",
                precip_conversion=1000,  # Convert meters to millimeters
                temp_conversion=-273.15,  # Convert Kelvin to Celsius
                start_year=1980,
                display_name="ERA5 Land Reanalysis",
                description="High resolution reanalysis dataset for land surface variables",
                region_coverage="Global",
                spatial_resolution="0.1° (~11km)"
            ),
            "PRISM": DatasetConfig(
                id="OREGONSTATE/PRISM/AN81d",
                precip_key="ppt",
                tmax_key="tmax",
                tmin_key="tmin",
                precip_conversion=1,
                temp_conversion=0,
                start_year=1981,
                display_name="PRISM Climate Data",
                description="High-resolution climate data for the contiguous United States",
                region_coverage="Contiguous United States",
                spatial_resolution="4km"
            ),
            "DAYMET": DatasetConfig(
                id="NASA/ORNL/DAYMET_V4",
                precip_key="prcp",
                tmax_key="tmax",
                tmin_key="tmin",
                precip_conversion=1,
                temp_conversion=0,
                start_year=1980,
                display_name="DAYMET Version 4",
                description="Daily surface weather and climatological data",
                region_coverage="North America",
                spatial_resolution="1km"
            )
        }
    
    def _load_custom_datasets(self):
        """Load custom datasets from configuration file"""
        config_dir = os.path.expanduser("~/.climate_tool")
        config_file = os.path.join(config_dir, "custom_datasets.json")
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    custom_configs = json.load(f)
                
                for key, config in custom_configs.items():
                    self.datasets[key] = DatasetConfig(**config)
                    
            except Exception as e:
                print(f"Warning: Failed to load custom datasets: {str(e)}")
    
    def add_custom_dataset(self, key: str, config: Dict[str, Any]) -> bool:
        """
        Add a custom dataset configuration
        
        Args:
            key: Unique identifier for the dataset
            config: Configuration dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create config from dictionary
            dataset_config = DatasetConfig(**config)
            
            # Add to datasets
            self.datasets[key] = dataset_config
            
            # Save custom datasets
            self._save_custom_datasets()
            
            return True
        except Exception as e:
            print(f"Error adding custom dataset: {str(e)}")
            return False
    
    def _save_custom_datasets(self):
        """Save custom datasets to configuration file"""
        config_dir = os.path.expanduser("~/.climate_tool")
        os.makedirs(config_dir, exist_ok=True)
        config_file = os.path.join(config_dir, "custom_datasets.json")
        
        custom_configs = {}
        
        # Identify custom datasets (not in the default set)
        default_keys = ["ERA5", "PRISM", "DAYMET"]
        for key, config in self.datasets.items():
            if key not in default_keys:
                # Convert dataclass to dictionary
                custom_configs[key] = {
                    "id": config.id,
                    "precip_key": config.precip_key,
                    "tmax_key": config.tmax_key,
                    "tmin_key": config.tmin_key,
                    "precip_conversion": config.precip_conversion,
                    "temp_conversion": config.temp_conversion,
                    "start_year": config.start_year,
                    "end_year": config.end_year,
                    "display_name": config.display_name,
                    "description": config.description,
                    "region_coverage": config.region_coverage,
                    "spatial_resolution": config.spatial_resolution,
                    "temporal_resolution": config.temporal_resolution
                }
        
        try:
            with open(config_file, 'w') as f:
                json.dump(custom_configs, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save custom datasets: {str(e)}")
    
    def get_dataset_config(self, dataset_name: str) -> DatasetConfig:
        """
        Get configuration for a specific dataset
        
        Args:
            dataset_name: Name of the dataset
            
        Returns:
            DatasetConfig object for the dataset
            
        Raises:
            ValueError: If dataset_name is not found
        """
        if dataset_name not in self.datasets:
            raise ValueError(f"Dataset not found: {dataset_name}")
        
        return self.datasets[dataset_name]
    
    def list_datasets(self) -> List[str]:
        """
        Get list of available dataset names
        
        Returns:
            List of dataset names
        """
        return list(self.datasets.keys())
    
    def get_dataset_info(self, dataset_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a dataset
        
        Args:
            dataset_name: Name of the dataset
            
        Returns:
            Dictionary with dataset information
        """
        config = self.get_dataset_config(dataset_name)
        
        return {
            "name": dataset_name,
            "display_name": config.display_name,
            "description": config.description,
            "region_coverage": config.region_coverage,
            "spatial_resolution": config.spatial_resolution,
            "temporal_resolution": config.temporal_resolution,
            "year_range": (config.start_year, config.end_year),
            "earth_engine_id": config.id
        }
    
    def get_ee_collection(self, dataset_name: str, start_date: str, 
                        end_date: str, geometry: ee.Geometry) -> ee.ImageCollection:
        """
        Get Earth Engine ImageCollection for a dataset
        
        Args:
            dataset_name: Name of the dataset
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            geometry: Earth Engine geometry defining the region of interest
            
        Returns:
            Filtered Earth Engine ImageCollection
        """
        config = self.get_dataset_config(dataset_name)
        
        # Create and filter collection
        collection = ee.ImageCollection(config.id) \
            .filterDate(start_date, end_date) \
            .filterBounds(geometry)
        
        # Check if collection has images
        if collection.size().getInfo() == 0:
            raise ValueError(f"No data available for {dataset_name} in the specified date range")
        
        return collection
    
    def get_variable_key(self, dataset_name: str, variable_type: str) -> str:
        """
        Get dataset-specific key for a variable
        
        Args:
            dataset_name: Name of the dataset
            variable_type: Type of variable ('precip', 'tmax', or 'tmin')
            
        Returns:
            Dataset-specific key for the variable
        """
        config = self.get_dataset_config(dataset_name)
        
        key_mapping = {
            'precip': config.precip_key,
            'tmax': config.tmax_key,
            'tmin': config.tmin_key
        }
        
        if variable_type not in key_mapping:
            raise ValueError(f"Unknown variable type: {variable_type}")
        
        return key_mapping[variable_type]
    
    def get_conversion_factor(self, dataset_name: str, variable_type: str) -> float:
        """
        Get conversion factor for a variable
        
        Args:
            dataset_name: Name of the dataset
            variable_type: Type of variable ('precip' or 'temp')
            
        Returns:
            Conversion factor for the variable
        """
        config = self.get_dataset_config(dataset_name)
        
        if variable_type == 'precip':
            return config.precip_conversion
        elif variable_type in ['temp', 'tmax', 'tmin']:
            return config.temp_conversion
        else:
            raise ValueError(f"Unknown variable type: {variable_type}")
    
    def validate_date_range(self, dataset_name: str, start_date: str, end_date: str) -> bool:
        """
        Validate if date range is available for a dataset
        
        Args:
            dataset_name: Name of the dataset
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            True if date range is valid, False otherwise
        """
        config = self.get_dataset_config(dataset_name)
        
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            
            # Check if years are within dataset range
            if not (config.start_year <= start.year <= config.end_year and 
                   config.start_year <= end.year <= config.end_year):
                return False
            
            # Check if start date is before end date
            if start > end:
                return False
            
            return True
        except ValueError:
            return False