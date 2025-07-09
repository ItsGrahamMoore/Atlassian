#!/usr/bin/env python3

import warnings
warnings.filterwarnings("ignore", category=Warning)

import requests
from bs4 import BeautifulSoup
import datetime
import re
import tempfile
import webbrowser
import html
import sys
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import urllib3
import time

urllib3.disable_warnings()

BASE_URL = "https://confluence.atlassian.com"
BLOG_URL = f"{BASE_URL}/cloud/blog"
REQUEST_TIMEOUT = 10

def update_progress(progress, total):
    bar_length = 40
    filled_length = int(round(bar_length * progress / float(total)))
    percents = round(100.0 * progress / float(total), 1)
    bar = '█' * filled_length + '░' * (bar_length - filled_length)
    sys.stdout.write(f'\r[{bar}] {percents}% complete')
    sys.stdout.flush()
    if progress == total:
        sys.stdout.write('\n')

def safe_request(url, timeout=REQUEST_TIMEOUT):
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException:
        return None

def get_weekly_release_urls():
    update_progress(1, 10)
    resp = safe_request(BLOG_URL)
    if not resp:
        return []
    
    soup = BeautifulSoup(resp.text, "html.parser")
    pattern = re.compile(r'atlassian-cloud-changes-[a-z]+-\d+-to-[a-z]+-\d+-\d{4}$')
    links = []
    seen = set()
    
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if pattern.search(href):
            if href.startswith("/"):
                href = f"{BASE_URL}{href}"
            if href not in seen:
                links.append(href)
                seen.add(href)
    
    def extract_date(url):
        match = re.search(r'-to-([a-z]+)-(\d+)-(\d{4})$', url)
        if not match:
            return datetime.date(1970, 1, 1)
        
        month_str, day, year = match.groups()
        try:
            months = {
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
            }
            month = months.get(month_str[:3].lower(), 1)
            return datetime.date(int(year), month, int(day))
        except (ValueError, KeyError):
            return datetime.date(1970, 1, 1)
    
    links.sort(key=extract_date, reverse=True)
    update_progress(2, 10)
    return links[:2] if len(links) >= 2 else links

