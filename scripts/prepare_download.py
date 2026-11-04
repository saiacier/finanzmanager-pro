# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Samuele Timoteo Iacierno
"""Collects the download package: program ZIPs of every system already built, source code ZIP,
legal texts as plain text, GPL text and checksums. No web pages: the download is embedded into
the provider's own website.
"""
from pathlib import Path
import hashlib,shutil,sys,zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'platform/python'))
from financecore import VERSION

OUT=ROOT/'releases'/('downloadpaket-'+VERSION)
SOURCE_ITEMS=['LICENSE','MARKEN-HINWEIS.md','README.md','apps','platform','scripts','tests']
SKIP_NAMES={'.DS_Store','documents_generated.py'}

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    programs=sorted(ROOT.glob('releases/FinanzManager-Pro-'+VERSION+'-*.zip'))
    if not programs:sys.exit('Bitte zuerst scripts/build.py ausführen.')
    if OUT.exists():shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for program in programs:shutil.copyfile(program,OUT/program.name)
    for slug,name in [('nutzung','FinanzManager.md'),('datenschutz','Datenschutz.md'),('impressum','Impressum.md'),('lizenzen','Komponenten.md'),('sicherheit','Sicherheit.md')]:
        shutil.copyfile(ROOT/'platform/terms'/name,OUT/(slug+'.txt'))
    shutil.copyfile(ROOT/'platform/terms/GPL-3.0.txt',OUT/'GPL-3.0.txt')
    source=OUT/('FinanzManager-Pro-'+VERSION+'-Quellcode.zip');prefix='FinanzManager-Pro-'+VERSION+'-Quellcode/'
    # Corresponding source for the GPL release; build outputs and local data stay out.
    with zipfile.ZipFile(source,'w',zipfile.ZIP_DEFLATED) as z:
        for item in SOURCE_ITEMS:
            for file in sorted([ROOT/item] if (ROOT/item).is_file() else (ROOT/item).rglob('*')):
                if file.is_file() and file.name not in SKIP_NAMES and '__pycache__' not in file.parts:z.write(file,prefix+file.relative_to(ROOT).as_posix())
    (OUT/'SHA256SUMS.txt').write_text(''.join(sha(f)+'  '+f.name+'\n' for f in [*sorted(OUT.glob('FinanzManager-Pro-'+VERSION+'-*.zip'))]))
    archive=ROOT/'releases'/('FinanzManager-Downloadpaket-'+VERSION+'.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for file in sorted(OUT.rglob('*')):
            if file.is_file():z.write(file,file.relative_to(OUT))
    print(OUT)

if __name__=='__main__':main()
