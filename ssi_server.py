#!/usr/bin/env python3

'''
A simple http server with SSI support.

Usage:

./ssi_server.py [--port 8000] [--dir .]

SSI is enabled if file name ends with '.shtml'.

Use ./ssi_server.py -g to generate html by expand shtml.
'''

__author__ = 'Michael Liao'
__version__ = '1.0'

import re, os, urllib, shutil, argparse, functools, mimetypes

from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler, HTTPStatus

AUTO_GENERATED = 'AUTO GENERATED HTML: DO NOT MODIFY MANUALLY'

DIR_IGNORE = ['node_modules', 'artifacts', 'cache', 'build', 'bin', 'tests']

INCLUDE_FILE = re.compile(r'^\s*\<\!\-\-\s*\#include\s+file\=\"([a-zA-Z0-9\-\_\.\/]+)\"\s*\-\-\>\s*$')

mimetypes.add_type('text/html', '.shtml')

def _expand_line(doc_root, line):
    '''
    Return line itself or file content by SSI directive <!--#include file="xxx"-->
    '''
    m = INCLUDE_FILE.match(line)
    if m:
        inc_file = m.group(1)
        print(f'found include: {inc_file}')
        if inc_file.endswith('.shtml'):
            return _expand_shtml(doc_root, inc_file)
        else:
            with open(os.path.join(doc_root, inc_file), 'r', encoding='utf-8') as fp:
                inc_content = fp.read()
            if inc_content[-1] != '\n':
                inc_content = inc_content + '\n'
            return inc_content
    else:
        if line.find('<!--#include') >= 0:
            print(f'WARNING: invalid directive: {line}')
        return line

def _expand_shtml(doc_root, fs):
    '''
    Return html content by processing SSI directive <!--#include file="xxx"-->
    '''
    with open(os.path.join(doc_root, fs), 'r', encoding='utf-8') as fp:
        lines = fp.readlines()
    slines = [_expand_line(doc_root, line) for line in lines]
    return f'<!-- {AUTO_GENERATED} -->\n' + ''.join(slines)

def _generate(doc_root, fs, force_overwrite):
    '''
    Process xxx.shtml and generate xxx.html.
    '''
    fh = fs[:-6] + '.html'
    print(f'generate {fs} to {fh}...')
    html = _expand_shtml(doc_root, fs)
    if os.path.exists(fh):
        with open(fh, 'r', encoding='utf-8') as fp:
            first_line = fp.readline()
        if not first_line.startswith('<!--') or first_line.find(AUTO_GENERATED) < 0:
            if not force_overwrite:
                print(f'ERROR: target file exist and it seems not auto-generated: {fh}')
                exit(1)
            else:
                print(f'WARNING: target file exist and it seems not auto-generated: {fh}')
    with open(fh, 'w', encoding='utf-8') as fp:
        fp.write(html)

def generate(doc_root, rel_path, force_override):
    '''
    Process all .shtml and generate .html.
    '''
    for f in os.listdir(os.path.join(doc_root, rel_path)):
        if os.path.isdir(os.path.join(doc_root, rel_path, f)):
            next_rel_path = os.path.join(rel_path, f)
            if f.startswith('.') or f in DIR_IGNORE:
                print(f'ignore dir: {next_rel_path}')
            else:
                generate(doc_root, next_rel_path, force_override)
        else:
            if f.endswith('.shtml'):
                _generate(doc_root, os.path.join(rel_path, f), force_override)

def serve(doc_root, port):
    print(f'start httpd at {port}...')
    addr = ('', port)
    httpd = ThreadingHTTPServer(addr, functools.partial(SSIHTTPRequestHandler, directory=doc_root))
    httpd.serve_forever()

class SSIHTTPRequestHandler(BaseHTTPRequestHandler):
    '''
    Simple HTTP request handler with SSI directive support.
    '''

    def __init__(self, *args, directory=None, **kwargs):
        self.directory = os.fspath(directory)
        super().__init__(*args, **kwargs)

    def do_GET(self):
        path = self.translate_path(self.path)
        print(f'translated path: {path}')
        if path.endswith('.html'):
            path_of_shtml = path[:-5] + '.shtml'
            if os.path.isfile(path_of_shtml):
                path = path_of_shtml
        if not os.path.isfile(path):
            self.send_response(HTTPStatus.NOT_FOUND, 'Not Found')
            self.end_headers()
            return None

        print(f'send file: {path}...')
        content = b''
        if path.endswith('.shtml'):
            rel_path = path[len(self.directory)+1:]
            content = _expand_shtml(self.directory, rel_path)
        else:
            with open(path, 'rb') as f:
                content = f.read()
        if isinstance(content, str):
            content = content.encode('utf-8')

        mime, _ = mimetypes.guess_type(path)
        if not mime:
            mime = 'application/octet-stream'

        self.send_response(HTTPStatus.OK)
        self.send_header('Content-type', mime)
        self.send_header('Content-Length', len(content))
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(content)

    def translate_path(self, path):
        # abandon query parameters
        path = path.split('?',1)[0]
        path = path.split('#',1)[0]
        # Don't forget explicit trailing slash when normalizing. Issue17324
        trailing_slash = path.rstrip().endswith('/')
        try:
            path = urllib.parse.unquote(path, errors='surrogatepass')
        except UnicodeDecodeError:
            path = urllib.parse.unquote(path)
        path = os.path.normpath(path)
        words = path.split('/')
        words = filter(None, words)
        path = self.directory
        for word in words:
            if os.path.dirname(word) or word in (os.curdir, os.pardir):
                # Ignore components that are not a simple file/directory name
                continue
            path = os.path.join(path, word)
        if trailing_slash:
            path += '/index.html'
        return path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='http_server',
        description='Simple HTTP server with SSI support.'
    )
    parser.add_argument('-g', '--generate', action='store_true', help='Generate HTML by expand SHTML.')
    parser.add_argument('-f', '--force', action='store_true', help='Force override target HTML.')
    parser.add_argument('-d', '--dir', default='.', help='HTTP root dir. Default to "." (current dir)')
    parser.add_argument('-p', '--port', default=8000, type=int, help='HTTP server port. Default to 8000.')

    args = parser.parse_args()
    doc_root = os.path.abspath(args.dir)
    port = args.port

    if args.generate:
        print(f'generating html files at {doc_root}...')
        generate(doc_root, '', args.force)
    else:
        serve(doc_root, port)
