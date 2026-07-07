"""Cliente CLI minimo para el servicio QR (solo para smoke tests)."""
import sys
import requests

def main():
    if len(sys.argv) < 2:
        print("Uso: python client.py <ruta_archivo>")
        sys.exit(1)
    with open(sys.argv[1], "rb") as f:
        r = requests.post("http://localhost:8766/extract", files={"file": f}, timeout=120)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        d = r.json()
        print(f"Items: {d['count']}")
        for it in d.get("items", []):
            print(f"  page={it['page']} format={it['format']} text={it['text'][:60]!r} b64_len={len(it['base64'])}")
    else:
        print(r.text)

if __name__ == "__main__":
    main()