@lru_cache(maxsize=32)
def get_jsm_section_panels(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    headers = soup.select('h1, h2')
    header = next((h for h in headers if 'jira service management' in h.get_text(strip=True).lower()), None)
    
    if not header:
        return []
    
    panels = []
    for sib in header.find_all_next():
        if sib.name in ['h1', 'h2'] and sib is not header:
            break
        if sib.name == 'div' and 'panel-block' in sib.get('class', []):
            panels.append(sib)
    
    return panels

def extract_text_with_formatting(element):
    result = []
    
    for content in element.contents:
        if getattr(content, 'name', None) == 'a':
            href = content.get('href', '')
            if href.startswith('/'):
                href = f"{BASE_URL}{href}"
            result.append(f'<a href="{html.escape(href)}" target="_blank" rel="noopener">{html.escape(content.get_text())}</a>')
        elif getattr(content, 'name', None) in ('strong', 'b'):
            result.append(f"<b>{html.escape(content.get_text())}</b>")
        elif getattr(content, 'name', None):
            result.append(extract_text_with_formatting(content))
        else:
            result.append(html.escape(str(content)))
    
    return "".join(result)

def convert_inline_numbered_list(text):
    matches = list(re.finditer(r'(\d+)\.\s*([^\d]+?)(?=(?:\d+\.|$))', text))
    if len(matches) >= 2:
        items = [m.group(2).strip() for m in matches]
        li_items = "".join(f"<li>{html.escape(item)}</li>" for item in items)
        return f"<ol>{li_items}</ol>"
    return None

def extract_panel_info(panel):
    h4 = panel.find('h4')
    name = h4.get_text(strip=True) if h4 else ""
    labels = [span.get_text(strip=True) for span in panel.find_all('span', class_='status-macro')]
    content_div = panel.find('div', class_='panel-block-content')
    description_parts = []
    
    if content_div:
        for child in content_div.children:
            tag_name = getattr(child, 'name', None)
            
            if tag_name == 'p':
                text = child.get_text(separator=" ", strip=True)
                ol_html = convert_inline_numbered_list(text)
                if ol_html:
                    description_parts.append(ol_html)
                else:
                    description_parts.append(f"<p>{extract_text_with_formatting(child)}</p>")
            elif tag_name in ('ol', 'ul'):
                list_type = tag_name
                list_items = "".join(f"<li>{extract_text_with_formatting(li)}</li>" 
                                    for li in child.find_all('li', recursive=False))
                description_parts.append(f"<{list_type}>{list_items}</{list_type}>")
    
    return {
        "name": name,
        "description_html": "".join(description_parts),
        "status_labels": ", ".join(labels)
    }

def fetch_week_entries(url, progress_value):
    resp = safe_request(url)
    if not resp:
        return []
    
    panels = get_jsm_section_panels(resp.text)
    if not panels:
        return []
    
    entries = []
    for panel in panels:
        try:
            entry = extract_panel_info(panel)
            if entry["name"]:
                entries.append(entry)
        except Exception:
            pass
    
    update_progress(progress_value, 10)
    return entries

def normalize_name(name):
    return ' '.join(name.lower().strip().split())

def write_and_open_html(new_entries, this_week_url, last_week_url):
    css = """
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: #F4F5F7;
            color: #172B4D;
            margin: 0;
            padding: 0;
        }
        .container {
            max-width: 900px;
            margin: 40px auto;
            padding: 0 24px 24px 24px;
        }
        h1 {
            font-size: 2rem;
            font-weight: 500;
            color: #253858;
            margin-top: 40px;
            margin-bottom: 0.5em;
        }
        h2 {
            font-size: 1.25rem;
            font-weight: 500;
            color: #172B4D;
            margin-top: 0;
            margin-bottom: 0.5em;
        }
        .panel {
            background: #fff;
            border: 1px solid #DFE1E6;
            border-radius: 8px;
            box-shadow: 0 1px 4px rgba(9,30,66,0.08);
            padding: 24px 32px 20px 32px;
            margin-bottom: 32px;
        }
        .status {
            margin-bottom: 1em;
        }
        .lozenge {
            display: inline-block;
            padding: 2px 12px;
            border-radius: 16px;
            font-size: 12px;
            font-weight: 500;
            line-height: 1.5;
            margin-right: 8px;
            margin-bottom: 2px;
            vertical-align: middle;
            border: none;
            color: #fff;
        }
        .lozenge.coming-soon { background: #6554C0; }
        .lozenge.rolling-out { background: #0052CC; }
        .lozenge.launched { background: #36B37E; }
        .lozenge.in-progress { background: #FFAB00; color: #172B4D; }
        .lozenge.deprecated, .lozenge.removed { background: #FF5630; }
        .lozenge.beta, .lozenge.experimental { background: #6554C0; }
        .lozenge.new-this-week { background: #36B37E; }
        .url {
            font-size: 0.95em;
            color: #6B778C;
            margin-bottom: 0.5em;
        }
        a {
            color: #0052CC;
            text-decoration: none;
            border-bottom: 1px dotted #0052CC;
            transition: border-bottom 0.2s;
        }
        a:hover {
            border-bottom: 1px solid #0052CC;
        }
        ul, ol {
            margin-top: 0.5em;
            margin-left: 2em;
            margin-bottom: 1em;
        }
        li {
            margin-bottom: 0.5em;
            line-height: 1.6;
        }
        p {
            margin-top: 0.5em;
            margin-bottom: 0.5em;
            line-height: 1.7;
        }
        hr {
            border: none;
            border-top: 1px solid #DFE1E6;
            margin: 2em 0;
        }
    """
    
    status_map = {
        "coming soon": "coming-soon",
        "rolling out": "rolling-out",
        "launched": "launched",
        "in progress": "in-progress",
        "deprecated": "deprecated",
        "removed": "removed",
        "beta": "beta",
        "experimental": "experimental",
        "new this week": "new-this-week",
    }
    
    def confluence_lozenge(text):
        text_lower = text.lower()
        css_class = next((val for key, val in status_map.items() if key in text_lower), "")
        return f'<span class="lozenge {css_class}">{html.escape(text)}</span>'
    
    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        '<meta charset="utf-8">',
        "<title>New JSM Weekly Release Notes</title>",
        f"<style>{css}</style>",
        "</head>",
        "<body>",
        '<div class="container">',
        "<h1>New Jira Service Management Changes</h1>",
        f'<div class="url">Current week: <a href="{this_week_url}" target="_blank" rel="noopener">{this_week_url}</a></div>',
        f'<div class="url">Last week: <a href="{last_week_url}" target="_blank" rel="noopener">{last_week_url}</a></div>',
        "<hr>"
    ]
    
    if new_entries:
        for entry in new_entries:
            panel_parts = [
                '<div class="panel">',
                f"<h2>{html.escape(entry['name'])}</h2>"
            ]
            
            if entry['status_labels']:
                lozenges = " ".join(confluence_lozenge(label) for label in entry["status_labels"].split(","))
                panel_parts.append(f'<div class="status">{lozenges}</div>')
            
            if entry['description_html']:
                panel_parts.append(entry['description_html'])
            
            panel_parts.append("</div>")
            html_parts.append("".join(panel_parts))
    else:
        html_parts.append("<p>No new JSM entries this week.</p>")
    
    html_parts.extend([
        "</div>",
        "<script>",
        "document.querySelectorAll('a').forEach(function(link) {",
        "  link.setAttribute('target', '_blank');",
        "  link.setAttribute('rel', 'noopener');",
        "});",
        "</script>",
        "</body>",
        "</html>"
    ])
    
    html_content = "\n".join(html_parts)
    
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html') as f:
        f.write(html_content)
        temp_html_path = f.name
    
    update_progress(9, 10)
    webbrowser.open(f"file://{temp_html_path}")
    update_progress(10, 10)

