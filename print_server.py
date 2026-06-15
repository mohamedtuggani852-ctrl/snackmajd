#!/usr/bin/env python3
# ================================================
# Snack Majd - Serveur Impression WiFi
# Lancer dans Termux: python print_server.py
# ================================================
from http.server import HTTPServer, BaseHTTPRequestHandler
import socket, json, sys

PRINTER_IP   = "192.168.0.100"   # IP imprimante Snack Majd
PRINTER_PORT = 9100
SERVER_PORT  = 8765
PAPER_WIDTH  = 42   # 42 pour 80mm, 32 pour 58mm

# ── ESC/POS commands ──────────────────────────
ESC = b'\x1b'
GS  = b'\x1d'
INIT          = ESC + b'\x40'
ALIGN_LEFT    = ESC + b'\x61\x00'
ALIGN_CENTER  = ESC + b'\x61\x01'
ALIGN_RIGHT   = ESC + b'\x61\x02'
BOLD_ON       = ESC + b'\x45\x01'
BOLD_OFF      = ESC + b'\x45\x00'
SIZE_NORMAL   = GS  + b'\x21\x00'
SIZE_DOUBLE_H = GS  + b'\x21\x01'
SIZE_DOUBLE   = GS  + b'\x21\x11'
FEED          = b'\x0a'
CUT           = GS  + b'\x56\x41\x05'

def enc(text):
    return text.encode('cp1252', errors='replace')

def line(left, right, width):
    gap = width - len(left) - len(right)
    if gap < 1:
        left = left[:width - len(right) - 1]
        gap  = 1
    return left + ' ' * gap + right

def build_receipt(data, width):
    sep = '-' * width
    parts = []
    parts += [INIT, ALIGN_CENTER, BOLD_ON, SIZE_DOUBLE]
    parts += [enc("SNACK MAJD\n")]
    parts += [SIZE_NORMAL, BOLD_OFF]
    parts += [enc("Tacos Pasticcio Pizza Panini Jus\n")]
    parts += [enc("Tel: 07.78.06.54.56\n")]
    parts += [enc(sep + "\n"), ALIGN_LEFT]
    parts += [enc(f"Table: {data['table']}   {data.get('dateStr','')} {data.get('timeStr','')}\n")]
    parts += [enc(f"Ticket N {data['id']}\n")]
    parts += [enc(sep + "\n")]
    for it in data['items']:
        name = it['name'] + (f" ({it['size']})" if it.get('size') else "")
        sub  = str(it['price'] * it['qty']) + " DH"
        lbl  = f"{name} x{it['qty']}"
        parts += [enc(line(lbl, sub, width) + "\n")]
    parts += [enc(sep + "\n"), ALIGN_RIGHT, BOLD_ON, SIZE_DOUBLE_H]
    parts += [enc(f"TOTAL: {data['total']} DH\n")]
    parts += [SIZE_NORMAL, BOLD_OFF, ALIGN_CENTER, enc(sep + "\n")]
    parts += [enc("Merci de votre visite!\n")]
    parts += [enc("Chokran 3la Ziyartakom!\n")]
    parts += [FEED * 4, CUT]
    return b''.join(parts)

def build_test(width):
    sep = '-' * width
    parts = [INIT, ALIGN_CENTER, BOLD_ON, enc("TEST IMPRESSION\n"), BOLD_OFF,
             enc("Snack Majd - OK\n"), enc(sep + "\n"), FEED * 3, CUT]
    return b''.join(parts)

def send_raw(ip, port, data_bytes):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    s.connect((ip, port))
    s.sendall(data_bytes)
    s.close()

def cors(handler):
    handler.send_header('Access-Control-Allow-Origin', '*')
    handler.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
    handler.send_header('Access-Control-Allow-Headers', 'Content-Type')

def read_body(handler):
    n = int(handler.headers.get('Content-Length', 0))
    return json.loads(handler.rfile.read(n)) if n else {}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"  [{args[1]}] {args[0]}")

    def do_OPTIONS(self):
        self.send_response(200); cors(self); self.end_headers()

    def ok(self, msg="ok"):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        cors(self); self.end_headers()
        self.wfile.write(json.dumps({"ok": True, "msg": msg}).encode())

    def err(self, msg):
        self.send_response(500)
        self.send_header('Content-Type', 'application/json')
        cors(self); self.end_headers()
        self.wfile.write(json.dumps({"ok": False, "error": msg}).encode())

    def do_GET(self):
        global PRINTER_IP, PAPER_WIDTH
        if self.path == '/ping':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            cors(self); self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "printer": PRINTER_IP, "width": PAPER_WIDTH}).encode())
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        global PRINTER_IP, PAPER_WIDTH
        try:
            data = read_body(self)
        except Exception as e:
            self.err(str(e)); return

        if self.path == '/config':
            if 'ip'    in data: PRINTER_IP  = data['ip']
            if 'width' in data: PAPER_WIDTH = int(data['width'])
            print(f"  Config: printer={PRINTER_IP} width={PAPER_WIDTH}")
            self.ok(f"Printer set to {PRINTER_IP}")

        elif self.path == '/print':
            ip    = data.get('printerIP', PRINTER_IP)
            width = data.get('width', PAPER_WIDTH)
            try:
                send_raw(ip, PRINTER_PORT, build_receipt(data, width))
                print(f"  Printed: Table {data.get('table')} - {data.get('total')} DH")
                self.ok("printed")
            except Exception as e:
                print(f"  Error printing: {e}")
                self.err(str(e))

        elif self.path == '/test':
            ip    = data.get('ip', PRINTER_IP)
            width = data.get('width', PAPER_WIDTH)
            try:
                send_raw(ip, PRINTER_PORT, build_test(width))
                self.ok("test ok")
            except Exception as e:
                self.err(str(e))
        else:
            self.send_response(404); self.end_headers()

if __name__ == '__main__':
    if len(sys.argv) > 1: PRINTER_IP = sys.argv[1]
    if len(sys.argv) > 2: SERVER_PORT = int(sys.argv[2])
    print("=" * 45)
    print("  Snack Majd - Serveur Impression")
    print(f"  Printer: {PRINTER_IP}:{PRINTER_PORT}")
    print(f"  Server:  http://localhost:{SERVER_PORT}")
    print("=" * 45)
    try:
        HTTPServer(('', SERVER_PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\n  Arrete.")
