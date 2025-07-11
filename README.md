# Philippine Election Data Dashboard

A scalable, dynamic election data dashboard for visualizing Philippine election results.
Built with Python, Streamlit, and Plotly.

## Features

-   📊 **Dynamic Election Awareness**: Automatically detects election type (national, local, barangay) based on `config.json`.
-   🔄 **Modular & Scalable**: Designed to handle different data schemas per election type.
-   📁 **Data Handling**: Uses CSV files for election results input. Sample data provided.
-   📈 **Visualization**: Interactive charts (bar, pie) using Plotly showing top candidates and regional summaries.
-   🎨 **UI/UX**: Clean interface with Streamlit components. Filters for election level, position, and location.
-   🔄 **Auto-Update Simulation**: Data is cached. A "Force Refresh Data" button allows manual reloading. Streamlit's reactivity handles UI updates on widget changes.
-   🧠 **Optional AI Integration**: Includes a placeholder for summarizing election highlights using Gemini API (can be enabled by setting up the API key).

## Project Structure
```ph_election_dashboard/
├── app.py                     # Main Streamlit application
├── config.json                # Configuration for election type and data files
├── data/
│   ├── national_election_results.csv
│   ├── local_election_results.csv
│   ├── barangay_election_results.csv
│   └── README_DATA.md         # Description of data formats
├── gemini_integration.py      # AI summary function (with placeholder)
├── requirements.txt           # Python dependencies
└── README.md                  # Main project README

```

## Setup and Installation
1.  **Clone the repository (or create the files as listed above):**
    ```bash
    # If it were a git repo:
    # git clone <repository_url>
    # cd ph_election_dashboard
    ```
    For now, create the `ph_election_dashboard` directory and populate it with the files provided.

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    If you plan to use the actual Gemini API for summaries, also run:
    `pip install google-generativeai`
    And ensure your `GEMINI_API_KEY` environment variable is set.

4.  **Configure the Election Type (Optional):**
    Edit `config.json` to set the `current_election_type` to `"national"`, `"local"`, or `"barangay"` to change the default view on startup. You can also change the election type via the sidebar in the app.

5.  **Prepare Data:**
    Place your election data CSV files in the `data/` directory. Ensure they follow the format described in `data/README_DATA.md`. Sample files are provided.

## Running the Application

1.  **Navigate to the project directory:**
    ```bash
    cd ph_election_dashboard
    ```

2.  **Run the Streamlit app:**
    ```bash
    streamlit run app.py
    ```
    This will open the dashboard in your web browser.

## How it Works

-   **`config.json`**: Defines the current election type and paths to data files.
-   **`app.py`**: The main Streamlit application. It loads data based on the configuration, provides filters, and displays visualizations.
-   **`data/`**: Contains CSV files with election results. The schema varies by election type.
-   **Visualizations**: Plotly is used to generate interactive bar charts for top candidates and pie charts for party distributions. Regional summaries are also provided.
-   **Filtering**: Users can filter data by position and geographic levels (region, province, municipality, barangay) depending on the election type.
-   **AI Summaries**: If enabled and configured, `gemini_integration.py` can call the Gemini API to provide textual summaries of the election data. A placeholder provides basic summaries if the API is not active.

## Scalability and Modularity

-   **Data Schema**: The application adapts its UI and data processing based on the `current_election_type` in `config.json`. Different columns and filter levels are handled dynamically.
-   **Code Structure**: Functions are used to separate logic for data loading, filtering, and chart generation, making it easier to extend or modify.
-   **Low Resource Usage**: Streamlit and Pandas are generally efficient. `@st.cache_data` is used to cache data loading operations, reducing redundant processing and improving performance on machines with limited RAM. Large datasets will still require adequate memory.

## To-Do / Potential Enhancements

-   [ ] Implement live file watching for automatic data updates without manual refresh.
-   [ ] Add map-based visualizations (e.g., choropleth maps for regional vote density) if geographical data (Shapefiles, GeoJSON) is available.
-   [ ] More sophisticated AI insights (e.g., trend analysis, voter turnout estimation if data allows).
-   [ ] User authentication and role-based access for data management.
-   [ ] Database integration for more robust data storage and querying instead of CSV files for larger scale deployments.
