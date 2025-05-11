"""
climate_tool.py
Main Climate Analysis Tool application with enhanced features
"""

import ee
import os
import numpy as np
from IPython.display import display, clear_output
from ipywidgets import widgets, VBox, HBox, Layout, Tab, HTML

from authentication import AuthenticationManager
from data_manager import DataManager
from geometry_manager import GeometryManager
from analysis_engine import AnalysisEngine
from visualizer import Visualizer
from exporter import Exporter

class ClimateAnalysisTool:
    """Enhanced Climate Analysis Tool with comparison and CLI features"""
    
    def __init__(self):
        """Initialize the Climate Analysis Tool"""
        self.auth_manager = AuthenticationManager()
        
        # These will be initialized after authentication
        self.data_manager = None
        self.geometry_manager = None
        self.analysis_engine = None
        self.visualizer = None
        self.exporter = None
        
        # State tracking with properly initialized nested dictionaries
        self.current_session = {
            "left_panel": {"widgets": {}, "state": {}},
            "right_panel": {"widgets": {}, "state": {}},
            "comparison_active": False
        }
        
        # UI containers
        self.main_container = None
        self.left_panel = None
        self.right_panel = None
        self.export_panel = None
    
    def start(self):
        """Start the Climate Analysis Tool application"""
        print("Starting Climate Analysis Tool...")
        
        # Try to load saved credentials
        self.auth_manager.load_credentials()
        
        # Create and display authentication widgets
        auth_container, start_button = self.auth_manager.create_auth_widgets()
        
        # Set up start button callback
        def on_start(b):
            self._initialize_components()
            self._create_main_interface()
        
        start_button.on_click(on_start)
        
        # Display authentication widgets
        display(auth_container)
    
    def _initialize_components(self):
        """Initialize tool components after authentication"""
        self.data_manager = DataManager()
        self.geometry_manager = GeometryManager()
        self.analysis_engine = AnalysisEngine(self.data_manager)
        self.visualizer = Visualizer()
        self.exporter = Exporter()
    
    def _create_main_interface(self):
        """Create the main tool interface after authentication"""
        clear_output(wait=True)
        
        # Create header
        header = widgets.HTML(
            value="""
            <div style="background-color: #f0f0f0; padding: 10px; border-radius: 5px; margin-bottom: 20px;">
                <h1 style="text-align: center; margin: 0;">Climate Analysis Tool</h1>
                <p style="text-align: center; margin: 5px 0 0 0;">Analyze climate data with Earth Engine</p>
            </div>
            """
        )
        
        # Create tabs for different tool sections
        tabs = self._create_tab_interface()
        
        # Create footer with information
        footer = widgets.HTML(
            value="""
            <div style="margin-top: 20px; padding: 10px; background-color: #f0f0f0; border-radius: 5px;">
                <p style="text-align: center; margin: 0;">
                    Climate Analysis Tool | Earth Engine Integration | v2.0
                </p>
            </div>
            """
        )
        
        # Assemble main container
        self.main_container = VBox([header, tabs, footer], layout=Layout(width='100%'))
        display(self.main_container)
    
    def _create_tab_interface(self):
        """Create tabbed interface for the tool"""
        # Create analysis tab
        analysis_tab = self._create_analysis_interface()
        
        # Create CLI tab
        cli_tab = self._create_cli_interface()
        
        # Create help tab
        help_tab = self._create_help_interface()
        
        # Create tab widget
        tab_widget = Tab([analysis_tab, cli_tab, help_tab])
        tab_widget.set_title(0, 'Analysis')
        tab_widget.set_title(1, 'Command Line')
        tab_widget.set_title(2, 'Help')
        
        return tab_widget
    
    def _create_analysis_interface(self):
        """Create the main analysis interface with comparison panels"""
        # Create left panel for primary analysis
        self.left_panel = self._create_analysis_panel("left")
        
        # Create center controls for comparison
        center_controls = self._create_comparison_controls()
        
        # Create right panel (initially hidden)
        self.right_panel = self._create_analysis_panel("right")
        self.right_panel.layout.display = 'none'
        
        # Create export panel
        self.export_panel = self._create_export_panel()
        
        # Assemble analysis interface
        analysis_container = widgets.VBox([
            widgets.HBox([self.left_panel, center_controls, self.right_panel], 
                        layout=Layout(width='100%')),
            self.export_panel
        ])
        
        return analysis_container
    
    def _create_analysis_panel(self, panel_id):
        """Create an analysis panel (left or right side)"""
        # Panel title
        title = "Primary Analysis" if panel_id == "left" else "Comparison Analysis"
        panel_header = widgets.HTML(
            value=f"<h3>{title}</h3>"
        )
        
        # Step 1: Area of Interest
        step1 = self._create_area_selection(panel_id)
        
        # Step 2: Time Range
        step2 = self._create_time_range_selection(panel_id)
        
        # Step 3: Dataset Selection
        step3 = self._create_dataset_selection(panel_id)
        
        # Step 4: Parameter Selection
        step4 = self._create_parameter_selection(panel_id)
        
        # Step 5: Index Selection
        step5 = self._create_index_selection(panel_id)
        
        # Analysis Button
        analyze_button = widgets.Button(
            description="Analyze",
            button_style="primary",
            layout=Layout(width='100px')
        )
        
        # Results container
        results_container = widgets.VBox([])
        
        # Handle analyze button click
        def on_analyze(b):
            # Update state
            self._update_panel_state(panel_id)
            
            # Run analysis
            self._run_analysis(panel_id, results_container)
        
        analyze_button.on_click(on_analyze)
        
        # Assemble panel
        panel = widgets.VBox([
            panel_header,
            widgets.HTML(value="<h4>Step 1: Choose Area of Interest</h4>"),
            step1,
            widgets.HTML(value="<h4>Step 2: Select Time Range</h4>"),
            step2,
            widgets.HTML(value="<h4>Step 3: Select Dataset</h4>"),
            step3,
            widgets.HTML(value="<h4>Step 4: Select Parameter</h4>"),
            step4,
            widgets.HTML(value="<h4>Step 5: Select Index</h4>"),
            step5,
            analyze_button,
            widgets.HTML(value="<h4>Results</h4>"),
            results_container
        ], layout=Layout(width='48%', border='1px solid #ddd', padding='10px'))
        
        # Store references to widgets
        if panel_id == "left":
            self.current_session["left_panel"]["widgets"] = {
                "step1": step1,
                "step2": step2,
                "step3": step3,
                "step4": step4,
                "step5": step5,
                "results": results_container
            }
        else:
            self.current_session["right_panel"]["widgets"] = {
                "step1": step1,
                "step2": step2,
                "step3": step3,
                "step4": step4,
                "step5": step5,
                "results": results_container
            }
        
        # Finalize widget connections after all widgets are created
        self._finalize_widget_connections()
        
        return panel
    
    def _create_area_selection(self, panel_id):
        """Create area selection widgets"""
        # Method selection
        method_dropdown = widgets.Dropdown(
            options=['Draw on Map', 'Shapefile', 'Geometric Bounds'],
            description='Method:',
            style={'description_width': 'initial'},
            layout=Layout(width='300px')
        )
        
        # Area widget container
        area_container = widgets.VBox([])
        
        # Method change handler
        def on_method_change(change):
            area_container.children = []
            
            if change.new == 'Draw on Map':
                map_widget = self.geometry_manager.create_map_widget(panel_id)
                area_container.children = [map_widget]
            elif change.new == 'Shapefile':
                shapefile_widgets = self.geometry_manager.create_shapefile_widgets(panel_id)
                area_container.children = [shapefile_widgets]
            elif change.new == 'Geometric Bounds':
                bounds_widgets = self.geometry_manager.create_bounds_widgets(panel_id)
                area_container.children = [bounds_widgets]
        
        method_dropdown.observe(on_method_change, names='value')
        
        # Trigger initial setup - FIX HERE
        # Option 1: Use initial setup directly instead of simulating a change event
        if method_dropdown.options:
            map_widget = self.geometry_manager.create_map_widget(panel_id)
            area_container.children = [map_widget]
        
        return widgets.VBox([method_dropdown, area_container])
    
    def _finalize_widget_connections(self):
        """
        Establish connections between widgets after all widgets are created.
        This resolves dependency issues during widget creation.
        """
        if hasattr(self, '_pending_widget_connections'):
            for setup_func in self._pending_widget_connections:
                try:
                    setup_func()
                except Exception as e:
                    print(f"Warning: Error finalizing widget connection: {str(e)}")
            
            # Clear the list after processing
            self._pending_widget_connections = []
    
    def _create_time_range_selection(self, panel_id):
        """Create time range selection widgets"""
        # Year sliders
        start_year = widgets.IntSlider(
            value=1980,
            min=1980,
            max=2023,
            description='Start Year:',
            style={'description_width': 'initial'},
            layout=Layout(width='300px')
        )
        
        end_year = widgets.IntSlider(
            value=2020,
            min=1980,
            max=2023,
            description='End Year:',
            style={'description_width': 'initial'},
            layout=Layout(width='300px')
        )
        
        # Link the sliders so end_year >= start_year
        def on_start_year_change(change):
            if end_year.value < change.new:
                end_year.value = change.new
        
        def on_end_year_change(change):
            if start_year.value > change.new:
                start_year.value = change.new
        
        start_year.observe(on_start_year_change, names='value')
        end_year.observe(on_end_year_change, names='value')
        
        return widgets.VBox([start_year, end_year])
    
    def _create_dataset_selection(self, panel_id):
        """Create dataset selection widgets"""
        # Dataset selection
        dataset_dropdown = widgets.Dropdown(
            options=['ERA5', 'PRISM', 'DAYMET'],
            description='Dataset:',
            style={'description_width': 'initial'},
            layout=Layout(width='300px')
        )
        
        # Dataset info display
        info_display = widgets.HTML(
            value="<p><em>ERA5: Global reanalysis dataset with high spatial resolution.</em></p>"
        )
        
        # Update info on selection change
        def on_dataset_change(change):
            if change.new == 'ERA5':
                info_display.value = "<p><em>ERA5: Global reanalysis dataset with high spatial resolution.</em></p>"
            elif change.new == 'PRISM':
                info_display.value = "<p><em>PRISM: High-resolution dataset for the contiguous United States.</em></p>"
            elif change.new == 'DAYMET':
                info_display.value = "<p><em>DAYMET: Daily surface weather data over North America.</em></p>"
        
        dataset_dropdown.observe(on_dataset_change, names='value')
        
        return widgets.VBox([dataset_dropdown, info_display])
    
    def _create_parameter_selection(self, panel_id):
        """Create parameter selection widgets"""
        # Parameter selection
        parameter_dropdown = widgets.Dropdown(
            options=['Precipitation', 'Temperature'],
            description='Parameter:',
            style={'description_width': 'initial'},
            layout=Layout(width='300px')
        )
        
        return parameter_dropdown

    def _create_index_selection(self, panel_id):
        """Create index selection widgets"""
        # Index selection - will be updated based on parameter
        index_dropdown = widgets.Dropdown(
            options=[],
            description='Index:',
            style={'description_width': 'initial'},
            layout=Layout(width='400px')
        )
        
        # Index info display
        info_display = widgets.HTML(value="")
        
        # Preload index options regardless of parameter
        # We'll filter them later when parameter is known
        all_precipitation_indices = [
            'Annual total precipitation',
            'Annual maximum 1-day precipitation',
            'Number of wet days',
            'Consecutive dry days'
        ]
        
        all_temperature_indices = [
            'Annual maximum temperature',
            'Annual minimum temperature',
            'Frost days',
            'Summer days'
        ]
        
        # Start with precipitation indices by default
        index_dropdown.options = all_precipitation_indices
        
        # This will be called after all widgets are created
        # to establish the connection between step4 and step5
        def setup_parameter_dependency():
            try:
                panel_widgets = self.current_session.get(f"{panel_id}_panel", {}).get("widgets", {})
                parameter_dropdown = panel_widgets.get("step4")
                
                if parameter_dropdown:
                    # Define the handler
                    def on_parameter_change(change):
                        if change.new == 'Precipitation':
                            index_dropdown.options = all_precipitation_indices
                        else:  # Temperature
                            index_dropdown.options = all_temperature_indices
                    
                    # Connect the handler
                    parameter_dropdown.observe(on_parameter_change, names='value')
                    
                    # Initialize with current value
                    if parameter_dropdown.value == 'Temperature':
                        index_dropdown.options = all_temperature_indices
            except Exception as e:
                print(f"Warning: Could not setup parameter dependency: {str(e)}")
        
        # Store the setup function to be called later
        if not hasattr(self, '_pending_widget_connections'):
            self._pending_widget_connections = []
        
        self._pending_widget_connections.append(setup_parameter_dependency)
        
        # Index change handler
        def on_index_change(change):
            if change.new and hasattr(self, 'analysis_engine') and self.analysis_engine:
                try:
                    # Get index info from analysis engine
                    index_info = self.analysis_engine.get_index_info(change.new)
                    info_display.value = f"<p><em>{index_info['description']} (Units: {index_info['units']})</em></p>"
                except Exception as e:
                    info_display.value = f"<p><em>No information available for {change.new}</em></p>"
        
        index_dropdown.observe(on_index_change, names='value')
        
        return widgets.VBox([index_dropdown, info_display])
    
    def _create_comparison_controls(self):
        """Create controls for comparison functionality with improved lat/long copying"""
        # Toggle comparison button
        compare_button = widgets.Button(
            description="Enable Comparison",
            button_style="info",
            layout=Layout(width='150px')
        )
        
        # Copy settings buttons
        copy_left_to_right = widgets.Button(
            description="→",
            tooltip="Copy left settings to right",
            layout=Layout(width='40px'),
            disabled=True
        )
        
        copy_right_to_left = widgets.Button(
            description="←",
            tooltip="Copy right settings to left",
            layout=Layout(width='40px'),
            disabled=True
        )
        
        # Status display
        status_display = widgets.HTML(
            value="<p><em>Comparison disabled</em></p>"
        )
        
        # Toggle comparison handler
        def on_compare_toggle(b):
            if self.current_session["comparison_active"]:
                # Disable comparison
                self.current_session["comparison_active"] = False
                self.right_panel.layout.display = 'none'
                compare_button.description = "Enable Comparison"
                copy_left_to_right.disabled = True
                copy_right_to_left.disabled = True
                status_display.value = "<p><em>Comparison disabled</em></p>"
            else:
                # Enable comparison
                self.current_session["comparison_active"] = True
                self.right_panel.layout.display = 'block'
                compare_button.description = "Disable Comparison"
                copy_left_to_right.disabled = False
                copy_right_to_left.disabled = False
                status_display.value = "<p><em>Comparison enabled</em></p>"
        
        compare_button.on_click(on_compare_toggle)
        
        # Copy settings handlers
        def on_copy_left_to_right(b):
            try:
                status_display.value = "<p><em>Copying settings from left to right...</em></p>"
                
                # Get left panel widgets
                left_widgets = self.current_session["left_panel"]["widgets"]
                
                # Get right panel widgets
                right_widgets = self.current_session["right_panel"]["widgets"]
                
                # Copy geometry first (this will handle bounds transfer)
                self.geometry_manager.copy_geometry("left", "right")
                
                # Copy time range settings (step 2)
                if "step2" in left_widgets and "step2" in right_widgets:
                    # Copy start year
                    right_widgets["step2"].children[0].value = left_widgets["step2"].children[0].value
                    # Copy end year
                    right_widgets["step2"].children[1].value = left_widgets["step2"].children[1].value
                
                # Copy dataset selection (step 3)
                if "step3" in left_widgets and "step3" in right_widgets:
                    right_widgets["step3"].children[0].value = left_widgets["step3"].children[0].value
                
                # Copy parameter selection (step 4)
                if "step4" in left_widgets and "step4" in right_widgets:
                    right_widgets["step4"].value = left_widgets["step4"].value
                
                # Copy index selection (step 5)
                if "step5" in left_widgets and "step5" in right_widgets:
                    right_widgets["step5"].children[0].value = left_widgets["step5"].children[0].value
                
                # Update status with success message and details
                has_bounds = "left_bounds" in self.geometry_manager.geometries
                bounds_info = ""
                if has_bounds:
                    bounds = self.geometry_manager.geometries["left_bounds"]
                    bounds_info = f"<br>Bounds copied: [{bounds.min_lon:.2f}, {bounds.min_lat:.2f}, {bounds.max_lon:.2f}, {bounds.max_lat:.2f}]"
                    
                status_display.value = f"<p><em style='color: green'>Settings copied from left to right!{bounds_info}</em></p>"
                
            except Exception as e:
                status_display.value = f"<p><em style='color: red'>Error copying settings: {str(e)}</em></p>"
                print(f"Error copying settings: {str(e)}")
        
        def on_copy_right_to_left(b):
            try:
                status_display.value = "<p><em>Copying settings from right to left...</em></p>"
                
                # Get left panel widgets
                left_widgets = self.current_session["left_panel"]["widgets"]
                
                # Get right panel widgets
                right_widgets = self.current_session["right_panel"]["widgets"]
                
                # Copy geometry first (this will handle bounds transfer)
                self.geometry_manager.copy_geometry("right", "left")
                
                # Copy time range settings (step 2)
                if "step2" in right_widgets and "step2" in left_widgets:
                    # Copy start year
                    left_widgets["step2"].children[0].value = right_widgets["step2"].children[0].value
                    # Copy end year
                    left_widgets["step2"].children[1].value = right_widgets["step2"].children[1].value
                
                # Copy dataset selection (step 3)
                if "step3" in right_widgets and "step3" in left_widgets:
                    left_widgets["step3"].children[0].value = right_widgets["step3"].children[0].value
                
                # Copy parameter selection (step 4)
                if "step4" in right_widgets and "step4" in left_widgets:
                    left_widgets["step4"].value = right_widgets["step4"].value
                
                # Copy index selection (step 5)
                if "step5" in right_widgets and "step5" in left_widgets:
                    left_widgets["step5"].children[0].value = right_widgets["step5"].children[0].value
                
                # Update status with success message and details
                has_bounds = "right_bounds" in self.geometry_manager.geometries
                bounds_info = ""
                if has_bounds:
                    bounds = self.geometry_manager.geometries["right_bounds"]
                    bounds_info = f"<br>Bounds copied: [{bounds.min_lon:.2f}, {bounds.min_lat:.2f}, {bounds.max_lon:.2f}, {bounds.max_lat:.2f}]"
                    
                status_display.value = f"<p><em style='color: green'>Settings copied from right to left!{bounds_info}</em></p>"
                
            except Exception as e:
                status_display.value = f"<p><em style='color: red'>Error copying settings: {str(e)}</em></p>"
                print(f"Error copying settings: {str(e)}")
        
        copy_left_to_right.on_click(on_copy_left_to_right)
        copy_right_to_left.on_click(on_copy_right_to_left)
        
        # Assemble controls in a vertical layout
        controls = widgets.VBox([
            compare_button,
            widgets.HBox([copy_left_to_right, copy_right_to_left],
                        layout=Layout(justify_content='center')),
            status_display
        ], layout=Layout(width='160px', align_items='center', justify_content='center'))
        
        return controls
    
    def _create_export_panel(self):
        """Create the export panel with options"""
        # Panel title
        export_header = widgets.HTML(
            value="<h3>Export Options</h3>"
        )
        
        # Export current view button
        export_current_btn = widgets.Button(
            description="Export Current View",
            button_style="success",
            layout=Layout(width='200px')
        )
        
        # Export all data button
        export_all_btn = widgets.Button(
            description="Export All Data",
            button_style="success",
            layout=Layout(width='200px')
        )
        
        # Format selection
        format_dropdown = widgets.Dropdown(
            options=['GeoTIFF', 'CSV', 'NetCDF'],
            value='GeoTIFF',
            description='Format:',
            style={'description_width': 'initial'},
            layout=Layout(width='200px')
        )
        
        # Create progress bar
        progress = widgets.IntProgress(
            value=0,
            min=0,
            max=100,
            description='Progress:',
            bar_style='info',
            style={'description_width': 'initial'},
            layout=Layout(width='50%', visibility='hidden')
        )
        
        # Create status display with better styling
        status_display = widgets.HTML(
            value="",
            layout=Layout(width='100%')
        )
        
        # Status update callback function
        def update_status(message, progress_value=None, is_error=False, is_success=False):
            # Update progress bar if value provided
            if progress_value is not None:
                progress.value = progress_value
                progress.layout.visibility = 'visible'
                
                # Hide progress bar when complete
                if progress_value >= 100:
                    progress.bar_style = 'success'
            
            # Style the message based on type
            style = ""
            if is_error:
                style = "color: #dc3545; background: #f8d7da; padding: 10px; border-radius: 5px;"
            elif is_success:
                style = "color: #28a745; background: #d4edda; padding: 10px; border-radius: 5px;"
            else:
                style = "background: #f8f9fa; padding: 10px; border-radius: 5px;"
                
            # Update status message
            status_display.value = f"<div style='{style}'>{message}</div>"
        
        # Export button handlers
        def on_export_current(b):
            # Reset progress bar
            progress.value = 0
            progress.bar_style = 'info'
            progress.layout.visibility = 'visible'
            
            # Show initial status
            update_status("<p>Initializing export of current view...</p>")
            
            # Get current panel data
            active_panel = "left_panel"
            if self.current_session["comparison_active"]:
                # Determine which panel is active based on most recent analysis
                # For now we'll just default to left
                active_panel = "left_panel"
            
            # Ensure we have the state information
            panel_state = self.current_session[active_panel].get("state", {})
            panel_results = self.current_session[active_panel].get("results", {})
            
            # Verify data availability
            if not panel_results.get("data"):
                update_status("<p>No data available for export. Please run analysis first.</p>", is_error=True)
                progress.layout.visibility = 'hidden'
                return
            
            # Get dataset, parameter, and index with proper fallbacks
            dataset = panel_state.get("dataset")
            if not dataset:
                dataset = panel_results.get("dataset", "general")
            
            parameter = panel_state.get("parameter")
            if not parameter:
                parameter = panel_results.get("parameter", "climate")
            
            index = panel_state.get("index")
            if not index:
                index = panel_results.get("index", "data")
            
            # Create comprehensive panel data with all necessary metadata
            panel_data = {
                "state": panel_state,
                "data": panel_results.get("data"),
                "results": panel_results,
                "temporal_data": panel_results.get("temporal_data", []),
                "analysis_engine": self.analysis_engine,  # Pass the analysis engine for recreating data
                "dataset": dataset,
                "parameter": parameter,
                "index": index,
                "time_range": panel_state.get("time_range", panel_results.get("time_range", (2020, 2020)))
            }
            
            # Print debug info to console
            print(f"Export data: dataset={panel_data['dataset']}, parameter={panel_data['parameter']}, index={panel_data['index']}")
            
            # Get selected format
            format_type = format_dropdown.value
            
            try:
                # Define status callback for real-time updates
                def export_progress_callback(message):
                    # Parse progress percentage if included
                    import re
                    progress_match = re.search(r"(\d+)%", message)
                    progress_value = int(progress_match.group(1)) if progress_match else None
                    
                    # Determine message type
                    is_error = any(err in message.lower() for err in ["error", "failed", "cannot"])
                    is_success = any(succ in message.lower() for succ in ["success", "complete", "saved"])
                    
                    # Update status
                    update_status(message, progress_value, is_error, is_success)
                
                # Call the enhanced exporter
                result = self.exporter.export_current_view(
                    format_type, 
                    panel_data,
                    export_progress_callback
                )
                
                # Update final status
                if "error" in result.lower():
                    update_status(result, 100, is_error=True)
                else:
                    update_status(result, 100, is_success=True)
                    
            except Exception as e:
                import traceback
                traceback.print_exc()  # Print full stack trace for debugging
                update_status(f"<p>Export failed: {str(e)}</p>", 100, is_error=True)
        
        def on_export_all(b):
            # Reset progress bar
            progress.value = 0
            progress.bar_style = 'info'
            progress.layout.visibility = 'visible'
            
            # Show initial status
            update_status("<p>Initializing export of all data...</p>")
            
            # Get current panel data (similar to above)
            active_panel = "left_panel"
            if self.current_session["comparison_active"]:
                # Determine which panel is active based on most recent analysis
                # For now we'll just default to left
                active_panel = "left_panel"
                
            panel_data = {
                "state": self.current_session[active_panel]["state"],
                "data": self.current_session[active_panel].get("results", {}).get("data"),
                "results": self.current_session[active_panel].get("results", {}),
                "temporal_data": self.current_session[active_panel].get("results", {}).get("temporal_data", []),
                "analysis_engine": self.analysis_engine  # Pass the analysis engine for recreating data
            }
            
            # Verify data availability
            if not panel_data["data"]:
                update_status("<p>No data available for export. Please run analysis first.</p>", is_error=True)
                progress.layout.visibility = 'hidden'
                return
            
            # Get selected format
            format_type = format_dropdown.value
            
            try:
                # Define status callback for real-time updates (same as above)
                def export_progress_callback(message):
                    import re
                    progress_match = re.search(r"(\d+)%", message)
                    
                    # For "all data" exports, we'll estimate progress from status messages
                    if "year" in message.lower() and "of" in message:
                        # Try to parse "year X of Y" pattern
                        year_match = re.search(r"year (\d+) of (\d+)", message.lower())
                        if year_match:
                            current = int(year_match.group(1))
                            total = int(year_match.group(2))
                            progress_value = int((current / total) * 100)
                        else:
                            progress_value = None
                    else:
                        progress_value = int(progress_match.group(1)) if progress_match else None
                    
                    is_error = any(err in message.lower() for err in ["error", "failed", "cannot"])
                    is_success = any(succ in message.lower() for succ in ["success", "complete", "saved"])
                    
                    update_status(message, progress_value, is_error, is_success)
                
                # Call the enhanced exporter
                result = self.exporter.export_all_data(
                    format_type, 
                    panel_data,
                    export_progress_callback
                )
                
                # Update final status
                if "error" in result.lower():
                    update_status(result, 100, is_error=True)
                else:
                    update_status(result, 100, is_success=True)
                    
            except Exception as e:
                update_status(f"<p>Export failed: {str(e)}</p>", 100, is_error=True)
        
        export_current_btn.on_click(on_export_current)
        export_all_btn.on_click(on_export_all)
        
        # Assemble export panel
        export_panel = widgets.VBox([
            export_header,
            widgets.HBox([
                export_current_btn,
                export_all_btn,
                format_dropdown
            ]),
            progress,
            status_display
        ], layout=Layout(width='100%', border='1px solid #ddd', padding='10px', margin='20px 0'))
        
        return export_panel
    
    def _create_cli_interface(self):
        """Create command-line interface tab"""
        # CLI header
        cli_header = widgets.HTML(
            value="""
            <h3>Command Line Interface</h3>
            <p>Advanced users can run climate analysis tasks with commands.</p>
            """
        )
        
        # Command input
        command_input = widgets.Text(
            placeholder="Enter climate analysis command",
            layout=Layout(width='80%')
        )
        
        # Command history
        command_history = widgets.Textarea(
            placeholder="Command history will appear here",
            layout=Layout(width='80%', height='300px'),
            disabled=True
        )
        
        # Execute button
        execute_button = widgets.Button(
            description="Execute",
            button_style="primary",
            layout=Layout(width='100px')
        )
        
        # Help button
        help_button = widgets.Button(
            description="Help",
            layout=Layout(width='100px')
        )
        
        # Command execution handler
        def on_execute(b):
            command = command_input.value
            if command:
                command_history.value += f"> {command}\n"
                try:
                    # Example command processing
                    if command.startswith("help"):
                        command_history.value += "Available commands:\n"
                        command_history.value += "  analyze <dataset> <parameter> <index> <startYear> <endYear>\n"
                        command_history.value += "  export <format> <dataType>\n"
                        command_history.value += "  help [command]\n"
                    elif command.startswith("analyze"):
                        command_history.value += "Starting analysis...\n"
                        command_history.value += "Analysis complete. Use 'export' to save results.\n"
                    elif command.startswith("export"):
                        command_history.value += "Exporting data...\n"
                        command_history.value += "Export task started. Files will be available in your Google Drive.\n"
                    else:
                        command_history.value += f"Unknown command: {command}\nType 'help' for available commands.\n"
                except Exception as e:
                    command_history.value += f"Error: {str(e)}\n"
                
                command_history.value += "\n"
                command_input.value = ""
        
        execute_button.on_click(on_execute)
        
        # Help button handler
        def on_help(b):
            command_history.value += "> help\n"
            command_history.value += "Available commands:\n"
            command_history.value += "  analyze <dataset> <parameter> <index> <startYear> <endYear>\n"
            command_history.value += "  export <format> <dataType>\n"
            command_history.value += "  help [command]\n\n"
        
        help_button.on_click(on_help)
        
        # Allow execution on Enter key
        def on_submit(widget):
            on_execute(None)
        
        command_input.on_submit(on_submit)
        
        # Assemble CLI interface
        cli_container = widgets.VBox([
            cli_header,
            widgets.HBox([command_input, execute_button, help_button]),
            command_history
        ])
        
        return cli_container
    
    def _create_help_interface(self):
        """Create help and documentation tab"""
        help_content = widgets.HTML(
            value="""
            <div style="height:600px; overflow-y:auto; padding:10px;">
                <h2>Climate Analysis Tool Help</h2>
                
                <h3>Overview</h3>
                <p>The Climate Analysis Tool allows you to analyze climate data using Google Earth Engine.</p>
                
                <h3>Analysis Steps</h3>
                <ol>
                    <li><strong>Area of Interest:</strong> Define the geographic region for analysis</li>
                    <li><strong>Time Range:</strong> Select the years to analyze</li>
                    <li><strong>Dataset:</strong> Choose a climate dataset (ERA5, PRISM, or DAYMET)</li>
                    <li><strong>Parameter:</strong> Select the climate parameter (Precipitation or Temperature)</li>
                    <li><strong>Index:</strong> Choose a specific climate index to analyze</li>
                </ol>
                
                <h3>Comparison Feature</h3>
                <p>Use the comparison feature to compare different datasets, time periods, or indices side by side.</p>
                
                <h3>Export Options</h3>
                <ul>
                    <li><strong>Export Current View:</strong> Export the data currently displayed on screen</li>
                    <li><strong>Export All Data:</strong> Export data for all years in the selected range</li>
                </ul>
                
                <h3>Command Line Interface</h3>
                <p>Advanced users can use the CLI tab for scripted analysis with commands like:</p>
                <pre>analyze ERA5 Temperature "Annual maximum temperature" 1980 2020</pre>
                <pre>export GeoTIFF all</pre>
                
                <h3>Datasets</h3>
                <ul>
                    <li><strong>ERA5:</strong> Global reanalysis dataset with high spatial resolution</li>
                    <li><strong>PRISM:</strong> High-resolution dataset for the contiguous United States</li>
                    <li><strong>DAYMET:</strong> Daily surface weather data over North America</li>
                </ul>
                
                <h3>Need more help?</h3>
                <p>Contact support at climate-tool-support@example.com</p>
            </div>
            """
        )
        
        # Create container with fixed height and scrolling
        help_container = widgets.VBox([
            help_content
        ], layout=widgets.Layout(
            overflow='auto',
            border='1px solid #ddd',
            padding='8px',
            width='100%',
            height='650px'
        ))
        
        return help_container
    
    def _update_panel_state(self, panel_id):
        """Update the state for a panel based on widget values"""
        widgets_dict = self.current_session[f"{panel_id}_panel"]["widgets"]
        
        # Extract values from widgets
        # This is a simplified example - you'd need to extract all relevant values
        self.current_session[f"{panel_id}_panel"]["state"] = {
            "geometry": self.geometry_manager.get_geometry(panel_id),
            "time_range": (
                widgets_dict["step2"].children[0].value,  # start year
                widgets_dict["step2"].children[1].value   # end year
            ),
            "dataset": widgets_dict["step3"].children[0].value,
            "parameter": widgets_dict["step4"].value,
            "index": widgets_dict["step5"].children[0].value
        }
    
    def _run_analysis(self, panel_id, results_container):
        """Run analysis and update results container with proper year toggling"""
        # Clear previous results
        results_container.children = [widgets.HTML(value="<p>Running analysis...</p>")]
        
        try:
            # Get state for the panel
            panel_state = self.current_session[f"{panel_id}_panel"]["state"]
            
            # Run analysis using the analysis engine
            results = self.analysis_engine.analyze(
                panel_state["geometry"],
                panel_state["time_range"][0],
                panel_state["time_range"][1],
                panel_state["dataset"],
                panel_state["parameter"],
                panel_state["index"]
            )
            
            # Store the full results in the session for later use
            self.current_session[f"{panel_id}_panel"]["results"] = results
            
            # Define callback to get image for a specific year
            def get_image_for_year(year):
                """Get image for a specific year"""
                try:
                    # Define date range for the year
                    start_date = f"{year}-01-01"
                    end_date = f"{year}-12-31"
                    
                    # Call analysis engine to calculate index for the year
                    result = self.analysis_engine._calculate_index(
                        geometry=panel_state["geometry"],
                        start_date=start_date,
                        end_date=end_date,
                        dataset=panel_state["dataset"],
                        index=panel_state["index"]
                    )
                    
                    # Return the image
                    return result.clip(panel_state["geometry"])
                except Exception as e:
                    print(f"Error getting image for year {year}: {str(e)}")
                    return None
            
            # Create visualization
            start_year, end_year = panel_state["time_range"]
            map_widget = self.visualizer.create_map(
                results["data"], 
                results["vis_params"],
                panel_state["index"],
                start_year=start_year,
                end_year=end_year,
                year_callback=get_image_for_year  # Pass the callback       
            )

            # Create temporal plot
            plot_widget = self.visualizer.create_temporal_plot(
                results["temporal_data"],
                f"Temporal Trend of {panel_state['index']}",
                results["units"]
            )
            
            # Update results container
            results_container.children = [
                widgets.HTML(value=f"<h5>Analysis Results: {panel_state['index']}</h5>"),
                map_widget,
                widgets.HTML(value="<h5>Temporal Trend</h5>"),
                plot_widget
            ]
            
        except Exception as e:
            error_message = f"<p style='color: red'>Analysis failed: {str(e)}</p>"
            results_container.children = [widgets.HTML(value=error_message)]

    def _calculate_data_for_year(self, geometry, year, dataset, parameter, index):
        """
        Calculate data for a specific year
        
        Args:
            geometry: Analysis geometry
            year: Year to calculate data for
            dataset: Dataset name
            parameter: Parameter type
            index: Index name
            
        Returns:
            Earth Engine image for the year
        """
        try:
            # Define date range for the year
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"
            
            # Call analysis engine to calculate index for the year
            result = self.analysis_engine._calculate_index(
                geometry=geometry,
                start_date=start_date,
                end_date=end_date,
                dataset=dataset,
                index=index
            )
            
            return result
        except Exception as e:
            print(f"Error calculating data for year {year}: {str(e)}")
            return None

if __name__ == "__main__":
    # Start the Climate Analysis Tool
    tool = ClimateAnalysisTool()
    tool.start()