"""Post-process a docx written by docx-js: add the empty <m:sup/> (or <m:sub/>) that OOXML requires
inside n-ary operators whose limit is hidden. Without it the file fails schema validation."""

import re
import shutil
import sys
import tempfile
import zipfile

path = sys.argv[1]
with zipfile.ZipFile(path) as z:
    items = {n: z.read(n) for n in z.namelist()}
xml = items["word/document.xml"].decode("utf8")


def fix(m: re.Match) -> str:
    block = m.group(0)
    if "<m:sup>" not in block and "<m:sup/>" not in block:
        block = block.replace("<m:e>", "<m:sup/><m:e>", 1) if "</m:sub>" not in block else \
            block.replace("</m:sub>", "</m:sub><m:sup/>", 1)
    if "<m:sub>" not in block and "<m:sub/>" not in block:
        block = block.replace("</m:naryPr>", "</m:naryPr><m:sub/>", 1)
    return block


# naryPr ... sub? sup? e: patch only the head of each n-ary (up to its first <m:e>).
xml = re.sub(r"<m:nary><m:naryPr>.*?</m:naryPr>(?:<m:sub>.*?</m:sub>)?(?:<m:sup>.*?</m:sup>)?<m:e>", fix, xml, flags=re.S)
items["word/document.xml"] = xml.encode("utf8")
tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx").name
with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
    for n, data in items.items():
        z.writestr(n, data)
shutil.move(tmp, path)
print("math fixed:", xml.count("<m:sup/>"), "empty upper limits")
