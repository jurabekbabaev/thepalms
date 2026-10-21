#!/usr/bin/env python3
"""Clean up a wget mirror so it works on GitHub Pages.

Usage: python3 postprocess.py <docs_dir> <domain> [inject_file]

1. Files saved by wget with a query string (``file.js@ver=1.2``) get their
   clean name back (``file.js``); references in HTML/CSS are rewritten.
   GitHub Pages picks the MIME type from the extension, so ``.js@ver=1.2``
   would be served as a binary and the browser would refuse to run it.
2. 404 stubs that wget saved as ``image.png.html`` are removed and the
   references point back to the original name.
3. Absolute ``http://<domain>`` links are upgraded to https.
4. Optional: the contents of ``inject_file`` are inserted before </body>
   of every HTML page (used for small fixes such as the contact form).
"""
import os
import re
import sys

ASSET_EXT = r"(?:css|js|json|woff2?|ttf|eot|svg|png|jpe?g|gif|webp|ico|mp4)"


def main():
    docs, domain = sys.argv[1], sys.argv[2]
    inject = open(sys.argv[3], encoding="utf-8").read() if len(sys.argv) > 3 else ""

    # 1. rename "name.ext@query[.ext]" -> "name.ext"
    renamed = 0
    for root, _dirs, files in os.walk(docs):
        for f in sorted(files):  # sorted: higher version wins on collision
            if "@" not in f:
                continue
            clean = f.split("@", 1)[0]
            src, dst = os.path.join(root, f), os.path.join(root, clean)
            if os.path.exists(dst):
                os.remove(dst)
            os.rename(src, dst)
            renamed += 1

    # 2. remove 404 stubs "x.png.html"
    stubs = 0
    stub_re = re.compile(r"\." + ASSET_EXT + r"\.html$", re.I)
    for root, _dirs, files in os.walk(docs):
        for f in files:
            p = os.path.join(root, f)
            if stub_re.search(f) and os.path.getsize(p) < 2048:
                os.remove(p)
                stubs += 1

    ref_query = re.compile(r"(\." + ASSET_EXT + r")(?:@|%40)[^\"'\s)<>]*", re.I)
    ref_stub = re.compile(r"(\." + ASSET_EXT + r")\.html(?=[\"'\s)?#])", re.I)
    dom = re.escape(domain)
    http_abs = re.compile(r"http:(\\?/\\?/)(www\.)?" + dom)

    edited = 0
    for root, _dirs, files in os.walk(docs):
        for f in files:
            if not f.endswith((".html", ".css")):
                continue
            p = os.path.join(root, f)
            with open(p, encoding="utf-8", errors="surrogateescape") as fh:
                text = fh.read()
            new = ref_query.sub(r"\1", text)
            new = ref_stub.sub(r"\1", new)
            new = http_abs.sub(lambda m: "https:" + m.group(1) + domain, new)
            if inject and f.endswith(".html") and "</body>" in new and inject not in new:
                new = new.replace("</body>", inject + "\n</body>", 1)
            if new != text:
                with open(p, "w", encoding="utf-8", errors="surrogateescape") as fh:
                    fh.write(new)
                edited += 1

    print(f"renamed={renamed} stubs_removed={stubs} files_edited={edited}")


if __name__ == "__main__":
    main()
