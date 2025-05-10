"""
exporter.py
Handles export of climate analysis results to various formats
"""

import ee
import os
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from ipywidgets import widgets, VBox, HBox, Layout, HTML

class Exporter:
    """
    Handles export of climate analysis results to various formats
    """
    
    def __init__(self):
        """Initialize Exporter"""
        self.export_root = "Climate_Analysis_Tool_Exports"
        self.local_export_dir = os.path.expanduser("~/climate_tool_exports")
        
        # Create local export directory if it doesn't exist
        os.makedirs(self.local_export_dir, exist_ok=True)
    
    def export_current_view(self, format_type: str, panel_data: Dict[str, Any], 
                           status_callback: Optional[callable] = None) -> str:
        """
        Export currently displayed data
        
        Args:
            format_type: Export format type ('GeoTIFF', 'CSV', 'NetCDF')
            panel_data: Data for the panel
            status_callback: Optional callback for status updates
            
        Returns:
            Status message
        """
        try:
            # Update status
            if status_callback:
                status_callback("Starting export of current view data...")
            
            # Get export data
            data = panel_data.get('data')
            if data is None:
                return "Error: No data available for export"
            
            # Generate export name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dataset = panel_data.get('dataset', 'unknown')
            index = panel_data.get('index', 'unknown')
            year = panel_data.get('time_range', (2020, 2020))[1]  # Use end year
            
            export_name = f"{dataset}_{index}_{year}_{timestamp}"
            folder_name = f"{self.export_root}/{dataset}/{index}"
            
            # Export based on format
            if format_type == 'GeoTIFF':
                return self._export_geotiff(data, export_name, folder_name, status_callback)
            elif format_type == 'CSV':
                return self._export_csv(panel_data, export_name, status_callback)
            elif format_type == 'NetCDF':
                return self._export_netcdf(data, export_name, folder_name, status_callback)
            else:
                return f"Error: Unsupported export format: {format_type}"
                
        except Exception as e:
            error_msg = f"Export failed: {str(e)}"
            if status_callback:
                status_callback(error_msg)
            return error_msg
    
    def export_all_data(self, format_type: str, panel_data: Dict[str, Any],
                      status_callback: Optional[callable] = None) -> str:
        """
        Export all data in the selected time range
        
        Args:
            format_type: Export format type ('GeoTIFF', 'CSV', 'NetCDF')
            panel_data: Data for the panel
            status_callback: Optional callback for status updates
            
        Returns:
            Status message
        """
        try:
            # Update status
            if status_callback:
                status_callback("Starting export of all data...")
            
            # Get export parameters
            state = panel_data.get('state', {})
            if not state:
                return "Error: No analysis state available for export"
            
            # Get time range
            time_range = state.get('time_range', (2020, 2020))
            start_year, end_year = time_range
            
            # Generate export name base
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dataset = state.get('dataset', 'unknown')
            index = state.get('index', 'unknown')
            
            export_name_base = f"{dataset}_{index}_{start_year}_{end_year}_{timestamp}"
            folder_name = f"{self.export_root}/{dataset}/{index}"
            
            # Export based on format
            if format_type == 'GeoTIFF':
                return self._export_all_geotiff(panel_data, export_name_base, folder_name, status_callback)
            elif format_type == 'CSV':
                return self._export_all_csv(panel_data, export_name_base, status_callback)
            elif format_type == 'NetCDF':
                return self._export_all_netcdf(panel_data, export_name_base, folder_name, status_callback)
            else:
                return f"Error: Unsupported export format: {format_type}"
                
        except Exception as e:
            error_msg = f"Export failed: {str(e)}"
            if status_callback:
                status_callback(error_msg)
            return error_msg
    
    def _export_geotiff(self, image: ee.Image, export_name: str,
                      folder_name: str, status_callback: Optional[callable] = None) -> str:
        """
        Export data as GeoTIFF
        
        Args:
            image: Earth Engine image to export
            export_name: Name for export file
            folder_name: Folder name in Google Drive
            status_callback: Optional callback for status updates
            
        Returns:
            Status message
        """
        # Update status
        if status_callback:
            status_callback("Setting up GeoTIFF export to Google Drive...")
        
        # Create export task
        export_task = ee.batch.Export.image.toDrive(
            image=image,
            description=export_name,
            folder=folder_name,
            fileNamePrefix=export_name,
            crs='EPSG:4326',
            scale=1000,
            maxPixels=1e9,
            fileFormat='GeoTIFF'
        )
        
        # Start the task
        export_task.start()
        
        # Update status
        if status_callback:
            status_callback(f"GeoTIFF export started. The file will be saved to '{folder_name}' folder in your Google Drive.")
        
        return f"GeoTIFF export started. The file will be saved to '{folder_name}' folder in your Google Drive."
    
    def _export_csv(self, panel_data: Dict[str, Any], export_name: str,
                   status_callback: Optional[callable] = None) -> str:
        """
        Export temporal data as CSV
        
        Args:
            panel_data: Data for the panel
            export_name: Name for export file
            status_callback: Optional callback for status updates
            
        Returns:
            Status message
        """
        # Update status
        if status_callback:
            status_callback("Setting up CSV export...")
        
        # Get temporal data
        temporal_data = panel_data.get('temporal_data', [])
        if not temporal_data:
            return "Error: No temporal data available for CSV export"
        
        # Convert to DataFrame
        df = pd.DataFrame(temporal_data)
        
        # Generate filename
        filename = f"{export_name}.csv"
        filepath = os.path.join(self.local_export_dir, filename)
        
        # Save DataFrame
        df.to_csv(filepath, index=False)
        
        # Update status
        if status_callback:
            status_callback(f"CSV export completed. File saved to: {filepath}")
        
        return f"CSV export completed. File saved to: {filepath}"
    
    def _export_netcdf(self, image: ee.Image, export_name: str,
                      folder_name: str, status_callback: Optional[callable] = None) -> str:
        """
        Export data as NetCDF
        
        Args:
            image: Earth Engine image to export
            export_name: Name for export file
            folder_name: Folder name in Google Drive
            status_callback: Optional callback for status updates
            
        Returns:
            Status message
        """
        # Update status
        if status_callback:
            status_callback("Setting up NetCDF export to Google Drive...")
        
        # Create export task
        export_task = ee.batch.Export.image.toDrive(
            image=image,
            description=export_name,
            folder=folder_name,
            fileNamePrefix=export_name,
            crs='EPSG:4326',
            scale=1000,
            maxPixels=1e9,
            fileFormat='NetCDF'
        )
        
        # Start the task
        export_task.start()
        
        # Update status
        if status_callback:
            status_callback(f"NetCDF export started. The file will be saved to '{folder_name}' folder in your Google Drive.")
        
        return f"NetCDF export started. The file will be saved to '{folder_name}' folder in your Google Drive."
    
    def _export_all_geotiff(self, panel_data: Dict[str, Any], export_name_base: str,
                          folder_name: str, status_callback: Optional[callable] = None) -> str:
        """
        Export all years of data as GeoTIFF
        
        Args:
            panel_data: Data for the panel
            export_name_base: Base name for export files
            folder_name: Folder name in Google Drive
            status_callback: Optional callback for status updates
            
        Returns:
            Status message
        """
        # Update status
        if status_callback:
            status_callback("Starting export of all years as GeoTIFF...")
        
        # Get state
        state = panel_data.get('state', {})
        if not state:
            return "Error: No analysis state available for export"
        
        # Get time range
        time_range = state.get('time_range', (2020, 2020))
        start_year, end_year = time_range
        
        # Create special folder for this export
        batch_folder = f"{folder_name}/{export_name_base}"
        
        # Track number of export tasks
        task_count = 0
        
        # Create export tasks for each year
        for year in range(start_year, end_year + 1):
            try:
                # Get data for year
                year_data = self._get_data_for_year(panel_data, year)
                
                if year_data:
                    # Create export name
                    export_name = f"{export_name_base}_{year}"
                    
                    # Create export task
                    export_task = ee.batch.Export.image.toDrive(
                        image=year_data,
                        description=export_name,
                        folder=batch_folder,
                        fileNamePrefix=export_name,
                        crs='EPSG:4326',
                        scale=1000,
                        maxPixels=1e9,
                        fileFormat='GeoTIFF'
                    )
                    
                    # Start the task
                    export_task.start()
                    task_count += 1
                    
                    # Update status periodically
                    if status_callback and year % 5 == 0:
                        status_callback(f"Started export task for year {year}...")
            
            except Exception as e:
                if status_callback:
                    status_callback(f"Warning: Error exporting year {year}: {str(e)}")
        
        # Final status update
        status_message = f"Started {task_count} GeoTIFF export tasks. Files will be saved to '{batch_folder}' folder in your Google Drive."
        
        if status_callback:
            status_callback(status_message)
        
        return status_message
    
    def _export_all_csv(self, panel_data: Dict[str, Any], export_name_base: str,
                      status_callback: Optional[callable] = None) -> str:
        """
        Export all temporal data as CSV
        
        Args:
            panel_data: Data for the panel
            export_name_base: Base name for export file
            status_callback: Optional callback for status updates
            
        Returns:
            Status message
        """
        # Update status
        if status_callback:
            status_callback("Exporting all temporal data as CSV...")
        
        # Get temporal data
        temporal_data = panel_data.get('temporal_data', [])
        if not temporal_data:
            return "Error: No temporal data available for CSV export"
        
        # Convert to DataFrame
        df = pd.DataFrame(temporal_data)
        
        # Generate filename
        filename = f"{export_name_base}_temporal.csv"
        filepath = os.path.join(self.local_export_dir, filename)
        
        # Save DataFrame
        df.to_csv(filepath, index=False)
        
        # Update status
        if status_callback:
            status_callback(f"CSV export completed. File saved to: {filepath}")
        
        return f"CSV export completed. File saved to: {filepath}"
    
    def _export_all_netcdf(self, panel_data: Dict[str, Any], export_name_base: str,
                         folder_name: str, status_callback: Optional[callable] = None) -> str:
        """
        Export all years of data as NetCDF
        
        Args:
            panel_data: Data for the panel
            export_name_base: Base name for export files
            folder_name: Folder name in Google Drive
            status_callback: Optional callback for status updates
            
        Returns:
            Status message
        """
        # This is similar to _export_all_geotiff but for NetCDF format
        # Update status
        if status_callback:
            status_callback("Starting export of all years as NetCDF...")
        
        # Get state
        state = panel_data.get('state', {})
        if not state:
            return "Error: No analysis state available for export"
        
        # Get time range
        time_range = state.get('time_range', (2020, 2020))
        start_year, end_year = time_range
        
        # Create special folder for this export
        batch_folder = f"{folder_name}/{export_name_base}"
        
        # Track number of export tasks
        task_count = 0
        
        # Create export tasks for each year
        for year in range(start_year, end_year + 1):
            try:
                # Get data for year
                year_data = self._get_data_for_year(panel_data, year)
                
                if year_data:
                    # Create export name
                    export_name = f"{export_name_base}_{year}"
                    
                    # Create export task
                    export_task = ee.batch.Export.image.toDrive(
                        image=year_data,
                        description=export_name,
                        folder=batch_folder,
                        fileNamePrefix=export_name,
                        crs='EPSG:4326',
                        scale=1000,
                        maxPixels=1e9,
                        fileFormat='NetCDF'
                    )
                    
                    # Start the task
                    export_task.start()
                    task_count += 1
                    
                    # Update status periodically
                    if status_callback and year % 5 == 0:
                        status_callback(f"Started export task for year {year}...")
            
            except Exception as e:
                if status_callback:
                    status_callback(f"Warning: Error exporting year {year}: {str(e)}")
        
        # Final status update
        status_message = f"Started {task_count} NetCDF export tasks. Files will be saved to '{batch_folder}' folder in your Google Drive."
        
        if status_callback:
            status_callback(status_message)
        
        return status_message
    
    def _get_data_for_year(self, panel_data: Dict[str, Any], year: int) -> Optional[ee.Image]:
        """
        Get data for a specific year
        
        Args:
            panel_data: Data for the panel
            year: Year to retrieve data for
            
        Returns:
            Earth Engine image for the year or None if not available
        """
        # This is a placeholder implementation
        # In a real implementation, we would recalculate the data for the specific year
        # or retrieve it from a cache
        
        # For now, just return the current data as an example
        return panel_data.get('data')
    
    def create_status_widget(self) -> Tuple[widgets.HTML, callable]:
        """
        Create a widget for displaying export status
        
        Returns:
            Tuple of (status widget, status update function)
        """
        # Create status widget
        status_widget = HTML(value="<p>Ready for export</p>")
        
        # Create status update function
        def update_status(message: str):
            status_widget.value = f"<p>{message}</p>"
        
        return status_widget, update_status