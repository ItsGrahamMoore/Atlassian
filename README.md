# Jira Service Management Weekly Release Notes Extractor

This script fetches, compares, and displays the latest Jira Service Management (JSM) weekly release notes from Atlassian's Confluence Cloud blog. It highlights new JSM changes introduced in the most recent week compared to the previous week, and presents them in a clean, styled HTML page.

---

## Features

- **Automatic fetching** of the two most recent Atlassian Cloud weekly release notes.
- **Extraction** of Jira Service Management (JSM) section entries.
- **Comparison** to highlight only new JSM entries for the current week.
- **Beautiful HTML output** with status lozenges and formatting.
- **Progress bar** for user feedback.
- **Automatic browser launch** of the results.
- **Optional macOS Terminal auto-close** after completion.

---

## Requirements

- Python 3.6+
- The following Python packages:
  - `requests`
  - `beautifulsoup4`
  - `lxml` (recommended for best parsing performance)
- Internet connection
- A modern web browser

Install dependencies with:

```bash
pip install requests beautifulsoup4 lxml
```

---

## Usage

1. **Save the script** to a file, e.g. `jsm_release_notes.py`.
2. **Run the script**:

   ```bash
   python jsm_release_notes.py
   ```

3. **Wait for the progress bar** to complete. The script will:
   - Fetch the two latest Atlassian Cloud weekly release notes.
   - Extract and compare JSM entries.
   - Open a browser window/tab with the new JSM changes for the current week.

4. **On macOS**, the Terminal window will auto-close after completion.

---

## How It Works

- The script scrapes the Atlassian Confluence Cloud blog for weekly release note URLs.
- It parses the HTML to find the "Jira Service Management" section and its entries.
- It compares the current and previous week's entries by name (case-insensitive).
- Only new entries (not present last week) are shown.
- The results are formatted as a styled HTML page and opened in your browser.

---

## Troubleshooting

- **Not enough weekly release URLs found**: The script may fail if Atlassian changes their blog structure.
- **No entries found for this week**: There may be no JSM updates, or the blog format has changed.
- **Browser does not open**: Ensure you have a default browser set up.
- **macOS Terminal does not close**: This feature uses AppleScript and only works on macOS.

---

## Customization

- To change the product or section (e.g., from JSM to Jira Software), modify the `get_jsm_section_panels` function.
- To adjust the number of weeks compared, change the slicing in `get_weekly_release_urls`.

---

## License

This script is provided as-is, without warranty or guarantee of accuracy. Use at your own risk.
