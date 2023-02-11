# Server Side Includes Server

SSI-Server is a simple HTTP server that supports the old Server-Side-Includes technology.

Using SSI to design .shtml can reduce lots of templating work, and simply publish all .shtml to .html pages to make everything works on GitHub pages or other static web server!

# Usage

Start server:

```
$ ./ssi_server.py [--port 8000] [--dir .]
```

Generate static pages:

```
$ ./ssi_server.py -g [--dir .]
```

# Limitation

Only support `include file` directive:

```
<!--#include file="header.html" -->
```

Directive must be in a single line that cannot contains other HTML tags:

```
<!-- ok -->
<div>
    <!--#include file="header.html" -->
</div>

<!-- wrong -->
<div><!--#include file="header.html" --></div>
```

# Best Practice

Always use `.html` for links:

```
<!-- index.shtml -->
<a href="about.html">About</a>
<!-- will response to about.shtml if file exists -->
```
