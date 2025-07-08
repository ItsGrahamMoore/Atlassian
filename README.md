Here is a README file for the `JSMReleases.py` script:

---

# JSMReleases.py

## Overview

`JSMReleases.py` is a Python script that automates the extraction and comparison of Jira Service Management (JSM) weekly release notes from Atlassian's Confluence Cloud blog. It identifies and displays new JSM changes introduced in the latest weekly release compared to the previous week.

## Features

- Automatically creates and manages a Python virtual environment for dependencies.
- Fetches the two most recent Atlassian Cloud weekly release blog posts.
- Extracts and parses the "Jira Service Management" section from each post.
- Compares the current and previous week's entries to highlight new changes.
- Outputs new JSM changes with details, status labels, descriptions, and relevant links.

## Requirements

- Python 3.6 or higher
- Internet connection (to fetch release notes and install dependencies)

## Usage

1. **Download the script**  
   Save `JSMReleases.py` to your local machine.

2. **Run the script**  
   Open a terminal and execute:
   ```bash
   python3 JSMReleases.py
   ```
   The script will:
   - Create a virtual environment (`jsm_venv`) in the script's directory (if not already present).
   - Install required packages (`requests`, `beautifulsoup4`) in the virtual environment.
   - Fetch and compare the latest two JSM release notes.
   - Print new JSM changes to the terminal.

## How It Works

- The script sets up a virtual environment and installs dependencies automatically.
- It scrapes the Atlassian Cloud blog index for links to weekly release notes.
- It parses the "Jira Service Management" section from each of the two most recent posts.
- It compares the entries by name and lists any new changes found in the latest week.

## Output

The script prints a list of new JSM changes, including:
- Change name
- Status labels (if any)
- Description (with formatting)
- Relevant links

If no new changes are found, it will indicate so.

## Troubleshooting

- If you encounter errors related to missing dependencies, delete the `jsm_venv` directory and rerun the script.
- Ensure you have a working internet connection.
- The script is designed to work on both Windows and Unix-like systems.

## License

This script is provided as-is, without warranty or guarantee of accuracy.
