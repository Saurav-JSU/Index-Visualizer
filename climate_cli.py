"""
climate_cli.py
Command Line Interface for Climate Analysis Tool
"""

import ee
import argparse
import sys
import os
import json
from typing import List, Dict, Any, Optional

from authentication import AuthenticationManager
from data_manager import DataManager
from geometry_manager import GeometryManager
from analysis_engine import AnalysisEngine
from exporter import Exporter

class CliTool:
    """
    Command Line Interface for Climate Analysis Tool
    """
    
    def __init__(self):
        """Initialize CLI Tool"""
        # Initialize components
        self.auth_manager = AuthenticationManager()
        
        # Check if already authenticated
        self.authenticated = self._authenticate()
        
        if self.authenticated:
            self.data_manager = DataManager()
            self.analysis_engine = AnalysisEngine(self.data_manager)
            self.exporter = Exporter()
            print("Climate Analysis Tool CLI initialized successfully")
        else:
            print("Authentication failed. Run 'authenticate' command first")
    
    def _authenticate(self) -> bool:
        """
        Authenticate with Earth Engine
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Try to load saved credentials
            if self.auth_manager.load_credentials():
                # Initialize Earth Engine
                project_id = self.auth_manager.project_id
                if project_id:
                    ee.Initialize(project=project_id)
                else:
                    ee.Initialize()
                
                # Test authentication
                ee.Number(1).getInfo()
                return True
            
            return False
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            return False
    
    def parse_args(self, args: Optional[List[str]] = None) -> argparse.Namespace:
        """
        Parse command line arguments
        
        Args:
            args: Command line arguments (defaults to sys.argv)
            
        Returns:
            Parsed arguments
        """
        parser = argparse.ArgumentParser(description="Climate Analysis Tool CLI")
        
        # Create subparsers for different commands
        subparsers = parser.add_subparsers(dest="command", help="Command to execute")
        
        # Authenticate command
        auth_parser = subparsers.add_parser("authenticate", help="Authenticate with Earth Engine")
        auth_parser.add_argument("--project", help="Earth Engine project ID")
        
        # Analyze command
        analyze_parser = subparsers.add_parser("analyze", help="Run climate analysis")
        analyze_parser.add_argument("dataset", help="Dataset name (ERA5, PRISM, DAYMET)")
        analyze_parser.add_argument("parameter", help="Parameter (Precipitation, Temperature)")
        analyze_parser.add_argument("index", help="Climate index name")
        analyze_parser.add_argument("start_year", type=int, help="Start year")
        analyze_parser.add_argument("end_year", type=int, help="End year")
        analyze_parser.add_argument("--bounds", nargs=4, type=float, metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"),
                           help="Geographic bounds (min_lon min_lat max_lon max_lat)")
        analyze_parser.add_argument("--shapefile", help="Path to shapefile")
        analyze_parser.add_argument("--output", help="Path to output JSON file")
        
        # Export command
        export_parser = subparsers.add_parser("export", help="Export analysis results")
        export_parser.add_argument("format", choices=["GeoTIFF", "CSV", "NetCDF"], help="Export format")
        export_parser.add_argument("type", choices=["current", "all"], help="Export current view or all data")
        export_parser.add_argument("--input", help="Path to input JSON file with analysis results")
        
        # List command
        list_parser = subparsers.add_parser("list", help="List available options")
        list_parser.add_argument("option", choices=["datasets", "indices"], help="Option to list")
        list_parser.add_argument("--category", help="Category for indices (Precipitation, Temperature)")
        
        # Help command
        help_parser = subparsers.add_parser("help", help="Show help for a command")
        help_parser.add_argument("topic", nargs="?", help="Help topic")
        
        # Parse arguments
        return parser.parse_args(args)
    
    def run(self, args: Optional[List[str]] = None) -> int:
        """
        Run CLI with arguments
        
        Args:
            args: Command line arguments (defaults to sys.argv)
            
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        args = self.parse_args(args)
        
        if args.command == "authenticate":
            return self.cmd_authenticate(args)
        elif args.command == "analyze":
            return self.cmd_analyze(args)
        elif args.command == "export":
            return self.cmd_export(args)
        elif args.command == "list":
            return self.cmd_list(args)
        elif args.command == "help":
            return self.cmd_help(args)
        else:
            print("Error: No command specified")
            print("Run 'climate_cli.py help' for usage information")
            return 1
    
    def run_command(self, command_str: str) -> int:
        """
        Run a command string
        
        Args:
            command_str: Command string to run
            
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        args = command_str.split()
        return self.run(args)
    
    def cmd_authenticate(self, args: argparse.Namespace) -> int:
        """
        Handle authenticate command
        
        Args:
            args: Command line arguments
            
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        print("Authenticating with Earth Engine...")
        
        try:
            # Authenticate with Earth Engine
            self.auth_manager.authenticate_ee()
            
            # Initialize with project ID if provided
            project_id = args.project
            if project_id:
                print(f"Initializing with project ID: {project_id}")
                success = self.auth_manager.initialize_ee(project_id)
            else:
                print("Initializing with default project")
                success = self.auth_manager.initialize_ee()
            
            if success:
                print("Authentication successful")
                self.authenticated = True
                
                # Initialize components
                self.data_manager = DataManager()
                self.analysis_engine = AnalysisEngine(self.data_manager)
                self.exporter = Exporter()
                
                return 0
            else:
                print(f"Authentication failed: {self.auth_manager.auth_status}")
                return 1
                
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            return 1
    
    def cmd_analyze(self, args: argparse.Namespace) -> int:
        """
        Handle analyze command
        
        Args:
            args: Command line arguments
            
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        if not self.authenticated:
            print("Error: Not authenticated. Run 'authenticate' command first")
            return 1
        
        try:
            # Get geometry
            geometry = self._get_geometry(args)
            if geometry is None:
                return 1
            
            print(f"Running analysis for {args.dataset} / {args.parameter} / {args.index}...")
            
            # Run analysis
            results = self.analysis_engine.analyze(
                geometry=geometry,
                start_year=args.start_year,
                end_year=args.end_year,
                dataset=args.dataset,
                parameter=args.parameter,
                index=args.index
            )
            
            # Convert Earth Engine objects to serializable format
            serializable_results = self._make_results_serializable(results)
            
            # Save to output file if specified
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(serializable_results, f, indent=2)
                print(f"Results saved to {args.output}")
            
            # Print summary
            self._print_results_summary(serializable_results)
            
            return 0
            
        except Exception as e:
            print(f"Analysis error: {str(e)}")
            return 1
    
    def cmd_export(self, args: argparse.Namespace) -> int:
        """
        Handle export command
        
        Args:
            args: Command line arguments
            
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        if not self.authenticated:
            print("Error: Not authenticated. Run 'authenticate' command first")
            return 1
        
        try:
            # Load input file if specified
            if not args.input:
                print("Error: Input file required for export")
                return 1
            
            with open(args.input, 'r') as f:
                panel_data = json.load(f)
            
            # Export data
            if args.type == "current":
                status = self.exporter.export_current_view(args.format, panel_data)
                print(status)
            else:  # all
                status = self.exporter.export_all_data(args.format, panel_data)
                print(status)
            
            return 0
            
        except Exception as e:
            print(f"Export error: {str(e)}")
            return 1
    
    def cmd_list(self, args: argparse.Namespace) -> int:
        """
        Handle list command
        
        Args:
            args: Command line arguments
            
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        if not self.authenticated and args.option != "help":
            print("Error: Not authenticated. Run 'authenticate' command first")
            return 1
        
        try:
            if args.option == "datasets":
                datasets = self.data_manager.list_datasets()
                print("Available datasets:")
                for dataset in datasets:
                    info = self.data_manager.get_dataset_info(dataset)
                    print(f"  {dataset}: {info['display_name']} - {info['description']}")
            
            elif args.option == "indices":
                category = args.category
                indices = self.analysis_engine.list_indices(category)
                
                if category:
                    print(f"Available {category} indices:")
                else:
                    print("Available indices:")
                    
                for index in indices:
                    info = self.analysis_engine.get_index_info(index)
                    print(f"  {index}: {info['description']} ({info['units']})")
            
            return 0
            
        except Exception as e:
            print(f"List error: {str(e)}")
            return 1
    
    def cmd_help(self, args: argparse.Namespace) -> int:
        """
        Handle help command
        
        Args:
            args: Command line arguments
            
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        if args.topic:
            self._show_topic_help(args.topic)
        else:
            self._show_general_help()
        
        return 0
    
    def _get_geometry(self, args: argparse.Namespace) -> Optional[ee.Geometry]:
        """
        Get geometry from arguments
        
        Args:
            args: Command line arguments
            
        Returns:
            Earth Engine geometry or None if error
        """
        geometry_manager = GeometryManager()
        
        if args.bounds:
            # Use bounds
            min_lon, min_lat, max_lon, max_lat = args.bounds
            try:
                geometry_manager.set_bounds("cli", min_lon, min_lat, max_lon, max_lat)
                return geometry_manager.get_geometry("cli")
            except ValueError as e:
                print(f"Error with bounds: {str(e)}")
                return None
                
        elif args.shapefile:
            # Use shapefile
            try:
                geometry_manager.process_shapefile("cli", args.shapefile)
                return geometry_manager.get_geometry("cli")
            except ValueError as e:
                print(f"Error with shapefile: {str(e)}")
                return None
                
        else:
            # Default to global bounds
            try:
                geometry_manager.set_bounds("cli", -180, -60, 180, 80)
                print("Using default global bounds (-180, -60, 180, 80)")
                return geometry_manager.get_geometry("cli")
            except ValueError as e:
                print(f"Error with default bounds: {str(e)}")
                return None
    
    def _make_results_serializable(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Earth Engine objects to serializable format
        
        Args:
            results: Analysis results
            
        Returns:
            Serializable results
        """
        # Create copy of results
        serializable = dict(results)
        
        # Remove Earth Engine objects
        if 'data' in serializable:
            serializable['data'] = 'ee.Image (not serializable)'
        
        return serializable
    
    def _print_results_summary(self, results: Dict[str, Any]) -> None:
        """
        Print summary of analysis results
        
        Args:
            results: Analysis results
        """
        print("\nAnalysis Results Summary:")
        print(f"  Dataset: {results.get('dataset', 'N/A')}")
        print(f"  Parameter: {results.get('parameter', 'N/A')}")
        print(f"  Index: {results.get('index', 'N/A')}")
        print(f"  Time Range: {results.get('time_range', 'N/A')}")
        print(f"  Units: {results.get('units', 'N/A')}")
        
        # Print temporal data if available
        temporal_data = results.get('temporal_data', [])
        if temporal_data:
            values = [d['value'] for d in temporal_data]
            print(f"  Data Points: {len(values)}")
            print(f"  Mean Value: {sum(values) / len(values):.2f} {results.get('units', '')}")
            print(f"  Min Value: {min(values):.2f} {results.get('units', '')}")
            print(f"  Max Value: {max(values):.2f} {results.get('units', '')}")
        else:
            print("  No temporal data available")
    
    def _show_topic_help(self, topic: str) -> None:
        """
        Show help for a specific topic
        
        Args:
            topic: Help topic
        """
        if topic == "authenticate":
            print("authenticate: Authenticate with Earth Engine")
            print("Usage: climate_cli.py authenticate [--project PROJECT_ID]")
            print("\nOptions:")
            print("  --project PROJECT_ID  Earth Engine project ID")
            
        elif topic == "analyze":
            print("analyze: Run climate analysis")
            print("Usage: climate_cli.py analyze DATASET PARAMETER INDEX START_YEAR END_YEAR [--bounds MIN_LON MIN_LAT MAX_LON MAX_LAT] [--shapefile SHAPEFILE] [--output OUTPUT]")
            print("\nArguments:")
            print("  DATASET     Dataset name (ERA5, PRISM, DAYMET)")
            print("  PARAMETER   Parameter (Precipitation, Temperature)")
            print("  INDEX       Climate index name")
            print("  START_YEAR  Start year")
            print("  END_YEAR    End year")
            print("\nOptions:")
            print("  --bounds MIN_LON MIN_LAT MAX_LON MAX_LAT  Geographic bounds")
            print("  --shapefile SHAPEFILE                     Path to shapefile")
            print("  --output OUTPUT                           Path to output JSON file")
            
        elif topic == "export":
            print("export: Export analysis results")
            print("Usage: climate_cli.py export FORMAT TYPE --input INPUT")
            print("\nArguments:")
            print("  FORMAT      Export format (GeoTIFF, CSV, NetCDF)")
            print("  TYPE        Export type (current, all)")
            print("\nOptions:")
            print("  --input INPUT  Path to input JSON file with analysis results")
            
        elif topic == "list":
            print("list: List available options")
            print("Usage: climate_cli.py list OPTION [--category CATEGORY]")
            print("\nArguments:")
            print("  OPTION      Option to list (datasets, indices)")
            print("\nOptions:")
            print("  --category CATEGORY  Category for indices (Precipitation, Temperature)")
            
        else:
            print(f"No help available for topic: {topic}")
            print("Run 'climate_cli.py help' for general help")
    
    def _show_general_help(self) -> None:
        """Show general help information"""
        print("Climate Analysis Tool CLI")
        print("\nUsage: climate_cli.py COMMAND [ARGS...]")
        print("\nCommands:")
        print("  authenticate  Authenticate with Earth Engine")
        print("  analyze       Run climate analysis")
        print("  export        Export analysis results")
        print("  list          List available options")
        print("  help          Show help for a command")
        print("\nRun 'climate_cli.py help COMMAND' for help on a specific command")

if __name__ == "__main__":
    # Create CLI tool and run with command line arguments
    cli = CliTool()
    sys.exit(cli.run())