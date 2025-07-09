Here’s a README file for your script:

---

# JSM Weekly Release Notes Extractor

This script fetches and compares the latest two Atlassian Cloud "Jira Service Management" (JSM) weekly release notes, then generates a user-friendly HTML report highlighting new changes for the current week.

## Features

- **Automatic virtual environment management:**  
  The script creates and manages its own Python virtual environment (`jsm_venv`) in the script directory.
- **Automatic dependency installation:**  
  Installs `requests` and `beautifulsoup4` if not already present.
- **No manual setup required:**  
  Just run the script!
- **HTML report:**  
  Opens a styled HTML page in your browser showing new JSM changes for the current week.

## Requirements

- Python 3.7 or newer
- Internet connection

## Usage

1. **Download the script** (e.g., `jsm_release_notes.py`).
2. **Open a terminal** and navigate to the script’s directory.
3. **Run the script:**

   ```sh
   python3 jsm_release_notes.py
   ```

   - On first run, the script will create a virtual environment and install dependencies.
   - On subsequent runs, it will reuse the environment.

4. **View the results:**  
   When the script finishes, your default web browser will open a new HTML page with the latest JSM changes.

## How it Works

- The script:
  1. Creates a virtual environment (`jsm_venv`) if it doesn’t exist.
  2. Installs required Python packages (`requests`, `beautifulsoup4`).
  3. Downloads and parses the two most recent Atlassian Cloud change blog posts.
  4. Extracts the "Jira Service Management" section from each.
  5. Compares the entries and highlights new items for the current week.
  6. Generates and opens an HTML report.

## Troubleshooting

- **If you see errors about missing Python or pip:**  
  Make sure Python 3.7+ is installed and available in your PATH.
- **If you see SSL or Tkinter warnings:**  
  These are usually safe to ignore and do not affect the script’s output.
- **If the browser does not open:**  
  Check your system’s default browser settings.

## Cleaning Up

To remove the virtual environment and start fresh, simply delete the `jsm_venv` folder in the script’s directory.

## License

MIT License
