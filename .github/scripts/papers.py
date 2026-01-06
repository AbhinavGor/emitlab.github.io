import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests
from semanticscholar import SemanticScholar

_AUTHOR_PATTERN = re.compile(r'(author\s*=\s*[{"])(.*?)([}"],?)', re.IGNORECASE | re.DOTALL)


def dedupe_bibtex_authors(bibtex_entry):
    def dedupe_authors(match):
        authors_str = match.group(2)
        authors = [a.strip() for a in authors_str.split(' and ')]
        deduped = list(dict.fromkeys(authors))
        return match.group(1) + ' and '.join(deduped) + match.group(3)

    return _AUTHOR_PATTERN.sub(dedupe_authors, bibtex_entry)


def update_index_heading_date(script_dir: Path) -> None:

    project_root = script_dir.parent.parent
    index_path = project_root / "index.html"

    if not index_path.exists():
        print(f"index.html not found at {index_path}, skipping heading date update")
        return

    try:
        with index_path.open("r", encoding="utf-8") as f:
            html = f.read()
    except OSError as e:
        print(f"Failed to read {index_path}: {e}")
        return

    today_str = datetime.today().strftime("%m/%y")
    new_heading = f"Publications ({today_str} - from Semantic Scholar)"

    # Replace only the Semantic Scholar heading, not the DBLP one
    pattern = r"Publications\s*\([^)]*-?\s*from\s+Semantic\s+Scholar[^)]*\)"
    new_html, count = re.subn(pattern, new_heading, html, flags=re.IGNORECASE)
    if count == 0:
        print("Did not find Publications heading to update in index.html")
        return

    try:
        with index_path.open("w", encoding="utf-8") as f:
            f.write(new_html)
        print(f"Updated publications heading date in {index_path} to {today_str}")
    except OSError as e:
        print(f"Failed to write {index_path}: {e}")


def main():
    author_ids = ['1720972', '2062304687','2239621942','51877438','1972061357']
    sch = SemanticScholar()

    # fetch all papers from all of the authors, then get the ids of the papers, keeping only the unique ones.
    paper_ids = set()
    for author_id in author_ids:
        author_papers = sch.get_author_papers(author_id)
        for paper in author_papers:
            paper_ids.add(paper['paperId'])
    paper_ids = list(paper_ids)
        
    # read a list of paper ids from a blacklist file.
    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    blacklist_path = script_dir / 'blacklist.txt'
    
    if blacklist_path.exists():
        with open(blacklist_path, 'r') as f:
            blacklist = [line.strip() for line in f if line.strip()]  # Skip empty lines
        paper_ids = [paper_id for paper_id in paper_ids if paper_id not in blacklist]
    else:
        print(f"Warning: blacklist.txt not found at {blacklist_path}, skipping blacklist filtering")

    print(f"Found {len(paper_ids)} papers")

    bibtex_list = []
    count = 0
    paper_infos = sch.get_papers(paper_ids)

    for paper_info in paper_infos:
        count += 1
        bibtex = paper_info.citationStyles['bibtex']

        # replace the author K. Candan, S. Candan, etc. in the bibtex with K. Selcuk Candan
        bibtex = bibtex.replace('K. Candan', 'K. Selçuk Candan')
        bibtex = bibtex.replace('S. Candan', 'K. Selçuk Candan')
        bibtex = bibtex.replace('Kasim Selçuk Candan', 'K. Selçuk Candan')
        bibtex = bibtex.replace('Kasim Selcuk Candan', 'K. Selçuk Candan')
        bibtex = bibtex.replace('Kapkicc', 'Kapkiç')
        bibtex = bibtex.replace('Kapkic', 'Kapkiç')

        # remove duplicate authors in the 'author' field, keep first occurrence
        bibtex = dedupe_bibtex_authors(bibtex)

        # fetch the doi of the paper if avaiable
        try:
            doi = paper_info.externalIds['DOI']
            # doi may not be in the bibtex, so add it to the last line of bibtex.
            bibtex = bibtex.replace('}\n}', f'}},\n doi = {{{doi}}}\n}}')
        except:
            doi = None
        
        # fetch the url of the paper if available
        try:
            url = paper_info.url
            bibtex = bibtex.replace('}\n}', f'}},\n url = {{{url}}}\n}}')
        except:
            url = None
        bibtex_list.append(bibtex)
        
        print(f"Added {count}, out of {len(paper_ids)}")

    #save bibtext list to a file.
    with open('assets/publications.bib', 'w') as f:
        for bibtex in bibtex_list:
            f.write(bibtex + '\n')

    # After updating publications, also refresh the heading date in index.html
    update_index_heading_date(script_dir)

if __name__ == '__main__':
    main()
