"""Loopback-only HTTP app, standard library only."""
import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
try:
    from .engine import Engine, InputError, ACTIVITIES
except ImportError:
    from engine import Engine, InputError, ACTIVITIES
ROOT=Path(__file__).parent/'web'
engine=Engine(); lock=threading.RLock()
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def reply(self,code,data,mime='application/json; charset=utf-8'):
        b=json.dumps(data,ensure_ascii=False).encode() if mime.startswith('application/json') else data
        self.send_response(code)
        for k,v in {'Content-Type':mime,'Content-Length':str(len(b)),'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'"}.items(): self.send_header(k,v)
        self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        p=urlparse(self.path); q=parse_qs(p.query)
        try:
            with lock:
                sid=q.get('id',[''])[0]
                if p.path=='/api/health': return self.reply(200,{'ok':True,'version':'0.2.0','storage':'memory-only'})
                if p.path=='/api/activities': return self.reply(200,{k:{'title':v['title'],'tag':v['tag']} for k,v in ACTIVITIES.items()})
                if p.path=='/api/session': return self.reply(200,engine.view(engine.get(sid)))
                if p.path=='/api/report': return self.reply(200,engine.report(sid))
                if p.path=='/api/robot': return self.reply(200,engine.robot_poll(sid,q.get('mode',['dry-run'])[0]))
            names={'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/style.css':('style.css','text/css; charset=utf-8')}
            if p.path.startswith('/assets/'):
                name=p.path.removeprefix('/assets/')
                if name in {f.name for f in (ROOT/'assets').glob('*.webp')}: return self.reply(200,(ROOT/'assets'/name).read_bytes(),'image/webp')
            if p.path not in names: return self.reply(404,{'error':'Not found'})
            name,mime=names[p.path]; return self.reply(200,(ROOT/name).read_bytes(),mime)
        except InputError as e: self.reply(400,{'error':str(e)})
    def do_POST(self):
        origin=self.headers.get('Origin')
        if origin and origin!='http://'+self.headers.get('Host',''): return self.reply(403,{'error':'不接受跨来源请求。'})
        if self.headers.get('Content-Type','').split(';')[0]!='application/json': return self.reply(415,{'error':'JSON required'})
        try:
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<=8192: return self.reply(413,{'error':'Body too large'})
            d=json.loads(self.rfile.read(n))
            if not isinstance(d,dict): raise InputError('需要 JSON 对象。')
            with lock:
                if self.path=='/api/session': return self.reply(201,engine.create(d))
                if self.path=='/api/event': return self.reply(200,engine.event(d.get('id'),d))
                if self.path=='/api/delete':
                    engine.sessions.pop(d.get('id'),None); return self.reply(200,{'deleted':True})
            self.reply(404,{'error':'Not found'})
        except (InputError,ValueError,TypeError) as e: self.reply(400,{'error':str(e)})
def main():
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8787);a=p.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',a.port),Handler)
    print(f'慢慢星 http://localhost:{a.port} | Ctrl+C to stop',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
if __name__=='__main__': main()
