# Climate Analysis Tool (Index-Visualizer)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive Python-based tool for analyzing climate data using Google Earth Engine. This tool enables users to perform sophisticated analyses of precipitation and temperature indices across various regions and time periods through both a graphical user interface (GUI) and a command-line interface (CLI).

## Features

- **Interactive Mapping**: Visualize climate indices on an interactive map
- **Multiple Data Sources**: Support for ERA5, PRISM, and DAYMET climate datasets
- **Various Climate Indices**: Analyze temperature and precipitation patterns:
  - Temperature indices: maximum/minimum temperature, frost days, summer days
  - Precipitation indices: annual total, maximum 1-day precipitation, wet/dry days count
- **Flexible Area Selection**: Draw on map, use shapefiles, or enter geographic bounds
- **Temporal Analysis**: Study climate patterns across different time periods
- **Side-by-Side Comparison**: Compare different datasets, time periods, or indices
- **Export Options**: Save results as GeoTIFF, CSV, or NetCDF formats
- **Command-Line Interface**: Automate analyses using bash scripts
- **Extensibility**: Add custom datasets and climate indices

## Prerequisites

- Google Earth Engine account ([Sign up here](https://signup.earthengine.google.com/))
- Python 3.9 or higher
- Internet connection
- 4GB RAM (8GB recommended)

## Installation

### Option 1: Using pip

1. Clone the repository:
```bash
git clone https://github.com/Saurav-JSU/Index-Visualizer.git
cd Index-Visualizer
```

2. Create and activate a virtual environment:
```bash
python -m venv climate-venv
# On Windows:
climate-venv\Scripts\activate
# On macOS/Linux:
source climate-venv/bin/activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

### Option 2: Using Conda

1. Clone the repository:
```bash
git clone https://github.com/Saurav-JSU/Index-Visualizer.git
cd Index-Visualizer
```

2. Create and activate the conda environment:
```bash
conda env create -f environment.yml
conda activate climate-analysis
```

## Getting Started

### VS Code Interface

1. Ensure your environment is activated (pip or conda).

2. Open the project in VS Code:
```bash
code .
```

3. Open and run `main.ipynb` in VS Code.

### Command-Line Interface

The tool provides a command-line interface for advanced users and automation:

1. Authenticate with Earth Engine:
```bash
python climate_cli.py authenticate
```

2. Run an analysis:
```bash
python climate_cli.py analyze ERA5 Temperature "Annual maximum temperature" 2010 2020 --bounds -120 30 -100 45 --output results.json
```

3. Export results:
```bash
python climate_cli.py export GeoTIFF all --input results.json
```

4. List available options:
```bash
python climate_cli.py list datasets
python climate_cli.py list indices --category Temperature
```

5. Get help information:
```bash
python climate_cli.py help
python climate_cli.py help analyze
```

## Project Structure

```
Index-Visualizer/
│
├── analysis_engine.py        # Core engine for climate data analysis
├── authentication.py         # Handles Earth Engine authentication
├── climate_cli.py            # Command-line interface
├── climate_tool.py           # Main application with GUI
├── data_manager.py           # Manages climate datasets
├── exporter.py               # Handles data export
├── geometry_manager.py       # Handles geographic operations
├── visualizer.py             # Handles visualization
├── main.ipynb                # Main Jupyter notebook entry point
├── environment.yml           # Conda environment definition
├── requirements.txt          # Python package requirements
└── .gitignore                # Git ignore file
```

## Example Usage

### Basic Analysis Workflow

1. Authenticate with Earth Engine
2. Define area of interest (draw on map, upload shapefile, or input coordinates)
3. Select time range (start and end years)
4. Choose dataset, parameter, and index
5. Run analysis and view results
6. Export results in desired format


### Advanced: Comparison Mode

Compare different datasets, time periods, or indices side by side:

1. Complete a basic analysis
2. Enable comparison mode
3. Configure second analysis with different parameters
4. Compare results visually and statistically


## Dependencies

The Climate Analysis Tool relies on the following key packages:

- **earthengine-api**: For Google Earth Engine access
- **geemap**: For Earth Engine mapping
- **ipywidgets**: For interactive widgets
- **anywidgets**: For custom interactive widgets
- **rasterio**, **xarray**, **geopandas**: For geospatial data handling
- **plotly**: For interactive plots
- **jupyter**: For notebook interface

See `requirements.txt` or `environment.yml` for complete list with versions.

## Troubleshooting

### Common Issues

- **Installation Problems**: Use conda instead of pip for geospatial packages
- **Authentication Errors**: Ensure you have a valid Earth Engine account
- **No Data Available**: Check if dataset covers your selected time range and area
- **Performance Issues**: Reduce area of interest or time range for large analyses
- **Export Failures**: For large exports, the tool falls back to Google Drive automatically

## Advanced Topics

### Adding Custom Datasets

```python
from data_manager import DataManager

data_manager = DataManager()
data_manager.add_custom_dataset("CustomDataset", {
    "id": "CUSTOM/DATASET/ID",
    "precip_key": "precipitation",
    "tmax_key": "tmax",
    "tmin_key": "tmin",
    "precip_conversion": 1.0,
    "temp_conversion": 0.0,
    "start_year": 2000,
    "end_year": 2020,
    "display_name": "Custom Dataset",
    "description": "Custom dataset description",
    "region_coverage": "Global",
    "spatial_resolution": "1km"
})
```

### Creating Custom Climate Indices

```python
from analysis_engine import AnalysisEngine
from data_manager import DataManager

data_manager = DataManager()
analysis_engine = AnalysisEngine(data_manager)

analysis_engine.add_custom_index("Custom Precipitation Index", {
    "category": "Precipitation",
    "description": "Custom precipitation index description",
    "units": "mm/year",
    "requires_daily": True,
    "min_vis_value": 0,
    "max_vis_value": 2000,
    "palette": ["#ffffff", "#0000ff"]
})
```

### Programmatic Usage

```python
import ee
from analysis_engine import AnalysisEngine
from data_manager import DataManager
from geometry_manager import GeometryManager

# Initialize Earth Engine
ee.Initialize()

# Create components
data_manager = DataManager()
geometry_manager = GeometryManager()
analysis_engine = AnalysisEngine(data_manager)

# Set geometry (example: Western US)
geometry_manager.set_bounds("region", -125, 30, -100, 45)
geometry = geometry_manager.get_geometry("region")

# Run analysis
results = analysis_engine.analyze(
    geometry=geometry,
    start_year=2010,
    end_year=2020,
    dataset="ERA5",
    parameter="Temperature",
    index="Annual maximum temperature"
)

# Access results
data = results["data"]  # Earth Engine image
temporal_data = results["temporal_data"]  # Temporal trend data
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- Google Earth Engine for providing the API and data
- Climate dataset providers: ERA5, PRISM, and DAYMET
- Contributors and maintainers of geospatial Python packages

## Contact

Saurav - [GitHub Profile](https://github.com/Saurav-JSU)

Project Link: [https://github.com/Saurav-JSU/Index-Visualizer](https://github.com/Saurav-JSU/Index-Visualizer)