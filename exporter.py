"""
exporter.py
Enhanced exporter for climate analysis results with local export priority, chunking, and fallback options
"""

import ee
import os
import pandas as pd
import numpy as np
import geemap
import rasterio
import xarray as xr
import geopandas as gpd
import math
import time
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from ipywidgets import widgets, VBox, HBox, Layout, HTML

class Exporter:
    """
    Enhanced exporter for climate analysis results with improved local export, chunking, and GDrive fallback
    """
    
    def __init__(self):
        """Initialize Exporter with enhanced folder structure"""
        # Base export directory using normpath to ensure consistent separators
        self.export_root = "Climate_Analysis_Tool_Exports"
        self.local_export_dir = os.path.normpath(os.path.expanduser("~/climate_tool_exports"))
        
        # Maximum sizes for different export types before chunking
        self.max_pixels_no_chunk = 5000000  # ~5 million pixels before spatial chunking
        self.max_file_size_mb = 500  # Maximum file size in MB before chunking
        self.max_rows_csv = 1000000  # Maximum rows in CSV before chunking
        
        # Create enhanced local directory structure
        self._ensure_export_directories()
    
    def _ensure_export_directories(self):
        """Ensure all necessary export directories exist with proper structure"""
        # Create main export directory
        os.makedirs(self.local_export_dir, exist_ok=True)
        
        # Create directories for different export types
        export_types = ['GeoTIFF', 'CSV', 'NetCDF']
        for export_type in export_types:
            os.makedirs(os.path.join(self.local_export_dir, export_type), exist_ok=True)
            
            # Create common subdirectories for better organization
            common_dirs = [
                os.path.join(export_type, 'ERA5'),
                os.path.join(export_type, 'PRISM'),
                os.path.join(export_type, 'DAYMET'),
                os.path.join(export_type, 'Custom')
            ]
            
            for dir_path in common_dirs:
                os.makedirs(os.path.join(self.local_export_dir, dir_path), exist_ok=True)
        
        # Create temporary directory for processing
        os.makedirs(os.path.join(self.local_export_dir, 'temp'), exist_ok=True)
    
    def export_current_view(self, format_type: str, panel_data: Dict[str, Any], 
                          status_callback: Optional[callable] = None) -> str:
        """
        Export currently displayed data with enhanced local export capabilities
        
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
            folder_name = f"{dataset}/{index}"
            
            # Export based on format
            if format_type == 'GeoTIFF':
                return self._export_geotiff_enhanced(data, export_name, folder_name, status_callback)
            elif format_type == 'CSV':
                return self._export_csv_enhanced(panel_data, export_name, folder_name, status_callback)
            elif format_type == 'NetCDF':
                return self._export_netcdf_enhanced(data, export_name, folder_name, status_callback)
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
        Export all data in the selected time range with enhanced capabilities
        
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
            folder_name = f"{dataset}/{index}"
            
            # Export based on format
            if format_type == 'GeoTIFF':
                return self._export_all_geotiff_enhanced(panel_data, export_name_base, folder_name, status_callback)
            elif format_type == 'CSV':
                return self._export_all_csv_enhanced(panel_data, export_name_base, folder_name, status_callback)
            elif format_type == 'NetCDF':
                return self._export_all_netcdf_enhanced(panel_data, export_name_base, folder_name, status_callback)
            else:
                return f"Error: Unsupported export format: {format_type}"
                
        except Exception as e:
            error_msg = f"Export failed: {str(e)}"
            if status_callback:
                status_callback(error_msg)
            return error_msg
    
    def _export_geotiff_enhanced(self, image: ee.Image, export_name: str,
                            folder_name: str, status_callback: Optional[callable] = None) -> str:
        # Update status
        if status_callback:
            status_callback("Setting up GeoTIFF export, checking image size...")
        
        # Fix folder_name: replace default values with better names if necessary
        if "unknown" in folder_name:
            folder_name = folder_name.replace("unknown", "climate_data")
        
        # Create proper local directory (with consistent path separators)
        local_folder = os.path.join(self.local_export_dir, 'GeoTIFF', *folder_name.split('/'))
        os.makedirs(local_folder, exist_ok=True)
        local_file_path = os.path.join(local_folder, f"{export_name}.tif")
        
        # Log the export path
        print(f"Exporting to: {local_file_path}")
        
        try:
            # Check image size/complexity using a simple measure
            # For example, checking the area in pixels at a particular scale
            try:
                image_info = image.getInfo()
                bands = image_info.get('bands', [])
                if bands:
                    # Get dimensions from the first band
                    size_estimate = 0
                    for band in bands:
                        dimensions = band.get('dimensions', [0, 0])
                        size_estimate += dimensions[0] * dimensions[1]
                else:
                    # If we can't get dimensions, estimate based on bounds
                    bounds = image.geometry().bounds()
                    area_km2 = bounds.area().divide(1000 * 1000).getInfo()
                    # Approximate size in pixels at 500m resolution
                    size_estimate = area_km2 * 4  # 500m x 500m = 0.25 km2 per pixel
                
                needs_chunking = size_estimate > self.max_pixels_no_chunk
            except:
                # If we can't estimate size, assume it's large
                needs_chunking = True
            
            # Attempt local export
            if needs_chunking:
                if status_callback:
                    status_callback("Large image detected, using spatial chunking for local export...")
                return self._chunked_geotiff_local_export(image, export_name, local_folder, status_callback)
            else:
                if status_callback:
                    status_callback("Image size acceptable, exporting directly to local file...")
                
                # Try direct local export using geemap
                try:
                    # Get projection info from the image
                    crs = image.projection().getInfo()['crs']
                    scale = 500  # Default scale in meters
                    
                    # Create bounds for the export
                    region = image.geometry().bounds().getInfo()['coordinates']
                    
                    # Use geemap to download the image
                    task = geemap.ee_export_image(
                        image, 
                        filename=local_file_path,
                        scale=scale,
                        region=region,
                        crs=crs,
                        file_per_band=False
                    )
                    
                    # Wait for the task to complete
                    if status_callback:
                        status_callback("Downloading GeoTIFF to local file, please wait...")
                    
                    # Check if the file was created successfully
                    if os.path.exists(local_file_path):
                        file_size_mb = os.path.getsize(local_file_path) / (1024 * 1024)
                        return f"GeoTIFF export completed successfully. File saved to: {local_file_path} ({file_size_mb:.2f} MB)"
                    else:
                        raise Exception("Export failed, file not created")
                        
                except Exception as e:
                    if status_callback:
                        status_callback(f"Local export failed: {str(e)}. Trying Google Drive export...")
                    
                    # Fall back to Google Drive
                    return self._export_geotiff_to_drive(image, export_name, folder_name, status_callback)
        
        except Exception as e:
            # Final fallback to Google Drive
            if status_callback:
                status_callback(f"Error during export process: {str(e)}. Falling back to Google Drive...")
            
            return self._export_geotiff_to_drive(image, export_name, folder_name, status_callback)
        
    def _chunked_geotiff_local_export(self, image: ee.Image, export_name: str,
                                folder_name: str, status_callback: Optional[callable] = None) -> str:
        """Export large GeoTIFF image by splitting it into spatial chunks"""
        """
        Export large GeoTIFF image by splitting it into spatial chunks
        
        Args:
            image: Earth Engine image to export
            export_name: Base name for export files
            local_folder: Local folder for saving files
            status_callback: Optional callback for status updates
            
        Returns:
            Status message
        """
        try:
            # Get the image bounds
            bounds = image.geometry().bounds().getInfo()
            coords = bounds['coordinates'][0]
            
            # Calculate the bounds dimensions
            min_x = min(c[0] for c in coords)
            min_y = min(c[1] for c in coords)
            max_x = max(c[0] for c in coords)
            max_y = max(c[1] for c in coords)
            
            # Determine the number of chunks (2x2 grid is usually a good start)
            # For very large images, could go to 3x3 or 4x4
            num_chunks_x = 2
            num_chunks_y = 2
            
            # Create temp directory for chunks
            chunk_dir = os.path.normpath(os.path.join(self.local_export_dir, 'temp', f"{export_name}_chunks"))
            os.makedirs(chunk_dir, exist_ok=True)
            
            # Calculate chunk sizes
            x_size = (max_x - min_x) / num_chunks_x
            y_size = (max_y - min_y) / num_chunks_y
            
            # Get projection info from the image
            crs = image.projection().getInfo()['crs']
            scale = 500  # Default scale in meters
            
            # Export each chunk
            chunk_files = []
            total_chunks = num_chunks_x * num_chunks_y
            chunks_completed = 0
            
            for i in range(num_chunks_x):
                for j in range(num_chunks_y):
                    chunk_x_min = min_x + (i * x_size)
                    chunk_x_max = min_x + ((i + 1) * x_size)
                    chunk_y_min = min_y + (j * y_size)
                    chunk_y_max = min_y + ((j + 1) * y_size)
                    
                    # Create geometry for this chunk
                    chunk_geometry = ee.Geometry.Rectangle([
                        chunk_x_min, chunk_y_min, 
                        chunk_x_max, chunk_y_max
                    ])
                    
                    # Clip image to chunk geometry
                    chunk_image = image.clip(chunk_geometry)
                    
                    # Create filename for this chunk
                    chunk_filename = os.path.join(chunk_dir, f"{export_name}_chunk_{i}_{j}.tif")
                    chunk_files.append(chunk_filename)
                    
                    if status_callback:
                        status_callback(f"Exporting chunk {chunks_completed+1} of {total_chunks}...")
                    
                    # Export this chunk using geemap
                    try:
                        task = geemap.ee_export_image(
                            chunk_image, 
                            filename=chunk_filename,
                            scale=scale,
                            region=chunk_geometry.getInfo()['coordinates'],
                            crs=crs,
                            file_per_band=False
                        )
                        
                        # Wait for completion
                        while not os.path.exists(chunk_filename):
                            time.sleep(2)  # Wait for file to appear
                            
                        chunks_completed += 1
                        
                    except Exception as e:
                        if status_callback:
                            status_callback(f"Error exporting chunk {i}_{j}: {str(e)}")
                        # Continue with other chunks
            
            # If we have at least one chunk, try to merge them
            if chunk_files and any(os.path.exists(f) for f in chunk_files):
                if status_callback:
                    status_callback(f"Successfully exported {chunks_completed} of {total_chunks} chunks. Merging chunks...")
                
                # Final merged file path
                merged_file = self._get_export_path('GeoTIFF', folder_name, export_name, 'tif')
                
                # Merge the chunks using rasterio
                try:
                    # Use rasterio to merge the tiles
                    # This is a simplified version - in production code, would need more robust merging
                    from rasterio.merge import merge
                    
                    # Open all valid chunk files
                    src_files_to_mosaic = [rasterio.open(f) for f in chunk_files if os.path.exists(f)]
                    
                    if src_files_to_mosaic:
                        # Merge the files
                        mosaic, out_trans = merge(src_files_to_mosaic)
                        
                        # Copy the metadata from the first file
                        out_meta = src_files_to_mosaic[0].meta.copy()
                        
                        # Update the metadata
                        out_meta.update({
                            "driver": "GTiff",
                            "height": mosaic.shape[1],
                            "width": mosaic.shape[2],
                            "transform": out_trans
                        })
                        
                        # Write the mosaic to disk
                        with rasterio.open(merged_file, "w", **out_meta) as dest:
                            dest.write(mosaic)
                        
                        # Close the source files
                        for src in src_files_to_mosaic:
                            src.close()
                        
                        # Clean up chunk files
                        try:
                            shutil.rmtree(chunk_dir)
                        except:
                            pass
                        
                        # Report success
                        file_size_mb = os.path.getsize(merged_file) / (1024 * 1024)
                        return f"GeoTIFF export completed successfully. File saved to: {merged_file} ({file_size_mb:.2f} MB)"
                    else:
                        raise Exception("No valid chunk files were created")
                        
                except Exception as e:
                    # If merging fails, return what we have
                    if status_callback:
                        status_callback(f"Error merging chunks: {str(e)}. Individual chunks available.")
                    
                    return f"Chunked export partially successful. {chunks_completed} of {total_chunks} chunks exported to: {chunk_dir}"
            else:
                # If no chunks were exported successfully, fall back to Google Drive
                if status_callback:
                    status_callback("Chunk export failed. Falling back to Google Drive...")
                
                return self._export_geotiff_to_drive(image, export_name, folder_name, status_callback)
                
        except Exception as e:
            # Final fallback to Google Drive
            if status_callback:
                status_callback(f"Error during chunked export: {str(e)}. Falling back to Google Drive...")
            
            return self._export_geotiff_to_drive(image, export_name, folder_name, status_callback)
    
    def _export_geotiff_to_drive(self, image: ee.Image, export_name: str,
                              folder_name: str, status_callback: Optional[callable] = None) -> str:
        """
        Fall back to Google Drive for GeoTIFF export
        
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
        drive_folder = f"{self.export_root}/{folder_name}"
        export_task = ee.batch.Export.image.toDrive(
            image=image,
            description=export_name,
            folder=drive_folder,
            fileNamePrefix=export_name,
            crs='EPSG:4326',
            scale=500,
            maxPixels=1e9,
            fileFormat='GeoTIFF'
        )
        
        # Start the task
        export_task.start()
        
        # Update status
        if status_callback:
            status_callback(f"GeoTIFF export to Google Drive started. The file will be saved to '{drive_folder}' folder in your Google Drive.")
        
        return f"GeoTIFF export to Google Drive started. The file will be saved to '{drive_folder}' folder in your Google Drive."
    
    def _export_csv_enhanced(self, panel_data: Dict[str, Any], export_name: str,
                        folder_name: str, status_callback: Optional[callable] = None) -> str:
        """Enhanced CSV export with chunking for large data"""
        # Update status
        if status_callback:
            status_callback("Setting up CSV export...")
        
        # Get temporal data
        temporal_data = panel_data.get('temporal_data', [])
        if not temporal_data:
            return "Error: No temporal data available for CSV export"
        
        # Get normalized path with proper structure
        local_file_path = self._get_export_path('CSV', folder_name, export_name, 'csv')
        local_folder = os.path.dirname(local_file_path)
        
        # Log the export path
        print(f"Exporting CSV to: {local_file_path}")
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame(temporal_data)
            
            # Check size
            num_rows = len(df)
            needs_chunking = num_rows > self.max_rows_csv
            
            if needs_chunking:
                if status_callback:
                    status_callback(f"Large dataset detected ({num_rows} rows), chunking CSV export...")
                
                # Calculate number of chunks needed
                chunk_size = self.max_rows_csv
                num_chunks = math.ceil(num_rows / chunk_size)
                
                # Create directory for chunks
                chunk_dir = os.path.join(local_folder, f"{export_name}_chunks")
                os.makedirs(chunk_dir, exist_ok=True)
                
                # Export each chunk
                for i in range(num_chunks):
                    start_idx = i * chunk_size
                    end_idx = min((i + 1) * chunk_size, num_rows)
                    
                    # Get chunk of data
                    chunk_df = df.iloc[start_idx:end_idx]
                    
                    # Create chunk filename
                    chunk_filename = os.path.join(chunk_dir, f"{export_name}_part_{i+1}_of_{num_chunks}.csv")
                    
                    # Save chunk
                    chunk_df.to_csv(chunk_filename, index=False)
                    
                    if status_callback and i % 5 == 0:  # Update status every 5 chunks
                        status_callback(f"Exported chunk {i+1} of {num_chunks}...")
                
                # Also save a single file with basic info
                summary_df = pd.DataFrame({
                    'Chunk': [f"Part {i+1} of {num_chunks}" for i in range(num_chunks)],
                    'Rows': [min(chunk_size, num_rows - i * chunk_size) for i in range(num_chunks)],
                    'Filename': [f"{export_name}_part_{i+1}_of_{num_chunks}.csv" for i in range(num_chunks)]
                })
                
                summary_file = os.path.join(local_folder, f"{export_name}_index.csv")
                summary_df.to_csv(summary_file, index=False)
                
                return f"CSV export completed with chunking. {num_chunks} files created in {chunk_dir}"
            else:
                # Save DataFrame for small files
                df.to_csv(local_file_path, index=False)
                
                # Get file size
                file_size_mb = os.path.getsize(local_file_path) / (1024 * 1024)
                
                # Update status
                if status_callback:
                    status_callback(f"CSV export completed. File saved to: {local_file_path} ({file_size_mb:.2f} MB)")
                
                return f"CSV export completed. File saved to: {local_file_path} ({file_size_mb:.2f} MB)"
        
        except Exception as e:
            error_msg = f"CSV export failed: {str(e)}"
            if status_callback:
                status_callback(error_msg)
            return error_msg
    
    def _export_netcdf_enhanced(self, image: ee.Image, export_name: str,
                            folder_name: str, status_callback: Optional[callable] = None) -> str:
        """Enhanced NetCDF export with local priority and chunking"""
        # Update status
        if status_callback:
            status_callback("Setting up NetCDF export, checking image complexity...")
        
        # Get normalized path with proper structure
        local_file_path = self._get_export_path('NetCDF', folder_name, export_name, 'nc')
        local_folder = os.path.dirname(local_file_path)
        
        # Log the export path
        print(f"Exporting NetCDF to: {local_file_path}")
        
        try:
            # Check image size similarly to GeoTIFF export
            try:
                image_info = image.getInfo()
                bands = image_info.get('bands', [])
                if bands:
                    # Get dimensions from the first band
                    size_estimate = 0
                    for band in bands:
                        dimensions = band.get('dimensions', [0, 0])
                        size_estimate += dimensions[0] * dimensions[1]
                else:
                    # If we can't get dimensions, estimate based on bounds
                    bounds = image.geometry().bounds()
                    area_km2 = bounds.area().divide(1000 * 1000).getInfo()
                    # Approximate size in pixels at 500m resolution
                    size_estimate = area_km2 * 4  # 500m x 500m = 0.25 km2 per pixel
                
                needs_chunking = size_estimate > self.max_pixels_no_chunk
            except:
                # If we can't estimate size, assume it's large
                needs_chunking = True
            
            # Attempt local export
            # For NetCDF, we can export to GeoTIFF first, then convert
            if needs_chunking:
                if status_callback:
                    status_callback("Large image detected, using spatial chunking for NetCDF export...")
                
                # Export as chunked GeoTIFF first
                geotiff_result = self._chunked_geotiff_local_export(
                    image, 
                    f"{export_name}_temp", 
                    os.path.join(self.local_export_dir, 'temp'),
                    status_callback
                )
                
                # Check if GeoTIFF export was successful
                if "export completed successfully" in geotiff_result:
                    # Extract the temporary GeoTIFF path
                    import re
                    geotiff_path_match = re.search(r"File saved to: (.*?\.(tif|TIF))", geotiff_result)
                    
                    if geotiff_path_match:
                        temp_geotiff_path = geotiff_path_match.group(1)
                        
                        # Convert GeoTIFF to NetCDF
                        if status_callback:
                            status_callback("Converting GeoTIFF to NetCDF format...")
                        
                        try:
                            # Use xarray and rasterio to convert
                            # Open the GeoTIFF with rasterio
                            with rasterio.open(temp_geotiff_path) as src:
                                # Get data and metadata
                                data = src.read(1)  # Read the first band
                                transform = src.transform
                                
                                # Create coordinates
                                height, width = data.shape
                                rows = np.arange(height)
                                cols = np.arange(width)
                                
                                # Create lon/lat coordinates
                                lons = np.zeros(width)
                                lats = np.zeros(height)
                                
                                for col in range(width):
                                    x, y = transform * (col + 0.5, 0)  # +0.5 for pixel center
                                    lons[col] = x
                                
                                for row in range(height):
                                    x, y = transform * (0, row + 0.5)  # +0.5 for pixel center
                                    lats[row] = y
                                
                                # Create xarray dataset
                                da = xr.DataArray(
                                    data,
                                    dims=('lat', 'lon'),
                                    coords={'lat': lats, 'lon': lons},
                                    attrs={
                                        'long_name': export_name.replace('_', ' '),
                                        'units': 'unknown',
                                        'missing_value': src.nodata if src.nodata is not None else -9999
                                    }
                                )
                                
                                # Create dataset
                                ds = xr.Dataset({
                                    'data': da
                                }, attrs={
                                    'title': export_name.replace('_', ' '),
                                    'source': 'Climate Analysis Tool',
                                    'creation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                })
                                
                                # Save as NetCDF
                                ds.to_netcdf(local_file_path)
                                
                                # Clean up temp file
                                try:
                                    os.remove(temp_geotiff_path)
                                except:
                                    pass
                                
                                # Get file size
                                file_size_mb = os.path.getsize(local_file_path) / (1024 * 1024)
                                
                                return f"NetCDF export completed successfully. File saved to: {local_file_path} ({file_size_mb:.2f} MB)"
                        
                        except Exception as e:
                            if status_callback:
                                status_callback(f"Error converting to NetCDF: {str(e)}. Falling back to Google Drive export...")
                            
                            # Fall back to Google Drive
                            return self._export_netcdf_to_drive(image, export_name, folder_name, status_callback)
                    else:
                        # Couldn't extract GeoTIFF path, fall back to Google Drive
                        return self._export_netcdf_to_drive(image, export_name, folder_name, status_callback)
                else:
                    # GeoTIFF export failed, fall back to Google Drive
                    return self._export_netcdf_to_drive(image, export_name, folder_name, status_callback)
            else:
                # Try direct local export for smaller images
                # (similar approach but without chunking)
                try:
                    # First export as GeoTIFF
                    temp_geotiff_path = os.path.join(self.local_export_dir, 'temp', f"{export_name}_temp.tif")
                    
                    # Get projection info from the image
                    crs = image.projection().getInfo()['crs']
                    scale = 500  # Default scale in meters
                    
                    # Create bounds for the export
                    region = image.geometry().bounds().getInfo()['coordinates']
                    
                    # Use geemap to download the image as GeoTIFF
                    task = geemap.ee_export_image(
                        image, 
                        filename=temp_geotiff_path,
                        scale=scale,
                        region=region,
                        crs=crs,
                        file_per_band=False
                    )
                    
                    # Wait for the GeoTIFF to be created
                    if status_callback:
                        status_callback("Downloading data for NetCDF, please wait...")
                    
                    # Check if the file was created successfully
                    if os.path.exists(temp_geotiff_path):
                        # Convert to NetCDF using the same code as for chunked exports
                        if status_callback:
                            status_callback("Converting to NetCDF format...")
                        
                        # Use xarray and rasterio to convert (same as above)
                        with rasterio.open(temp_geotiff_path) as src:
                            # Get data and metadata
                            data = src.read(1)  # Read the first band
                            transform = src.transform
                            
                            # Create coordinates
                            height, width = data.shape
                            rows = np.arange(height)
                            cols = np.arange(width)
                            
                            # Create lon/lat coordinates
                            lons = np.zeros(width)
                            lats = np.zeros(height)
                            
                            for col in range(width):
                                x, y = transform * (col + 0.5, 0)  # +0.5 for pixel center
                                lons[col] = x
                            
                            for row in range(height):
                                x, y = transform * (0, row + 0.5)  # +0.5 for pixel center
                                lats[row] = y
                            
                            # Create xarray dataset
                            da = xr.DataArray(
                                data,
                                dims=('lat', 'lon'),
                                coords={'lat': lats, 'lon': lons},
                                attrs={
                                    'long_name': export_name.replace('_', ' '),
                                    'units': 'unknown',
                                    'missing_value': src.nodata if src.nodata is not None else -9999
                                }
                            )
                            
                            # Create dataset
                            ds = xr.Dataset({
                                'data': da
                            }, attrs={
                                'title': export_name.replace('_', ' '),
                                'source': 'Climate Analysis Tool',
                                'creation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            })
                            
                            # Save as NetCDF
                            ds.to_netcdf(local_file_path)
                            
                            # Clean up temp file
                            try:
                                os.remove(temp_geotiff_path)
                            except:
                                pass
                            
                            # Get file size
                            file_size_mb = os.path.getsize(local_file_path) / (1024 * 1024)
                            
                            return f"NetCDF export completed successfully. File saved to: {local_file_path} ({file_size_mb:.2f} MB)"
                    else:
                        raise Exception("Export failed, temporary file not created")
                        
                except Exception as e:
                    if status_callback:
                        status_callback(f"Local NetCDF export failed: {str(e)}. Trying Google Drive export...")
                    
                    # Fall back to Google Drive
                    return self._export_netcdf_to_drive(image, export_name, folder_name, status_callback)
        
        except Exception as e:
            # Final fallback to Google Drive
            if status_callback:
                status_callback(f"Error during NetCDF export process: {str(e)}. Falling back to Google Drive...")
            
            return self._export_netcdf_to_drive(image, export_name, folder_name, status_callback)
    
    def _export_netcdf_to_drive(self, image: ee.Image, export_name: str,
                             folder_name: str, status_callback: Optional[callable] = None) -> str:
        """
        Fall back to Google Drive for NetCDF export
        
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
        drive_folder = f"{self.export_root}/{folder_name}"
        export_task = ee.batch.Export.image.toDrive(
            image=image,
            description=export_name,
            folder=drive_folder,
            fileNamePrefix=export_name,
            crs='EPSG:4326',
            scale=500,
            maxPixels=1e9,
            fileFormat='NetCDF'
        )
        
        # Start the task
        export_task.start()
        
        # Update status
        if status_callback:
            status_callback(f"NetCDF export to Google Drive started. The file will be saved to '{drive_folder}' folder in your Google Drive.")
        
        return f"NetCDF export to Google Drive started. The file will be saved to '{drive_folder}' folder in your Google Drive."
    
    def _export_all_geotiff_enhanced(self, panel_data: Dict[str, Any], export_name_base: str,
                                folder_name: str, status_callback: Optional[callable] = None) -> str:
        """
        Enhanced export of all years as GeoTIFF with parallel processing
        
        Args:
            panel_data: Data for the panel
            export_name_base: Base name for export files
            folder_name: Folder name for organization
            status_callback: Optional callback for status updates
            
        Returns:
            Status message
        """
        # Update status
        if status_callback:
            status_callback("Starting enhanced export of all years as GeoTIFF...")
        
        # Get state
        state = panel_data.get('state', {})
        if not state:
            return "Error: No analysis state available for export"
        
        # Get time range
        time_range = state.get('time_range', (2020, 2020))
        start_year, end_year = time_range
        
        # Create the base directory path using our helper
        # We'll just get the directory part and not create a specific file
        temp_path = self._get_export_path('GeoTIFF', folder_name, export_name_base, 'tif')
        local_folder = os.path.dirname(temp_path)
        
        # Create a specific subfolder for this time series
        time_series_folder = os.path.join(local_folder, export_name_base)
        os.makedirs(time_series_folder, exist_ok=True)
        
        # Log the export directory
        print(f"Exporting GeoTIFF time series to: {time_series_folder}")
        
        # Track results
        successful_exports = 0
        failed_exports = 0
        total_years = end_year - start_year + 1
        
        # Try using multiprocessing for parallel exports
        try:
            # Import multiprocessing
            import multiprocessing as mp
            from functools import partial
            
            # Determine number of processes (use fewer processes than CPUs to avoid overwhelming the system)
            num_processes = max(1, min(mp.cpu_count() - 1, 4))  # Use at most 4 processes
            
            if status_callback:
                status_callback(f"Using {num_processes} parallel processes for export...")
            
            # Define function to export one year
            def export_one_year(year, data_source, state_copy, folder):
                try:
                    # Get data for year
                    year_data = self._get_data_for_year(data_source, year)
                    
                    if year_data:
                        # Create export name
                        year_export_name = f"{export_name_base}_{year}"
                        
                        # Create proper file path for this year using helper function
                        # We'll place it in the time series subfolder
                        year_filename = f"{year_export_name}"
                        local_file_path = os.path.join(folder, f"{year_filename}.tif")
                        
                        # Get projection info from the image
                        crs = year_data.projection().getInfo()['crs']
                        scale = 500  # Default scale in meters
                        
                        # Create bounds for the export
                        region = year_data.geometry().bounds().getInfo()['coordinates']
                        
                        # Use geemap to download the image
                        task = geemap.ee_export_image(
                            year_data, 
                            filename=local_file_path,
                            scale=scale,
                            region=region,
                            crs=crs,
                            file_per_band=False
                        )
                        
                        # Check if the file was created
                        if os.path.exists(local_file_path):
                            return (True, year)
                        else:
                            return (False, year)
                    else:
                        return (False, year)
                except Exception as e:
                    print(f"Error exporting year {year}: {str(e)}")
                    return (False, year)
            
            # Create a partial function with fixed arguments
            export_func = partial(
                export_one_year, 
                data_source=panel_data, 
                state_copy=state.copy(),
                folder=time_series_folder
            )
            
            # Create a pool of processes
            with mp.Pool(processes=num_processes) as pool:
                # Export all years in parallel
                years_to_export = list(range(start_year, end_year + 1))
                
                # Process years in batches to avoid overwhelming Earth Engine
                batch_size = 5
                for i in range(0, len(years_to_export), batch_size):
                    batch = years_to_export[i:i+batch_size]
                    
                    if status_callback:
                        status_callback(f"Processing years {batch[0]}-{batch[-1]} ({i+1}-{min(i+batch_size, len(years_to_export))} of {len(years_to_export)})...")
                    
                    # Process this batch in parallel
                    results = pool.map(export_func, batch)
                    
                    # Count successes and failures
                    for success, year in results:
                        if success:
                            successful_exports += 1
                        else:
                            failed_exports += 1
                    
                    # Update status
                    if status_callback:
                        status_callback(f"Completed {i+len(batch)} of {len(years_to_export)} years. {successful_exports} successful, {failed_exports} failed.")
            
        except Exception as e:
            # Fall back to sequential processing if parallel fails
            if status_callback:
                status_callback(f"Parallel processing failed: {str(e)}. Falling back to sequential processing...")
            
            # Process each year sequentially
            for year in range(start_year, end_year + 1):
                try:
                    # Get data for year
                    year_data = self._get_data_for_year(panel_data, year)
                    
                    if year_data:
                        # Create export name
                        year_export_name = f"{export_name_base}_{year}"
                        
                        # Update status
                        if status_callback:
                            status_callback(f"Exporting year {year} ({year - start_year + 1} of {total_years})...")
                        
                        # Create proper file path for this year
                        local_file_path = os.path.join(time_series_folder, f"{year_export_name}.tif")
                        
                        try:
                            # Get projection info from the image
                            crs = year_data.projection().getInfo()['crs']
                            scale = 500  # Default scale in meters
                            
                            # Create bounds for the export
                            region = year_data.geometry().bounds().getInfo()['coordinates']
                            
                            # Use geemap to download the image
                            task = geemap.ee_export_image(
                                year_data, 
                                filename=local_file_path,
                                scale=scale,
                                region=region,
                                crs=crs,
                                file_per_band=False
                            )
                            
                            # Check if the file was created
                            if os.path.exists(local_file_path):
                                successful_exports += 1
                            else:
                                failed_exports += 1
                                
                        except Exception as e:
                            failed_exports += 1
                            if status_callback:
                                status_callback(f"Error exporting year {year}: {str(e)}")
                    else:
                        failed_exports += 1
                
                except Exception as e:
                    failed_exports += 1
                    if status_callback:
                        status_callback(f"Error processing year {year}: {str(e)}")
        
        # Final status update
        if successful_exports > 0:
            status_message = f"GeoTIFF export completed. {successful_exports} of {total_years} years exported successfully to {time_series_folder}"
            
            if failed_exports > 0:
                status_message += f". {failed_exports} years failed to export."
        else:
            status_message = f"GeoTIFF export failed. No years were exported successfully."
            
            # Offer Google Drive export as fallback
            if status_callback:
                status_callback(f"{status_message} Would you like to try Google Drive export instead?")
            
            # For now, let's go ahead with Google Drive export automatically
            return self._export_all_geotiff_to_drive(panel_data, export_name_base, folder_name, status_callback)
        
        if status_callback:
            status_callback(status_message)
        
        return status_message
    
    def _export_all_geotiff_to_drive(self, panel_data: Dict[str, Any], export_name_base: str,
                                folder_name: str, status_callback: Optional[callable] = None) -> str:
        """
        Fall back to Google Drive for all-year GeoTIFF export
        
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
            status_callback("Starting export of all years as GeoTIFF to Google Drive...")
        
        # Get state
        state = panel_data.get('state', {})
        if not state:
            return "Error: No analysis state available for export"
        
        # Get time range
        time_range = state.get('time_range', (2020, 2020))
        start_year, end_year = time_range
        
        # Fix folder name for consistency
        parts = folder_name.split('/')
        
        # Fix dataset name (first part)
        if len(parts) > 0:
            if parts[0].lower() == "unknown":
                parts[0] = "general"
            # Make sure it's one of our standard directories or create custom
            if parts[0] not in ["ERA5", "PRISM", "DAYMET", "general", "Custom"]:
                # If it's a recognized name with different case, fix it
                upper_part = parts[0].upper()
                if upper_part in ["ERA5", "PRISM", "DAYMET"]:
                    parts[0] = upper_part
                else:
                    # Create inside Custom folder
                    parts = ["Custom", parts[0]]
        
        # Ensure we have at least two parts
        if len(parts) == 0:
            parts = ["general", "data"]
        elif len(parts) == 1:
            parts.append("climate_data")
        
        # Reconstruct folder name
        folder_name = '/'.join(parts)
        
        # Create special folder for this export
        drive_folder = f"{self.export_root}/{folder_name}/{export_name_base}"
        
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
                        folder=drive_folder,
                        fileNamePrefix=export_name,
                        crs='EPSG:4326',
                        scale=500,
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
        status_message = f"Started {task_count} GeoTIFF export tasks to Google Drive. Files will be saved to '{drive_folder}' folder."
        
        if status_callback:
            status_callback(status_message)
        
        return status_message
    
    def _export_all_csv_enhanced(self, panel_data: Dict[str, Any], export_name_base: str,
                            folder_name: str, status_callback: Optional[callable] = None) -> str:
        """
        Enhanced export of all temporal data as CSV
        
        Args:
            panel_data: Data for the panel
            export_name_base: Base name for export file
            folder_name: Folder name for organization
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
        
        # Create proper file path using our helper
        local_file_path = self._get_export_path('CSV', folder_name, f"{export_name_base}_temporal", 'csv')
        local_folder = os.path.dirname(local_file_path)
        
        # Log the export path
        print(f"Exporting CSV to: {local_file_path}")
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame(temporal_data)
            
            # Add metadata
            state = panel_data.get('state', {})
            dataset = panel_data.get('dataset', state.get('dataset', 'general'))
            parameter = panel_data.get('parameter', state.get('parameter', 'climate'))
            index = panel_data.get('index', state.get('index', 'data'))
            
            # Add metadata as columns
            df['dataset'] = dataset
            df['parameter'] = parameter
            df['index'] = index
            
            # Reorder columns to put metadata first
            cols = df.columns.tolist()
            meta_cols = ['dataset', 'parameter', 'index']
            data_cols = [col for col in cols if col not in meta_cols]
            df = df[meta_cols + data_cols]
            
            # Check size
            num_rows = len(df)
            needs_chunking = num_rows > self.max_rows_csv
            
            if needs_chunking:
                if status_callback:
                    status_callback(f"Large dataset detected ({num_rows} rows), chunking CSV export...")
                
                # Calculate number of chunks needed
                chunk_size = self.max_rows_csv
                num_chunks = math.ceil(num_rows / chunk_size)
                
                # Create directory for chunks using our helper for consistent naming
                chunk_dir_path = self._get_export_path('CSV', folder_name, f"{export_name_base}_chunks", '')
                chunk_dir = os.path.dirname(chunk_dir_path)
                os.makedirs(chunk_dir, exist_ok=True)
                
                # Export each chunk
                for i in range(num_chunks):
                    start_idx = i * chunk_size
                    end_idx = min((i + 1) * chunk_size, num_rows)
                    
                    # Get chunk of data
                    chunk_df = df.iloc[start_idx:end_idx]
                    
                    # Create chunk filename
                    chunk_filename = os.path.join(chunk_dir, f"{export_name_base}_part_{i+1}_of_{num_chunks}.csv")
                    
                    # Save chunk
                    chunk_df.to_csv(chunk_filename, index=False)
                
                # Also save a single file with basic info
                summary_df = pd.DataFrame({
                    'Chunk': [f"Part {i+1} of {num_chunks}" for i in range(num_chunks)],
                    'Rows': [min(chunk_size, num_rows - i * chunk_size) for i in range(num_chunks)],
                    'Filename': [f"{export_name_base}_part_{i+1}_of_{num_chunks}.csv" for i in range(num_chunks)]
                })
                
                summary_file = os.path.join(local_folder, f"{export_name_base}_index.csv")
                summary_df.to_csv(summary_file, index=False)
                
                return f"CSV export completed with chunking. {num_chunks} files created in {chunk_dir}"
            else:
                # Save DataFrame for small files
                df.to_csv(local_file_path, index=False)
                
                # Get file size
                file_size_mb = os.path.getsize(local_file_path) / (1024 * 1024)
                
                # Update status
                if status_callback:
                    status_callback(f"CSV export completed. File saved to: {local_file_path} ({file_size_mb:.2f} MB)")
                
                return f"CSV export completed. File saved to: {local_file_path} ({file_size_mb:.2f} MB)"
        
        except Exception as e:
            error_msg = f"CSV export failed: {str(e)}"
            if status_callback:
                status_callback(error_msg)
            return error_msg
    
    def _export_all_netcdf_enhanced(self, panel_data: Dict[str, Any], export_name_base: str,
                                folder_name: str, status_callback: Optional[callable] = None) -> str:
        """
        Enhanced export of all years as NetCDF with chunking and merging
        
        Args:
            panel_data: Data for the panel
            export_name_base: Base name for export files
            folder_name: Folder name for organization
            status_callback: Optional callback for status updates
            
        Returns:
            Status message
        """
        # Update status
        if status_callback:
            status_callback("Starting enhanced export of all years as NetCDF...")
        
        # Get state
        state = panel_data.get('state', {})
        if not state:
            return "Error: No analysis state available for export"
        
        # Get time range
        time_range = state.get('time_range', (2020, 2020))
        start_year, end_year = time_range
        
        # Create the base directory path using our helper
        temp_path = self._get_export_path('NetCDF', folder_name, export_name_base, 'nc')
        local_folder = os.path.dirname(temp_path)
        
        # Create a specific subfolder for individual year files
        years_folder = os.path.join(local_folder, f"{export_name_base}_years")
        os.makedirs(years_folder, exist_ok=True)
        
        # Log the export paths
        print(f"Exporting NetCDF time series. Individual files to: {years_folder}")
        print(f"Combined file will be saved to: {temp_path}")
        
        # First, try to create individual NetCDF files for each year
        individual_files = []
        successful_exports = 0
        failed_exports = 0
        total_years = end_year - start_year + 1
        
        for year in range(start_year, end_year + 1):
            try:
                # Get data for year
                year_data = self._get_data_for_year(panel_data, year)
                
                if year_data:
                    # Create export name
                    year_export_name = f"{export_name_base}_{year}"
                    
                    # Update status
                    if status_callback:
                        status_callback(f"Exporting year {year} ({year - start_year + 1} of {total_years})...")
                    
                    # Create proper file path for this year
                    year_file_path = os.path.join(years_folder, f"{year_export_name}.nc")
                    
                    # Export this year to NetCDF
                    try:
                        # First export as GeoTIFF
                        temp_geotiff_path = os.path.join(self.local_export_dir, 'temp', f"{year_export_name}_temp.tif")
                        
                        # Get projection info from the image
                        crs = year_data.projection().getInfo()['crs']
                        scale = 500  # Default scale in meters
                        
                        # Create bounds for the export
                        region = year_data.geometry().bounds().getInfo()['coordinates']
                        
                        # Use geemap to download the image as GeoTIFF
                        task = geemap.ee_export_image(
                            year_data, 
                            filename=temp_geotiff_path,
                            scale=scale,
                            region=region,
                            crs=crs,
                            file_per_band=False
                        )
                        
                        # Wait for the GeoTIFF to be created
                        if status_callback:
                            status_callback(f"Downloading data for year {year}, please wait...")
                        
                        # Check if the file was created successfully
                        if os.path.exists(temp_geotiff_path):
                            # Convert to NetCDF
                            if status_callback:
                                status_callback(f"Converting year {year} to NetCDF format...")
                            
                            # Use xarray and rasterio to convert
                            with rasterio.open(temp_geotiff_path) as src:
                                # Get data and metadata
                                data = src.read(1)  # Read the first band
                                transform = src.transform
                                
                                # Create coordinates
                                height, width = data.shape
                                rows = np.arange(height)
                                cols = np.arange(width)
                                
                                # Create lon/lat coordinates
                                lons = np.zeros(width)
                                lats = np.zeros(height)
                                
                                for col in range(width):
                                    x, y = transform * (col + 0.5, 0)  # +0.5 for pixel center
                                    lons[col] = x
                                
                                for row in range(height):
                                    x, y = transform * (0, row + 0.5)  # +0.5 for pixel center
                                    lats[row] = y
                                
                                # Create xarray dataset
                                da = xr.DataArray(
                                    data,
                                    dims=('lat', 'lon'),
                                    coords={'lat': lats, 'lon': lons},
                                    attrs={
                                        'long_name': f"{panel_data.get('index', 'climate_index')} {year}",
                                        'units': panel_data.get('results', {}).get('units', 'unknown'),
                                        'missing_value': src.nodata if src.nodata is not None else -9999,
                                        'year': year
                                    }
                                )
                                
                                # Create dataset with year in the name
                                ds = xr.Dataset({
                                    'data': da
                                }, attrs={
                                    'title': f"{panel_data.get('index', 'climate_index')} {year}",
                                    'source': 'Climate Analysis Tool',
                                    'creation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    'year': year,
                                    'dataset': panel_data.get('dataset', 'general'),
                                    'parameter': panel_data.get('parameter', 'climate'),
                                    'index': panel_data.get('index', 'data')
                                })
                                
                                # Save as NetCDF with compression
                                encoding = {'data': {'zlib': True, 'complevel': 5}}
                                ds.to_netcdf(year_file_path, encoding=encoding)
                                
                                # Clean up temp file
                                try:
                                    os.remove(temp_geotiff_path)
                                except:
                                    pass
                                
                                # Add to list of successful exports
                                individual_files.append((year, year_file_path))
                                successful_exports += 1
                        else:
                            failed_exports += 1
                            if status_callback:
                                status_callback(f"Failed to export year {year}: temporary file not created")
                    
                    except Exception as e:
                        failed_exports += 1
                        if status_callback:
                            status_callback(f"Error exporting year {year}: {str(e)}")
                else:
                    failed_exports += 1
            
            except Exception as e:
                failed_exports += 1
                if status_callback:
                    status_callback(f"Error processing year {year}: {str(e)}")
        
        # Now try to merge all individual files into a single NetCDF with time dimension
        if successful_exports > 0:
            try:
                if status_callback:
                    status_callback("Creating multi-year NetCDF file...")
                
                # Sort files by year
                individual_files.sort(key=lambda x: x[0])
                
                # Create merged file path using our helper
                merged_file = self._get_export_path('NetCDF', folder_name, f"{export_name_base}_all_years", 'nc')
                
                # Use xarray to open and merge files
                datasets = []
                for year, file_path in individual_files:
                    try:
                        ds = xr.open_dataset(file_path)
                        # Add year as a coordinate if not already present
                        if 'year' not in ds.coords:
                            ds = ds.assign_coords(year=year)
                        # Add year as a dimension to all data variables
                        if 'year' not in ds.dims:
                            ds = ds.expand_dims('year')
                        datasets.append(ds)
                    except Exception as e:
                        if status_callback:
                            status_callback(f"Warning: Could not include year {year}: {str(e)}")
                
                if datasets:
                    # Merge along the year dimension
                    combined = xr.concat(datasets, dim='year')
                    
                    # Add metadata
                    combined.attrs.update({
                        'title': f"{panel_data.get('index', 'climate_index')} {start_year}-{end_year}",
                        'source': 'Climate Analysis Tool',
                        'creation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'years_included': f"{start_year}-{end_year}",
                        'dataset': panel_data.get('dataset', 'general'),
                        'parameter': panel_data.get('parameter', 'climate'),
                        'index': panel_data.get('index', 'data')
                    })
                    
                    # Save as NetCDF with compression
                    encoding = {var: {'zlib': True, 'complevel': 5} for var in combined.data_vars}
                    combined.to_netcdf(merged_file, encoding=encoding)
                    
                    # Close datasets
                    for ds in datasets:
                        ds.close()
                    
                    # Get file size
                    file_size_mb = os.path.getsize(merged_file) / (1024 * 1024)
                    
                    status_message = (
                        f"NetCDF export completed. {successful_exports} of {total_years} years exported. "
                        f"Multi-year file saved to: {merged_file} ({file_size_mb:.2f} MB). "
                        f"Individual year files available in {years_folder}."
                    )
                    
                    if failed_exports > 0:
                        status_message += f" {failed_exports} years failed to export."
                else:
                    status_message = (
                        f"NetCDF export partially completed. {successful_exports} individual year files created "
                        f"but could not be merged. Files available in {years_folder}."
                    )
            
            except Exception as e:
                status_message = (
                    f"NetCDF export partially completed. {successful_exports} individual year files created "
                    f"but could not be merged due to error: {str(e)}. Files available in {years_folder}."
                )
        
        else:
            status_message = f"NetCDF export failed. No years were exported successfully."
            
            # Fall back to Google Drive
            if status_callback:
                status_callback(f"{status_message} Falling back to Google Drive export...")
            
            return self._export_all_netcdf_to_drive(panel_data, export_name_base, folder_name, status_callback)
        
        if status_callback:
            status_callback(status_message)
        
        return status_message
    
    def _export_all_netcdf_to_drive(self, panel_data: Dict[str, Any], export_name_base: str,
                                  folder_name: str, status_callback: Optional[callable] = None) -> str:
        """
        Fall back to Google Drive for all-year NetCDF export
        
        Args:
            panel_data: Data for the panel
            export_name_base: Base name for export files
            folder_name: Folder name in Google Drive
            status_callback: Optional callback for status updates
            
        Returns:
            Status message
        """
        # This has almost the same implementation as _export_all_geotiff_to_drive, but for NetCDF
        # Update status
        if status_callback:
            status_callback("Starting export of all years as NetCDF to Google Drive...")
        
        # Get state
        state = panel_data.get('state', {})
        if not state:
            return "Error: No analysis state available for export"
        
        # Get time range
        time_range = state.get('time_range', (2020, 2020))
        start_year, end_year = time_range
        
        # Create special folder for this export
        drive_folder = f"{self.export_root}/{folder_name}/{export_name_base}"
        
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
                        folder=drive_folder,
                        fileNamePrefix=export_name,
                        crs='EPSG:4326',
                        scale=500,
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
        status_message = f"Started {task_count} NetCDF export tasks to Google Drive. Files will be saved to '{drive_folder}' folder."
        
        if status_callback:
            status_callback(status_message)
        
        return status_message
    
    def _get_data_for_year(self, panel_data: Dict[str, Any], year: int) -> Optional[ee.Image]:
        """
        Get data for a specific year with improved implementation
        
        Args:
            panel_data: Data for the panel
            year: Year to retrieve data for
            
        Returns:
            Earth Engine image for the year or None if not available
        """
        try:
            # Get state
            state = panel_data.get('state', {})
            if not state:
                return None
            
            # Extract necessary parameters
            geometry = state.get('geometry')
            dataset = state.get('dataset')
            parameter = state.get('parameter')
            index = state.get('index')
            
            if not all([geometry, dataset, parameter, index]):
                return None
            
            # Get analysis engine from panel data if available
            analysis_engine = panel_data.get('analysis_engine')
            
            if analysis_engine:
                # Define date range for year
                start_date = f"{year}-01-01"
                end_date = f"{year}-12-31"
                
                # Use analysis engine to calculate index for the year
                image = analysis_engine._calculate_index(
                    geometry=geometry,
                    start_date=start_date,
                    end_date=end_date,
                    dataset=dataset,
                    index=index
                )
                
                return image.clip(geometry)
            
            # If we can't get the analysis engine, check if there's cached data
            # This is a fallback mechanism
            cached_data = panel_data.get('data')
            if cached_data and isinstance(cached_data, ee.Image):
                # Just return the cached data as a best-effort approach
                # Not ideal but better than nothing
                return cached_data
            
            return None
            
        except Exception as e:
            print(f"Error getting data for year {year}: {str(e)}")
            return None
    
    def create_status_widget(self) -> Tuple[widgets.HTML, callable]:
        """
        Create an enhanced widget for displaying export status
        
        Returns:
            Tuple of (status widget, status update function)
        """
        # Create status widget with better styling
        status_widget = HTML(
            value="<div style='padding: 10px; background: #f5f5f5; border-radius: 5px;'>"
                 "<p style='margin: 0;'><b>Export Status:</b> Ready</p>"
                 "</div>"
        )
        
        # Create status update function
        def update_status(message: str):
            # Determine if this is an error, warning, or success message
            message_type = "info"
            if any(error_word in message.lower() for error_word in ["error", "failed", "cannot", "could not"]):
                message_type = "error"
            elif any(warning_word in message.lower() for warning_word in ["warning", "caution", "partial"]):
                message_type = "warning"
            elif any(success_word in message.lower() for success_word in ["success", "complete", "saved"]):
                message_type = "success"
            
            # Style based on message type
            if message_type == "error":
                color = "#f8d7da"
                text_color = "#721c24"
            elif message_type == "warning":
                color = "#fff3cd"
                text_color = "#856404"
            elif message_type == "success":
                color = "#d4edda"
                text_color = "#155724"
            else:  # info
                color = "#f5f5f5"
                text_color = "#000000"
            
            status_widget.value = (
                f"<div style='padding: 10px; background: {color}; "
                f"border-radius: 5px; color: {text_color};'>"
                f"<p style='margin: 0;'><b>Export Status:</b> {message}</p>"
                "</div>"
            )
        
        return status_widget, update_status
    
    def _get_export_path(self, format_type: str, folder_name: str, export_name: str, extension: str) -> str:
        """
        Create a properly formatted export path with consistent separators and metadata
        
        Args:
            format_type: Export format type ('GeoTIFF', 'CSV', 'NetCDF')
            folder_name: Folder structure (e.g. 'ERA5/Temperature')
            export_name: File name for the export
            extension: File extension without the dot (e.g. 'tif', 'csv', 'nc')
            
        Returns:
            Properly formatted file path
        """
        # Replace unknown values with better defaults
        parts = folder_name.split('/')
        
        # Fix dataset name (first part)
        if len(parts) > 0:
            if parts[0].lower() == "unknown":
                parts[0] = "general"
            # Make sure it's one of our standard directories or create custom
            if parts[0] not in ["ERA5", "PRISM", "DAYMET", "general", "Custom"]:
                # If it's a recognized name with different case, fix it
                upper_part = parts[0].upper()
                if upper_part in ["ERA5", "PRISM", "DAYMET"]:
                    parts[0] = upper_part
                else:
                    # Create inside Custom folder
                    parts = ["Custom", parts[0]]
        
        # Fix index name (second part)
        if len(parts) > 1:
            if parts[1].lower() == "unknown":
                if format_type == 'GeoTIFF':
                    parts[1] = "raster_data"
                elif format_type == 'CSV':
                    parts[1] = "tabular_data"
                else:
                    parts[1] = "climate_data"
        
        # Ensure we have at least two parts
        if len(parts) == 0:
            parts = ["general", "data"]
        elif len(parts) == 1:
            if format_type == 'GeoTIFF':
                parts.append("raster_data")
            elif format_type == 'CSV':
                parts.append("tabular_data")
            else:
                parts.append("climate_data")
        
        # Reconstruct folder name
        folder_name = '/'.join(parts)
        
        # Create local folder path with proper directory separators
        # Handle path parts more carefully
        path_parts = [self.local_export_dir, format_type]
        for part in parts:
            if part:  # Only add non-empty parts
                path_parts.append(part)
        
        local_folder = os.path.normpath(os.path.join(*path_parts))
        
        # Ensure directory exists
        os.makedirs(local_folder, exist_ok=True)
        
        # Create full file path
        file_path = os.path.normpath(os.path.join(local_folder, f"{export_name}.{extension}"))
        
        return file_path