def quit_terminal_app():
    if sys.platform == 'darwin':  # macOS
        print("\nTask completed successfully. Closing Terminal...")
        sys.stdout.flush()
        time.sleep(1)  # Give time for the browser to open

        # Use AppleScript to detach the script and then quit the application
        applescript = '''
        tell application "Terminal"
            set frontWindow to front window
            set currentTab to selected tab of frontWindow
            
            # Detach the process by running 'disown' in the shell
            tell currentTab
                delay 0.1 -- Give the shell a moment to become ready
                do script "disown" in it
            end tell
            
            # Now quit the application
            quit
        end tell
        '''
        subprocess.Popen(['osascript', '-e', applescript])

def main():
    try:
        update_progress(0, 10)

        urls = get_weekly_release_urls()
        if len(urls) < 2:
            print("\nError: Could not find enough weekly release URLs.")
            quit_terminal_app()
            return 1

        this_week_url, last_week_url = urls[0], urls[1]

        with ThreadPoolExecutor(max_workers=2) as executor:
            this_week_future = executor.submit(fetch_week_entries, this_week_url, 4)
            last_week_future = executor.submit(fetch_week_entries, last_week_url, 6)

            this_week_entries = this_week_future.result()
            last_week_entries = last_week_future.result()

        if not this_week_entries:
            print("\nError: No entries found for this week.")
            quit_terminal_app()
            return 1

        last_week_names = {normalize_name(e['name']) for e in last_week_entries}
        new_entries = [entry for entry in this_week_entries
                      if normalize_name(entry['name']) not in last_week_names]

        update_progress(8, 10)
        write_and_open_html(new_entries, this_week_url, last_week_url)

        # Call quit_terminal_app after successful completion
        quit_terminal_app()
        return 0

    except Exception as e:
        print(f"\nError: {str(e)}")
        quit_terminal_app()
        return 1

if __name__ == "__main__":
    sys.exit(main())
