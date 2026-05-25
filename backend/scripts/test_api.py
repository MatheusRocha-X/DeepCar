import urllib.request
import json

# Test page 26 to find iCarros vehicles
r = urllib.request.urlopen("http://localhost:8000/api/search?page=26&per_page=20")
data = json.loads(r.read())
print(f"Total: {data['total']} | Page 26/{data['total_pages']}")
for v in data["results"]:
    fotos_count = len(v.get("fotos") or [])
    print(f"  [{v['source_name']}] {v['titulo']} | sc:{v['score']} | {fotos_count}fotos")


