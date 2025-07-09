#!/usr/bin/env python3

import os
import sys
import subprocess
import venv
import platform
import tempfile

VENV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jsm_venv")

def create_venv():
    if not os.path.exists(VENV_DIR):
        print(f"Creating virtual environment at {VENV_DIR}...")
        venv.create(VENV_DIR, with_pip=True)
        return True
    return False

def get_venv_python():
    if platform.system() == 'Windows':
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    return os.path.join(VENV_DIR, "bin", "python")

def get_venv_pip():
    if platform.system() == 'Windows':
        return os.path.join(VENV_DIR, "Scripts", "pip.exe")
    return os.path.join(VENV_DIR, "bin", "pip")

def install_dependencies():
    pip_path = get_venv_pip()
    print("Installing required packages...")
    subprocess.check_call([pip_path, "install", "-q", "requests", "beautifulsoup4"])

def run_script():
    python_path = get_venv_python()
    script_content = '''
import requests
from bs4 import BeautifulSoup
import datetime
import re
import platform
import signal
import time
import traceback
import tempfile
import webbrowser
import html

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")

if platform.system() != 'Windows':
    signal.signal(signal.SIGALRM, timeout_handler)

def safe_request(url, timeout=5):
    print(f"Requesting {url}...")
    if platform.system() != 'Windows':
        signal.alarm(timeout + 2)
    try:
        start_time = time.time()
        response = requests.get(url, timeout=timeout)
        print(f"Request completed in {time.time() - start_time:.2f} seconds")
        return response
    except (requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
        print(f"Error: {e}")
        return None
    finally:
        if platform.system() != 'Windows':
            signal.alarm(0)

def get_weekly_release_urls():
    print("Fetching blog index...")
    resp = safe_request("https://confluence.atlassian.com/cloud/blog")
    if not resp:
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    links = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.search(r'atlassian-cloud-changes-[a-z]{3,9}-\\d{1,2}-to-[a-z]{3,9}-\\d{1,2}-\\d{4}$', href):
            if href.startswith("/"):
                href = "https://confluence.atlassian.com" + href
            if href not in seen:
                links.append(href)
                seen.add(href)
    def extract_date(url):
        m = re.search(r'-to-([a-z]{3,9})-(\\d{1,2})-(\\d{4})$', url)
        if m:
            month_str, day, year = m.groups()
            try:
                month = datetime.datetime.strptime(month_str[:3], "%b").month
            except ValueError:
                return datetime.date(1970,1,1)
            return datetime.date(int(year), month, int(day))
        return datetime.date(1970,1,1)
    links = sorted(links, key=extract_date, reverse=True)
    return links[:2] if len(links) >= 2 else links

def get_jsm_section_panels(soup):
    header = soup.find(lambda tag: tag.name in ['h1', 'h2'] and 'jira service management' in tag.get_text(strip=True).lower())
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
    result = ""
    for content in element.contents:
        if getattr(content, 'name', None) == 'a':
            href = content.get('href', '')
            if href.startswith('/'):
                href = "https://confluence.atlassian.com" + href
            result += f'<a href="{html.escape(href)}" target="_blank" rel="noopener">{html.escape(content.get_text())}</a>'
        elif getattr(content, 'name', None) in ('strong', 'b'):
            result += f"<b>{html.escape(content.get_text())}</b>"
        elif getattr(content, 'name', None):
            result += extract_text_with_formatting(content)
        else:
            result += html.escape(str(content))
    return result

def convert_inline_numbered_list(text):
    # Matches: 1. Something 2. Something else 3. Another thing
    matches = list(re.finditer(r'(\\d+)\\.\\s*([^\\d]+?)(?=(?:\\d+\\.|$))', text))
    if len(matches) >= 2:
        items = [m.group(2).strip() for m in matches]
        ol = "<ol>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ol>"
        return ol
    return None

def extract_panel_info(panel):
    h4 = panel.find('h4')
    name = h4.get_text(strip=True) if h4 else ""
    labels = [span.get_text(strip=True) for span in panel.find_all('span', class_='status-macro')]
    content_div = panel.find('div', class_='panel-block-content')
    description_html = ""
    if content_div:
        for child in content_div.children:
            if getattr(child, 'name', None) == 'p':
                # Try to convert inline numbered lists
                text = child.get_text(separator=" ", strip=True)
                ol_html = convert_inline_numbered_list(text)
                if ol_html:
                    description_html += ol_html
                else:
                    description_html += f"<p>{extract_text_with_formatting(child)}</p>"
            elif getattr(child, 'name', None) == 'ol':
                description_html += "<ol>"
                for li in child.find_all('li', recursive=False):
                    description_html += f"<li>{extract_text_with_formatting(li)}</li>"
                description_html += "</ol>"
            elif getattr(child, 'name', None) == 'ul':
                description_html += "<ul>"
                for li in child.find_all('li', recursive=False):
                    description_html += f"<li>{extract_text_with_formatting(li)}</li>"
                description_html += "</ul>"
    return {
        "name": name,
        "description_html": description_html,
        "status_labels": ", ".join(labels)
    }

def fetch_week_entries(url):
    resp = safe_request(url)
    if not resp:
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    panels = get_jsm_section_panels(soup)
    if not panels:
        return []
    entries = []
    for panel in panels:
        try:
            entry = extract_panel_info(panel)
            if entry["name"]:
                entries.append(entry)
        except Exception as e:
            print(f"Error processing panel: {e}")
            traceback.print_exc()
    return entries

def normalize_name(name):
    return ' '.join(name.lower().strip().split())

def write_and_open_html(new_entries, this_week_url, last_week_url):
    html_content = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>New JSM Weekly Release Notes</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                background: #F4F5F7;
                color: #172B4D;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 900px;
                margin: 40px auto;
                padding: 0 24px 24px 24px;
            }}
            h1 {{
                font-size: 2rem;
                font-weight: 500;
                color: #253858;
                margin-top: 40px;
                margin-bottom: 0.5em;
            }}
            h2 {{
                font-size: 1.25rem;
                font-weight: 500;
                color: #172B4D;
                margin-top: 0;
                margin-bottom: 0.5em;
            }}
            .panel {{
                background: #fff;
                border: 1px solid #DFE1E6;
                border-radius: 8px;
                box-shadow: 0 1px 4px rgba(9,30,66,0.08);
                padding: 24px 32px 20px 32px;
                margin-bottom: 32px;
            }}
            .status {{
                margin-bottom: 1em;
            }}
            .lozenge {{
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
            }}
            .lozenge.coming-soon {{ background: #6554C0; }}
            .lozenge.rolling-out {{ background: #0052CC; }}
            .lozenge.launched {{ background: #36B37E; }}
            .lozenge.in-progress {{ background: #FFAB00; color: #172B4D; }}
            .lozenge.deprecated, .lozenge.removed {{ background: #FF5630; }}
            .lozenge.beta, .lozenge.experimental {{ background: #6554C0; }}
            .lozenge.new-this-week {{ background: #36B37E; }}  /* Green for "New this week" */
            .url {{
                font-size: 0.95em;
                color: #6B778C;
                margin-bottom: 0.5em;
            }}
            a {{
                color: #0052CC;
                text-decoration: none;
                border-bottom: 1px dotted #0052CC;
                transition: border-bottom 0.2s;
            }}
            a:hover {{
                border-bottom: 1px solid #0052CC;
            }}
            ul, ol {{
                margin-top: 0.5em;
                margin-left: 2em;
                margin-bottom: 1em;
            }}
            li {{
                margin-bottom: 0.5em;
                line-height: 1.6;
            }}
            p {{
                margin-top: 0.5em;
                margin-bottom: 0.5em;
                line-height: 1.7;
            }}
            hr {{
                border: none;
                border-top: 1px solid #DFE1E6;
                margin: 2em 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
        <h1>New Jira Service Management Changes</h1>
        <div class="url">Current week: <a href="{this_week_url}" target="_blank" rel="noopener">{this_week_url}</a></div>
        <div class="url">Last week: <a href="{last_week_url}" target="_blank" rel="noopener">{last_week_url}</a></div>
        <hr>
    """

    def confluence_lozenge(text):
        # Map status to CSS class
        status_map = {
            "coming soon": "coming-soon",
            "rolling out": "rolling-out",
            "launched": "launched",
            "in progress": "in-progress",
            "deprecated": "deprecated",
            "removed": "removed",
            "beta": "beta",
            "experimental": "experimental",
            "new this week": "new-this-week",  # Green for "New this week"
        }
        text_lower = text.lower()
        css_class = ""
        for key, val in status_map.items():
            if key in text_lower:
                css_class = val
                break
        return f'<span class="lozenge {css_class}">{html.escape(text)}</span>'

    if new_entries:
        for entry in new_entries:
            html_content += '<div class="panel">'
            html_content += f"<h2>{html.escape(entry['name'])}</h2>"
            if entry['status_labels']:
                lozenges = " ".join([confluence_lozenge(label) for label in entry["status_labels"].split(",")])
                html_content += f'<div class="status">{lozenges}</div>'
            if entry['description_html']:
                html_content += entry['description_html']
            html_content += "</div>"
    else:
        html_content += "<p>No new JSM entries this week.</p>"

    html_content += """
        </div>
        <script>
        // Ensure all links open in a new tab (in case any were missed)
        document.querySelectorAll('a').forEach(function(link) {
          link.setAttribute('target', '_blank');
          link.setAttribute('rel', 'noopener');
        });
        </script>
    </body></html>
    """

    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html') as f:
        f.write(html_content)
        temp_html_path = f.name

    webbrowser.open(f"file://{temp_html_path}")

def main():
    try:
        print("JSM Weekly Release Notes Extractor")
        print("==================================\\n")
        urls = get_weekly_release_urls()
        if len(urls) < 2:
            print("Error: Could not find enough release note URLs to compare.")
            return 1
        this_week_url, last_week_url = urls[0], urls[1]
        print(f"Current week URL: {this_week_url}")
        print(f"Last week URL: {last_week_url}\\n")
        this_week_entries = fetch_week_entries(this_week_url)
        if not this_week_entries:
            print("No JSM entries found for the current week.")
            return 1
        last_week_entries = fetch_week_entries(last_week_url)
        last_week_names = {normalize_name(e['name']) for e in last_week_entries}
        new_entries = []
        for entry in this_week_entries:
            if normalize_name(entry['name']) not in last_week_names:
                new_entries.append(entry)
        write_and_open_html(new_entries, this_week_url, last_week_url)
        return 0
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    main()
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(script_content)
        temp_script = f.name

    try:
        subprocess.check_call([python_path, temp_script])
    finally:
        os.unlink(temp_script)

def main():
    try:
        if create_venv():
            install_dependencies()
        run_script()
    except Exception as e:
        print(f"Error: {e}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
