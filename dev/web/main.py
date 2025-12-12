import re
import requests
from bs4 import BeautifulSoup

url = "https://annas-archive.org/md5/f1724a521de7afadc7f93d5fabf7e3a3"

response = requests.get(url)
response.raise_for_status()

soup = BeautifulSoup(response.content, 'html.parser')

# Find all aacid identifiers using regex pattern
# Pattern: aacid__collection__timestamp__identifier__hash
aacid_pattern = re.compile(r'aacid__[a-zA-Z0-9_]+__\d{8}T\d{6}Z__[a-zA-Z0-9_]+__[a-zA-Z0-9]+')
aacids = set()

# Search in all text content
for text in soup.stripped_strings:
    matches = aacid_pattern.findall(text)
    aacids.update(matches)

# Search in all attributes
for element in soup.find_all():
    for attr, value in element.attrs.items():
        if isinstance(value, str):
            matches = aacid_pattern.findall(value)
            aacids.update(matches)
        elif isinstance(value, list):
            for v in value:
                if isinstance(v, str):
                    matches = aacid_pattern.findall(v)
                    aacids.update(matches)

# Print all unique aacid fields found
print("Found aacid fields:")
for aacid in sorted(aacids):
    print(aacid)
