"""
visualizer.py
Handles visualization of climate data analysis results
"""

import ee
import geemap
import numpy as np
import plotly.graph_objects as go
from typing import Dict, List, Any, Optional, Tuple
from ipywidgets import widgets, VBox, HBox, Layout, HTML
from IPython.display import display

class Visualizer:
    """
    Handles visualization of climate data analysis results
    """
    
    def __init__(self):
        """Initialize Visualizer"""
        pass
    
    def create_map(self, image: ee.Image, vis_params: Dict[str, Any], 
                title: str, center: Tuple[float, float] = None, 
                zoom: int = 3, start_year: int = None, end_year: int = None,
                year_callback: callable = None) -> widgets.VBox:
        """
        Create a map visualization for Earth Engine image with proper year toggling
        
        Args:
            image: Earth Engine image to visualize
            vis_params: Visualization parameters
            title: Layer title
            center: Optional center coordinates (lat, lon)
            zoom: Initial zoom level
            start_year: Start year for time range
            end_year: End year for time range
            year_callback: Callback to get image for a specific year
            
        Returns:
            Widget containing the map
        """
        # Create map
        m = geemap.Map(layout=Layout(width='100%', height='500px'))
        
        # Set center and zoom if provided
        if center:
            m.center = center
        else:
            # Try to center on image bounds
            try:
                bounds = image.geometry().bounds().getInfo()
                coords = bounds['coordinates'][0]
                lon = (coords[0][0] + coords[2][0]) / 2
                lat = (coords[0][1] + coords[2][1]) / 2
                m.center = [lat, lon]
            except:
                pass
        
        m.zoom = zoom
        
        # Add layer
        m.addLayer(image, vis_params, title)
        
        # Add color bar (we'll keep just one)
        m.add_colorbar(
            vis_params['palette'],
            vis_params['min'],
            vis_params['max'],
            title,
            position='bottomright'
        )
        
        # Create title
        map_title = HTML(value=f"<h5>{title}</h5>")
        
        # Create map widget (will be used for year selector creation)
        map_widget = VBox([
            map_title,
            m
        ])
        
        # Create year selector if time range is provided
        if start_year is not None and end_year is not None and start_year != end_year:
            year_selector = self.create_year_selector(
                start_year, 
                end_year,
                map_widget,  # Pass the map_widget for updates
                year_callback
            )
            
            # No legend toggle needed - we'll remove this control
            
            # Update map widget to include year selector
            map_widget = VBox([
                map_title,
                m,
                widgets.HBox([year_selector])
            ])
        
        # Create visualization controls
        vis_controls = self.create_visualization_controls(image, vis_params, map_widget, title)
        
        # Return combined widget
        return widgets.VBox([
            map_widget,
            vis_controls
        ])
    
    def create_temporal_plot(self, data: List[Dict[str, Any]], 
                           title: str, y_label: str) -> go.FigureWidget:
        """
        Create a temporal trend plot
        
        Args:
            data: List of dictionaries with 'year' and 'value' keys
            title: Plot title
            y_label: Y-axis label
            
        Returns:
            Plotly figure widget
        """
        # Check if data is available
        if not data:
            return HTML(value="<p style='color: orange'>No temporal data available for plotting</p>")
        
        # Extract years and values
        years = [d['year'] for d in data]
        values = [d['value'] for d in data]
        
        # Calculate trend line
        z = np.polyfit(years, values, 1)
        p = np.poly1d(z)
        trend_values = p(years)
        
        # Create figure
        fig = go.Figure()
        
        # Add data trace
        fig.add_trace(
            go.Scatter(
                x=years,
                y=values,
                mode='lines+markers',
                name='Observed',
                line=dict(color='#2166ac', width=2),
                marker=dict(size=8)
            )
        )
        
        # Add trend line
        fig.add_trace(
            go.Scatter(
                x=years,
                y=trend_values,
                mode='lines',
                name='Trend',
                line=dict(color='#b2182b', width=2, dash='dash')
            )
        )
        
        # Update layout
        fig.update_layout(
            title=dict(
                text=title,
                x=0.5,
                xanchor='center'
            ),
            xaxis=dict(
                title='Year',
                gridcolor='lightgrey',
                showgrid=True,
                zeroline=True,
                zerolinecolor='grey'
            ),
            yaxis=dict(
                title=y_label,
                gridcolor='lightgrey',
                showgrid=True,
                zeroline=True,
                zerolinecolor='grey'
            ),
            plot_bgcolor='white',
            width=800,
            height=400,
            margin=dict(l=50, r=50, t=70, b=50),
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor='rgba(255, 255, 255, 0.8)'
            )
        )
        
        # Create widget
        plot_widget = go.FigureWidget(fig)
        
        return plot_widget
    
    def create_year_selector(self, start_year: int, end_year: int, 
                        map_widget, image_callback) -> widgets.Dropdown:
        """
        Create year selection dropdown with proper callback
        
        Args:
            start_year: First year in range
            end_year: Last year in range
            map_widget: Map widget to update
            image_callback: Function to get image for a specific year
            
        Returns:
            Year selection dropdown
        """
        # Default years if not provided
        if start_year is None:
            start_year = 2020
        if end_year is None:
            end_year = 2020
        
        # Create dropdown with all years
        year_dropdown = widgets.Dropdown(
            options=list(range(start_year, end_year + 1)),
            value=end_year,
            description='Year:',
            style={'description_width': 'initial'},
            layout=Layout(width='150px'),
            disabled=start_year == end_year
        )
        
        # Create update function that actually updates the map
        def update_map_for_year(change):
            if not image_callback:
                return
                
            try:
                # Get the new year
                new_year = change.new
                
                # Get image for the new year
                new_image = image_callback(new_year)
                
                if new_image and map_widget:
                    # Get map from widget (second child is the map)
                    m = map_widget.children[1]
                    
                    # Get current layer
                    layer_name = None
                    for layer_key in m.layers.keys():
                        if layer_key.startswith('ee_layer_'):
                            layer_name = m.layers[layer_key].name
                            break
                    
                    if layer_name:
                        # Get current visualization parameters
                        vis_params = None
                        for layer in m.layers:
                            if hasattr(layer, 'name') and layer.name == layer_name:
                                vis_params = layer.vis_params
                                break
                        
                        if not vis_params:
                            # Default vis params
                            vis_params = {
                                'min': 0,
                                'max': 100,
                                'palette': ['blue', 'white', 'red']
                            }
                        
                        # Remove old layer
                        m.remove_layer(layer_name)
                        
                        # Add new layer with the same name
                        m.addLayer(new_image, vis_params, layer_name)
                        
                        # Update colorbar if needed
                        try:
                            m.remove_colorbar()
                            m.add_colorbar(
                                vis_params['palette'],
                                vis_params['min'],
                                vis_params['max'],
                                layer_name,
                                position='bottomright'
                            )
                        except:
                            pass
                        
                        print(f"Map updated for year {new_year}")
                        
            except Exception as e:
                print(f"Error updating map for year {change.new}: {str(e)}")
        
        # Set callback for year change
        year_dropdown.observe(update_map_for_year, names='value')
        
        return year_dropdown
    
    def create_comparison_visualization(self, left_results: Dict[str, Any], 
                                      right_results: Dict[str, Any]) -> widgets.HBox:
        """
        Create side-by-side comparison visualization
        
        Args:
            left_results: Results for left panel
            right_results: Results for right panel
            
        Returns:
            Widget with side-by-side comparison
        """
        # Create title
        title = HTML(value="<h4>Comparison Visualization</h4>")
        
        # Create left map
        left_map = self.create_map(
            left_results["data"],
            left_results["vis_params"],
            f"{left_results['index']} ({left_results['dataset']})"
        )
        
        # Create right map
        right_map = self.create_map(
            right_results["data"],
            right_results["vis_params"],
            f"{right_results['index']} ({right_results['dataset']})"
        )
        
        # Create comparison table
        comparison_table = self._create_comparison_table(left_results, right_results)
        
        # Assemble comparison widget
        comparison_widget = VBox([
            title,
            HBox([left_map, right_map], layout=Layout(width='100%')),
            comparison_table
        ])
        
        return comparison_widget
    
    def _create_comparison_table(self, left_results: Dict[str, Any], 
                               right_results: Dict[str, Any]) -> widgets.HTML:
        """
        Create a comparison table
        
        Args:
            left_results: Results for left panel
            right_results: Results for right panel
            
        Returns:
            HTML widget with comparison table
        """
        # Calculate statistics
        left_values = [d['value'] for d in left_results.get('temporal_data', [])]
        right_values = [d['value'] for d in right_results.get('temporal_data', [])]
        
        left_mean = np.mean(left_values) if left_values else "N/A"
        right_mean = np.mean(right_values) if right_values else "N/A"
        
        left_min = np.min(left_values) if left_values else "N/A"
        right_min = np.min(right_values) if right_values else "N/A"
        
        left_max = np.max(left_values) if left_values else "N/A"
        right_max = np.max(right_values) if right_values else "N/A"
        
        left_trend = "Increasing" if left_values and len(left_values) > 1 and np.polyfit(range(len(left_values)), left_values, 1)[0] > 0 else "Decreasing"
        right_trend = "Increasing" if right_values and len(right_values) > 1 and np.polyfit(range(len(right_values)), right_values, 1)[0] > 0 else "Decreasing"
        
        # Create table
        table_html = f"""
        <table style="width:100%; border-collapse: collapse; margin: 20px 0;">
            <thead>
                <tr style="background-color: #f0f0f0;">
                    <th style="padding: 8px; border: 1px solid #ddd;">Metric</th>
                    <th style="padding: 8px; border: 1px solid #ddd;">{left_results['index']} ({left_results['dataset']})</th>
                    <th style="padding: 8px; border: 1px solid #ddd;">{right_results['index']} ({right_results['dataset']})</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">Mean</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{left_mean} {left_results['units']}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{right_mean} {right_results['units']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">Min</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{left_min} {left_results['units']}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{right_min} {right_results['units']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">Max</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{left_max} {left_results['units']}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{right_max} {right_results['units']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">Trend</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{left_trend}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{right_trend}</td>
                </tr>
            </tbody>
        </table>
        """
        
        return HTML(value=table_html)
    
    def create_summary_stats(self, results: Dict[str, Any]) -> widgets.HTML:
        """
        Create summary statistics display
        
        Args:
            results: Analysis results
            
        Returns:
            HTML widget with summary statistics
        """
        # Extract values
        values = [d['value'] for d in results.get('temporal_data', [])]
        
        if not values:
            return HTML(value="<p>No data available for statistics</p>")
        
        # Calculate statistics
        mean_val = np.mean(values)
        min_val = np.min(values)
        max_val = np.max(values)
        std_val = np.std(values)
        
        # Create HTML
        stats_html = f"""
        <div style="padding: 10px; background: #f5f5f5; border-radius: 5px; margin: 10px 0;">
            <h5 style="margin-top: 0;">Summary Statistics</h5>
            <table style="width:100%;">
                <tr><td>Mean:</td><td>{mean_val:.2f} {results['units']}</td></tr>
                <tr><td>Min:</td><td>{min_val:.2f} {results['units']}</td></tr>
                <tr><td>Max:</td><td>{max_val:.2f} {results['units']}</td></tr>
                <tr><td>Standard Deviation:</td><td>{std_val:.2f} {results['units']}</td></tr>
            </table>
        </div>
        """
        
        return HTML(value=stats_html)
    
    def create_visualization_controls(self, image, vis_params, map_widget, layer_name):
        """
        Create controls for adjusting visualization parameters
        
        Args:
            image: Earth Engine image
            vis_params: Current visualization parameters
            map_widget: Map widget to update
            layer_name: Name of the layer to update
            
        Returns:
            Widget with visualization controls
        """
        # Get current visualization parameters
        current_min = vis_params.get('min', 0)
        current_max = vis_params.get('max', 100)
        current_palette = vis_params.get('palette', ['blue', 'white', 'red'])
        
        # Create min/max sliders
        min_slider = widgets.FloatSlider(
            value=current_min,
            min=current_min * 0.5 if current_min != 0 else -10,
            max=current_max,
            step=(current_max - current_min) / 100 if current_max > current_min else 1,
            description='Min:',
            style={'description_width': 'initial'},
            layout=Layout(width='250px')
        )
        
        max_slider = widgets.FloatSlider(
            value=current_max,
            min=current_min,
            max=current_max * 1.5 if current_max != 0 else 100,
            step=(current_max - current_min) / 100 if current_max > current_min else 1,
            description='Max:',
            style={'description_width': 'initial'},
            layout=Layout(width='250px')
        )
        
        # Create palette selector
        palette_options = {
            'Blue-White-Red': ['blue', 'white', 'red'],
            'Viridis': ['#440154', '#414487', '#2a788e', '#22a884', '#7ad151', '#fde725'],
            'Plasma': ['#0d0887', '#5302a3', '#8b0aa5', '#b83289', '#db5c68', '#f48849', '#febc2a'],
            'Blues': ['#f7fbff', '#deebf7', '#c6dbef', '#9ecae1', '#6baed6', '#4292c6', '#2171b5', '#084594'],
            'Reds': ['#fff5f0', '#fee0d2', '#fcbba1', '#fc9272', '#fb6a4a', '#ef3b2c', '#cb181d', '#99000d'],
            'Terrain': ['#008837', '#a4da87', '#ffffcc', '#e0c18a', '#b30000'],
            'Spectral': ['#9e0142', '#d53e4f', '#f46d43', '#fdae61', '#fee08b', '#ffffbf', '#e6f598', '#abdda4', '#66c2a5', '#3288bd', '#5e4fa2']
        }
        
        palette_dropdown = widgets.Dropdown(
            options=list(palette_options.keys()),
            value='Blue-White-Red',
            description='Palette:',
            style={'description_width': 'initial'},
            layout=Layout(width='250px')
        )
        
        # Create stretch type selector with better options
        stretch_options = ['None', 'Min-Max', 'Percentile (2-98%)', 'Percentile (5-95%)', 'Data Range + 10%']
        stretch_dropdown = widgets.Dropdown(
            options=stretch_options,
            value='None',
            description='Stretch:',
            style={'description_width': 'initial'},
            layout=Layout(width='250px')
        )
        
        # Create apply button
        apply_button = widgets.Button(
            description='Apply Changes',
            button_style='primary',
            layout=Layout(width='150px')
        )
        
        # Status message
        status_message = widgets.HTML(value="")
        
        # Apply button handler
        def on_apply(b):
            try:
                # Get current values
                min_val = min_slider.value
                max_val = max_slider.value
                palette_name = palette_dropdown.value
                stretch_type = stretch_dropdown.value
                
                # Update status
                status_message.value = "<p>Updating visualization...</p>"
                
                # Get palette
                palette = palette_options[palette_name]
                
                # Apply stretch if selected
                if stretch_type != 'None':
                    try:
                        if stretch_type == 'Min-Max':
                            # Calculate min/max for the region
                            stats = image.reduceRegion(
                                reducer=ee.Reducer.minMax(),
                                geometry=image.geometry(),
                                scale=1000,
                                maxPixels=1e9
                            ).getInfo()
                            
                            # Extract min/max values (use first band's values)
                            band_keys = [k for k in stats.keys() if k.endswith('_min') or k.endswith('_max')]
                            if band_keys:
                                min_key = [k for k in band_keys if k.endswith('_min')][0]
                                max_key = [k for k in band_keys if k.endswith('_max')][0]
                                min_val = stats[min_key]
                                max_val = stats[max_key]
                        
                        elif stretch_type.startswith('Percentile'):
                            # Extract percentile values
                            if '2-98%' in stretch_type:
                                low_pct = 2
                                high_pct = 98
                            else:  # 5-95%
                                low_pct = 5
                                high_pct = 95
                            
                            # Calculate percentiles
                            percentiles = image.reduceRegion(
                                reducer=ee.Reducer.percentile([low_pct, high_pct]),
                                geometry=image.geometry(),
                                scale=1000,
                                maxPixels=1e9
                            ).getInfo()
                            
                            # Extract percentile values (use first band's values)
                            band_keys = list(percentiles.keys())
                            if band_keys:
                                first_band = band_keys[0].split('_')[0]
                                min_val = percentiles.get(f"{first_band}_{low_pct}", min_val)
                                max_val = percentiles.get(f"{first_band}_{high_pct}", max_val)
                        
                        elif stretch_type == 'Data Range + 10%':
                            # Calculate min/max for the region
                            stats = image.reduceRegion(
                                reducer=ee.Reducer.minMax(),
                                geometry=image.geometry(),
                                scale=1000,
                                maxPixels=1e9
                            ).getInfo()
                            
                            # Extract min/max values (use first band's values)
                            band_keys = [k for k in stats.keys() if k.endswith('_min') or k.endswith('_max')]
                            if band_keys:
                                min_key = [k for k in band_keys if k.endswith('_min')][0]
                                max_key = [k for k in band_keys if k.endswith('_max')][0]
                                data_min = stats[min_key]
                                data_max = stats[max_key]
                                
                                # Add 10% padding
                                range_val = data_max - data_min
                                min_val = data_min - (range_val * 0.1)
                                max_val = data_max + (range_val * 0.1)
                        
                        # Update sliders with new values
                        min_slider.min = min_val * 0.8 if min_val != 0 else -10
                        min_slider.max = max_val
                        min_slider.value = min_val
                        
                        max_slider.min = min_val
                        max_slider.max = max_val * 1.2 if max_val != 0 else 100
                        max_slider.value = max_val
                        
                    except Exception as e:
                        status_message.value = f"<p style='color: orange'>Warning: Could not compute stretch values: {str(e)}</p>"
                
                # Create new visualization parameters
                new_vis_params = {
                    'min': min_val,
                    'max': max_val,
                    'palette': palette,
                    'opacity': vis_params.get('opacity', 0.8)
                }
                
                # Access the map object
                m = map_widget.children[1]
                
                # Remove old layer and add new one
                m.remove_layer(layer_name)
                m.addLayer(image, new_vis_params, layer_name)
                
                # Update colorbar
                try:
                    # First remove existing colorbar if any
                    if hasattr(m, 'colorbar') and m.colorbar is not None:
                        m.remove_colorbar()
                    
                    # Add new colorbar with the actual min/max values
                    m.add_colorbar(
                        new_vis_params['palette'],
                        new_vis_params['min'],
                        new_vis_params['max'],
                        layer_name,
                        position='bottomright'
                    )
                except Exception as e:
                    print(f"Error updating colorbar: {str(e)}")
                
                status_message.value = "<p style='color: green'>Visualization updated!</p>"
                
            except Exception as e:
                status_message.value = f"<p style='color: red'>Error updating visualization: {str(e)}</p>"
        
        apply_button.on_click(on_apply)
        
        # Create visualization controls container
        controls = widgets.VBox([
            widgets.HTML(value="<h5>Visualization Controls</h5>"),
            widgets.HBox([min_slider, max_slider]),
            widgets.HBox([palette_dropdown, stretch_dropdown]),
            widgets.HBox([apply_button, status_message])
        ])
        
        return controls