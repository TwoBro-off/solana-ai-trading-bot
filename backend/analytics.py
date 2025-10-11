"""
Module: analytics.py
Description: Export et analytics des performances (CSV/JSON/HTML).
"""
import csv, json
from typing import List, Dict

def export_results_csv(results: List[Dict], path: str):
    if not results:
        return
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        header = list(results[0].keys())
        writer.writerow(header)
        for r in results:
            writer.writerow([r[k] for k in header])

def export_results_json(results: List[Dict], path: str):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

def export_results_html(results: List[Dict], path: str):
    with open(path, 'w', encoding='utf-8') as f:
        f.write('<html><body><table border="1">')
        if results:
            f.write('<tr>' + ''.join(f'<th>{k}</th>' for k in results[0].keys()) + '</tr>')
            for r in results:
                f.write('<tr>' + ''.join(f'<td>{r[k]}</td>' for k in r.keys()) + '</tr>')
        f.write('</table></body></html>')
