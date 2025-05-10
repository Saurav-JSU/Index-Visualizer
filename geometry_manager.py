"""
geometry_manager.py
Handles geographic bounds and geometry operations
"""

import ee
import geemap
import geopandas as gpd
import os
from ipywidgets import widgets, VBox, HBox, Layout
from ipyleaflet import DrawControl
from shapely.geometry import box, mapping
from typing import Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass

@dataclass
class BoundsConfig:
    """Configuration for geographic bounds"""
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float
    
    def to_list(self) -> list:
        """Convert bounds to list format"""
        return [self.min_lon, self.min_lat, self.max_lon, self.max_lat]
    
    @property
    def center(self) -> Tuple[float, float]:
        """Calculate center point of bounds"""
        return ((self.min_lat + self.max_lat) / 2, 
                (self.min_lon + self.max_lon) / 2)

class GeometryManager:
    """
    Handles geographic bounds and geometry operations
    """
    
    def __init__(self):
        """Initialize GeometryManager"""
        self.geometries = {}
        self.maps = {}
        self.draw_controls = {}
        self.current_method = {}

    def create_map_widget(self, panel_id: str) -> widgets.VBox:
        """
        Create a map widget for drawing regions
        
        Args:
            panel_id: Identifier for the panel ("left" or "right")
            
        Returns:
            Widget containing the map
        """
        # Clean up existing map
        self._cleanup_map(panel_id)
        
        # Create new map
        self.maps[panel_id] = geemap.Map(
            center=[0, 0],
            zoom=2,
            layout=Layout(width='100%', height='400px')
        )
        
        # Add draw control
        self.draw_controls[panel_id] = DrawControl(
            rectangle={"shapeOptions": {"color": "#3388ff"}},
            polygon={"shapeOptions": {"color": "#3388ff"}},
            circle={},
            circlemarker={},
            polyline={},
            marker={}
        )
        
        # Handle drawing events
        def handle_draw(target, action, geo_json):
            """Handle drawing events on the map"""
            if action == 'created':
                # Get geometry type
                geo_type = geo_json['geometry']['type']
                
                if geo_type == 'Polygon':
                    # Get coordinates
                    coords = geo_json['geometry']['coordinates'][0]
                    
                    # Extract bounds
                    lons = [coord[0] for coord in coords]
                    lats = [coord[1] for coord in coords]
                    
                    # Set bounds
                    self.set_bounds(
                        panel_id,
                        min(lons),
                        min(lats),
                        max(lons),
                        max(lats)
                    )
                    
                    # Show bounds info
                    info_output.value = f"""
                    <p>Area selected:</p>
                    <ul>
                        <li>Min Lon: {min(lons):.4f}</li>
                        <li>Min Lat: {min(lats):.4f}</li>
                        <li>Max Lon: {max(lons):.4f}</li>
                        <li>Max Lat: {max(lats):.4f}</li>
                    </ul>
                    """
        
        self.draw_controls[panel_id].on_draw(handle_draw)
        self.maps[panel_id].add_control(self.draw_controls[panel_id])
        
        # Create info output
        info_output = widgets.HTML(
            value="<p>Draw a rectangle or polygon on the map to define your area of interest.</p>"
        )
        
        # Create clear button
        clear_button = widgets.Button(
            description="Clear Drawing",
            button_style="warning",
            layout=Layout(width='150px')
        )
        
        # Fixed clear button handler
        def on_clear(b):
            """Clear all drawings on the map"""
            try:
                # Clear draw control features
                if panel_id in self.draw_controls:
                    # Access the native ipyleaflet object and clear all layers
                    draw_control = self.draw_controls[panel_id]
                    if hasattr(draw_control, 'clear'):
                        draw_control.clear()
                    
                    # Clear all map layers except base layer
                    if panel_id in self.maps:
                        map_obj = self.maps[panel_id]
                        layers_to_remove = [layer for layer in map_obj.layers[1:]]
                        for layer in layers_to_remove:
                            map_obj.remove_layer(layer)
                
                # Clear stored geometry
                if panel_id in self.geometries:
                    del self.geometries[panel_id]
                    
                # Also clear bounds
                bounds_key = f"{panel_id}_bounds"
                if bounds_key in self.geometries:
                    del self.geometries[bounds_key]
                
                info_output.value = "<p>Drawing cleared. Draw a new area on the map.</p>"
                
                # Print debug info
                print(f"Map cleared for panel {panel_id}")
                
            except Exception as e:
                info_output.value = f"<p style='color: red'>Error clearing map: {str(e)}</p>"
                print(f"Error clearing map: {str(e)}")
        
        clear_button.on_click(on_clear)
        
        # Set current method
        self.current_method[panel_id] = "draw"
        
        # Return widget
        return widgets.VBox([
            info_output,
            self.maps[panel_id],
            clear_button
        ])
    
    def create_shapefile_widgets(self, panel_id: str) -> widgets.VBox:
        """
        Create widgets for shapefile upload
        
        Args:
            panel_id: Identifier for the panel ("left" or "right")
            
        Returns:
            Widget for shapefile input
        """
        # Clean up existing map
        self._cleanup_map(panel_id)
        
        # Create shapefile input
        shapefile_input = widgets.Text(
            placeholder="Enter path to shapefile",
            description="Path:",
            style={'description_width': 'initial'},
            layout=Layout(width='80%')
        )
        
        # Create upload button
        upload_button = widgets.Button(
            description="Process Shapefile",
            button_style="primary",
            layout=Layout(width='150px')
        )
        
        # Create info output
        info_output = widgets.HTML(
            value="<p>Enter the path to your shapefile (.shp) file.</p>"
        )
        
        # Handle upload button click
        def on_upload(b):
            """Process shapefile upload"""
            path = shapefile_input.value.strip()
            
            if not path:
                info_output.value = "<p style='color: red'>Please enter a path to a shapefile.</p>"
                return
            
            if not os.path.exists(path):
                info_output.value = f"<p style='color: red'>File not found: {path}</p>"
                return
            
            try:
                # Process shapefile
                self.process_shapefile(panel_id, path)
                
                # Show success message
                info_output.value = "<p style='color: green'>✓ Shapefile processed successfully!</p>"
                
                # Create map to display shapefile
                if panel_id not in self.maps:
                    self.maps[panel_id] = geemap.Map(
                        center=[0, 0],
                        zoom=2,
                        layout=Layout(width='100%', height='400px')
                    )
                
                # Display shape on map
                bounds = self.geometries[panel_id + "_bounds"]
                self.maps[panel_id].center = bounds.center
                self.maps[panel_id].zoom = 4
                
                # Add map to container
                container.children = [
                    widgets.VBox([
                        shapefile_input,
                        upload_button,
                        info_output
                    ]),
                    self.maps[panel_id]
                ]
                
            except Exception as e:
                info_output.value = f"<p style='color: red'>Error processing shapefile: {str(e)}</p>"
        
        upload_button.on_click(on_upload)
        
        # Set current method
        self.current_method[panel_id] = "shapefile"
        
        # Create container
        container = widgets.VBox([
            widgets.VBox([
                shapefile_input,
                upload_button,
                info_output
            ])
        ])
        
        return container
    
    def create_bounds_widgets(self, panel_id: str) -> widgets.VBox:
        """
        Create widgets for manual bounds input
        
        Args:
            panel_id: Identifier for the panel ("left" or "right")
            
        Returns:
            Widget for manual bounds input
        """
        # Clean up existing map
        self._cleanup_map(panel_id)
        
        # Create bounds inputs
        min_lon = widgets.FloatText(
            value=-180.0,
            description="Min Lon:",
            style={'description_width': 'initial'},
            layout=Layout(width='200px')
        )
        
        min_lat = widgets.FloatText(
            value=-90.0,
            description="Min Lat:",
            style={'description_width': 'initial'},
            layout=Layout(width='200px')
        )
        
        max_lon = widgets.FloatText(
            value=180.0,
            description="Max Lon:",
            style={'description_width': 'initial'},
            layout=Layout(width='200px')
        )
        
        max_lat = widgets.FloatText(
            value=90.0,
            description="Max Lat:",
            style={'description_width': 'initial'},
            layout=Layout(width='200px')
        )
        
        # Create set bounds button
        set_button = widgets.Button(
            description="Set Bounds",
            button_style="primary",
            layout=Layout(width='150px')
        )
        
        # Create info output
        info_output = widgets.HTML(
            value="<p>Enter geographic bounds for your area of interest.</p>"
        )
        
        # Handle set button click
        def on_set(b):
            """Set bounds from inputs"""
            try:
                self.set_bounds(
                    panel_id,
                    min_lon.value,
                    min_lat.value,
                    max_lon.value,
                    max_lat.value
                )
                
                # Show success message
                info_output.value = "<p style='color: green'>✓ Bounds set successfully!</p>"
                
                # Create map to display bounds
                if panel_id not in self.maps:
                    self.maps[panel_id] = geemap.Map(
                        center=[0, 0],
                        zoom=2,
                        layout=Layout(width='100%', height='400px')
                    )
                
                # Display bounds on map
                bounds = self.geometries[panel_id + "_bounds"]
                self.maps[panel_id].center = bounds.center
                self.maps[panel_id].zoom = 4
                
                # Add rectangle to map
                rect = ee.Geometry.Rectangle([
                    min_lon.value, min_lat.value,
                    max_lon.value, max_lat.value
                ])
                
                # Clear previous layers
                self.maps[panel_id].layers = self.maps[panel_id].layers[:1]
                
                # Add new layer
                self.maps[panel_id].addLayer(
                    rect,
                    {'color': '3388ff'},
                    'Selected Area'
                )
                
                # Add map to container
                container.children = [
                    widgets.VBox([
                        widgets.HBox([min_lon, min_lat]),
                        widgets.HBox([max_lon, max_lat]),
                        set_button,
                        info_output
                    ]),
                    self.maps[panel_id]
                ]
                
            except ValueError as e:
                info_output.value = f"<p style='color: red'>Error: {str(e)}</p>"
        
        set_button.on_click(on_set)
        
        # Set current method
        self.current_method[panel_id] = "bounds"
        
        # Create container
        container = widgets.VBox([
            widgets.VBox([
                widgets.HBox([min_lon, min_lat]),
                widgets.HBox([max_lon, max_lat]),
                set_button,
                info_output
            ])
        ])
        
        return container
    
    def process_shapefile(self, panel_id: str, filepath: str) -> None:
        """
        Process uploaded shapefile
        
        Args:
            panel_id: Identifier for the panel ("left" or "right")
            filepath: Path to shapefile
            
        Raises:
            ValueError: If shapefile cannot be processed
        """
        try:
            # Read shapefile
            gdf = gpd.read_file(filepath)
            
            # Check projection
            if gdf.crs is None:
                raise ValueError("Shapefile has no CRS defined")
            
            # Convert to EPSG:4326 if needed
            if gdf.crs.to_string() != "EPSG:4326":
                gdf = gdf.to_crs(epsg=4326)
            
            # Get bounds
            bounds = gdf.total_bounds
            
            # Set bounds
            self.set_bounds(
                panel_id,
                bounds[0],
                bounds[1],
                bounds[2],
                bounds[3]
            )
            
            # Store geometry
            first_geom = gdf.geometry.iloc[0]
            self.geometries[panel_id] = ee.Geometry.Polygon(
                [[(p[0], p[1]) for p in list(first_geom.exterior.coords)]]
            )
            
        except Exception as e:
            raise ValueError(f"Error processing shapefile: {str(e)}")
    
    def set_bounds(self, panel_id: str, min_lon: float, min_lat: float, 
                  max_lon: float, max_lat: float) -> None:
        """
        Set geographic bounds
        
        Args:
            panel_id: Identifier for the panel ("left" or "right")
            min_lon: Minimum longitude
            min_lat: Minimum latitude
            max_lon: Maximum longitude
            max_lat: Maximum latitude
            
        Raises:
            ValueError: If bounds are invalid
        """
        # Validate bounds
        if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
            raise ValueError("Longitude must be between -180 and 180")
        
        if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        
        if min_lon >= max_lon or min_lat >= max_lat:
            raise ValueError("Minimum values must be less than maximum values")
        
        # Create bounds config
        bounds = BoundsConfig(min_lon, min_lat, max_lon, max_lat)
        
        # Store bounds
        self.geometries[panel_id + "_bounds"] = bounds
        
        # Create EE geometry if not already created
        if panel_id not in self.geometries:
            self.geometries[panel_id] = ee.Geometry.Rectangle(bounds.to_list())
    
    def get_geometry(self, panel_id: str) -> ee.Geometry:
        """
        Get Earth Engine geometry
        
        Args:
            panel_id: Identifier for the panel ("left" or "right")
            
        Returns:
            Earth Engine geometry
            
        Raises:
            ValueError: If no geometry is defined
        """
        if panel_id not in self.geometries:
            raise ValueError("No geometry defined for this panel")
        
        return self.geometries[panel_id]
    
    def get_bounds(self, panel_id: str) -> BoundsConfig:
        """
        Get bounds configuration
        
        Args:
            panel_id: Identifier for the panel ("left" or "right")
            
        Returns:
            BoundsConfig object
            
        Raises:
            ValueError: If no bounds are defined
        """
        bounds_key = panel_id + "_bounds"
        
        if bounds_key not in self.geometries:
            raise ValueError("No bounds defined for this panel")
        
        return self.geometries[bounds_key]
    
    def _cleanup_map(self, panel_id: str) -> None:
        """
        Clean up map resources
        
        Args:
            panel_id: Identifier for the panel ("left" or "right")
        """
        if panel_id in self.maps:
            try:
                # Remove draw control if it exists
                if panel_id in self.draw_controls:
                    self.maps[panel_id].remove_control(self.draw_controls[panel_id])
                    del self.draw_controls[panel_id]
                
                # Close map
                self.maps[panel_id].close()
                del self.maps[panel_id]
            except Exception as e:
                print(f"Warning: Error during map cleanup - {str(e)}")
    
    def copy_geometry(self, source_panel: str, target_panel: str) -> None:
        """
        Copy geometry from one panel to another with improved bounds handling
        
        Args:
            source_panel: Source panel ID ("left" or "right")
            target_panel: Target panel ID ("left" or "right")
        """
        try:
            # Get the current method being used in source panel
            source_method = self.current_method.get(source_panel, 'draw')
            target_method = self.current_method.get(target_panel, 'draw')
            
            print(f"Source method: {source_method}, Target method: {target_method}")
            
            # Make sure we have geometry for the source panel
            if source_panel not in self.geometries:
                print(f"No geometry found for {source_panel} panel")
                return
            
            # Deep copy the geometry to avoid reference issues
            source_geom = self.geometries[source_panel]
            if isinstance(source_geom, ee.Geometry):
                # For Earth Engine geometry, serialize and deserialize
                geom_json = source_geom.getInfo()
                target_geom = ee.Geometry(geom_json)
                self.geometries[target_panel] = target_geom
            else:
                # For other geometry types, use direct assignment
                self.geometries[target_panel] = source_geom
            
            # Copy bounds if they exist
            source_bounds_key = f"{source_panel}_bounds"
            target_bounds_key = f"{target_panel}_bounds"
            
            if source_bounds_key in self.geometries:
                # Copy bounds
                source_bounds = self.geometries[source_bounds_key]
                self.geometries[target_bounds_key] = source_bounds
                
                # If working with bounds UI, update the UI elements
                self._update_bounds_ui(target_panel, source_bounds)
                
            # Copy method
            if source_panel in self.current_method:
                self.current_method[target_panel] = self.current_method[source_panel]
            
            # Update map if it exists
            if target_panel in self.maps and source_panel in self.maps:
                try:
                    # Get source map center and zoom
                    source_map = self.maps[source_panel]
                    target_map = self.maps[target_panel]
                    
                    # Set target map center and zoom
                    target_map.center = source_map.center
                    target_map.zoom = source_map.zoom
                    
                    # Add geometry to map for visualization
                    if isinstance(source_geom, ee.Geometry):
                        # Clear previous layers
                        layers_to_remove = [layer for layer in target_map.layers[1:]]
                        for layer in layers_to_remove:
                            target_map.remove_layer(layer)
                        
                        # Add new layer
                        target_map.addLayer(
                            source_geom,
                            {'color': '3388ff'},
                            'Selected Area'
                        )
                except Exception as e:
                    print(f"Error updating map: {str(e)}")
            
            print(f"Geometry copied from {source_panel} to {target_panel}")
            
        except Exception as e:
            print(f"Error copying geometry: {str(e)}")

    def _update_bounds_ui(self, panel_id: str, bounds) -> None:
        """
        Update bounds UI widgets with copied bounds
        
        Args:
            panel_id: Panel ID
            bounds: Bounds configuration
        """
        try:
            # Skip if method is not 'bounds'
            if self.current_method.get(panel_id) != 'bounds':
                return
                
            # Get min/max values from bounds
            min_lon = bounds.min_lon
            min_lat = bounds.min_lat
            max_lon = bounds.max_lon
            max_lat = bounds.max_lat
            
            # Check if panel has a container for bounds widgets
            if panel_id in self.maps:
                # Get the map for this panel
                map_widget = self.maps[panel_id]
                
                # In a real implementation, we'd find bounds widgets in the UI
                # For this demo, we'll create a new bounds display
                rect = ee.Geometry.Rectangle([min_lon, min_lat, max_lon, max_lat])
                
                # Clear previous layers
                layers_to_remove = [layer for layer in map_widget.layers[1:]]
                for layer in layers_to_remove:
                    map_widget.remove_layer(layer)
                
                # Add new layer
                map_widget.addLayer(
                    rect,
                    {'color': '3388ff'},
                    'Selected Area'
                )
                
                # Center and zoom map to bounds
                map_widget.center = bounds.center
                map_widget.zoom = 4
                
                print(f"Updated bounds UI for {panel_id}: {min_lon}, {min_lat}, {max_lon}, {max_lat}")
        except Exception as e:
            print(f"Error updating bounds UI: {str(e)}")