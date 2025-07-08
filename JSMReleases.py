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
import string
import platform
import signal
import time
import traceback

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
        if content.name in ('strong', 'b'):
            result += f"**{content.get_text()}**"
        elif content.name:
            result += extract_text_with_formatting(content)
        else:
            result += str(content)
    return result

def extract_panel_info(panel):
    h4 = panel.find('h4')
    name = h4.get_text(strip=True) if h4 else ""
    
    labels = [span.get_text(strip=True) for span in panel.find_all('span', class_='status-macro')]
    content_div = panel.find('div', class_='panel-block-content')
    
    description_parts = []
    description_html = ""
    
    if content_div:
        for child in content_div.children:
            if getattr(child, 'name', None) == 'p':
                description_html += str(child)
                text = extract_text_with_formatting(child)
                if text.strip():
                    description_parts.append(text.strip())
            elif getattr(child, 'name', None) in ['ol', 'ul']:
                description_html += str(child)
                if description_parts:
                    description_parts.append("")
                
                for i, li in enumerate(child.find_all('li', recursive=False), 1):
                    text = extract_text_with_formatting(li)
                    prefix = f"{i}. " if child.name == 'ol' else "• "
                    description_parts.append(f"{prefix}{text.strip()}")
                
                description_parts.append("")
    
    description = "\\n\\n".join(filter(None, description_parts))
    
    links = []
    if description_html:
        soup = BeautifulSoup(description_html, 'html.parser')
        for a in soup.find_all('a', href=True):
            link_text = a.get_text(strip=True)
            href = a['href']
            if href.startswith('/'):
                href = "https://confluence.atlassian.com" + href
            links.append((link_text, href))
    
    return {
        "name": name,
        "description": description,
        "status_labels": ", ".join(labels),
        "links": links
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
        
        if new_entries:
            print("\\n===== NEW JIRA SERVICE MANAGEMENT CHANGES =====\\n")
            for i, entry in enumerate(new_entries, 1):
                print(f"{i}. {entry['name']}")
                if entry['status_labels']:
                    print(f"   Status: {entry['status_labels']}\\n")
                
                if entry['description']:
                    lines = entry['description'].split('\\n')
                    for line in lines:
                        line = line.strip()
                        if line:
                            print(f"   {line}")
                            print()
                
                if entry['links']:
                    print("   Links:")
                    for text, url in entry['links']:
                        print(f"   - {text}: {url}")
                    print()
                print()
        else:
            print("\\nNo new JSM entries this week.")
        
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