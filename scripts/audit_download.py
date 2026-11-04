# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Samuele Timoteo Iacierno
"""Checks the download package before upload: intact ZIPs, version, legal texts identical to
platform/terms, interface security policy, no user data, keys or databases, matching checksums,
complete source code and (macOS) a valid signature after unpacking.
"""
from pathlib import Path
import hashlib,plistlib,shutil,subprocess,sys,tempfile,zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'platform/python'))
from financecore import PRODUCT,VERSION

OUT=ROOT/'releases'/('downloadpaket-'+VERSION)
LEGAL=['FinanzManager.md','Datenschutz.md','Impressum.md','Komponenten.md','Sicherheit.md','GPL-3.0.txt','MIT-Gestaltung.txt']
FORBIDDEN=('.sqlite3','.sqlite3-journal','.fmb','.p12','.pem','.key','programm.json','.DS_Store')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def check_program(archive):
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None,'ZIP beschädigt: '+archive.name
        names=z.namelist()
        assert not any(n.endswith(FORBIDDEN) for n in names),'Verbotene Datei in '+archive.name
        mac=archive.name.endswith('-macOS.zip')
        base=PRODUCT+'.app/Contents/Resources/' if mac else PRODUCT+'/_internal/'
        if mac:assert plistlib.loads(z.read(PRODUCT+'.app/Contents/Info.plist'))['CFBundleShortVersionString']==VERSION,'Version passt nicht'
        for name in LEGAL:assert z.read(base+'Legal/'+name)==(ROOT/'platform/terms'/name).read_bytes(),'Rechtstext weicht ab: '+name
        assert any(n.startswith(base+'Legal/PythonProgram/') and n.endswith('components.json') for n in names),'Komponentenliste fehlt'
        page=z.read(base+'Web/index.html').decode()
        assert "connect-src 'self'" in page and "script-src 'unsafe-inline'" in page and 'unsafe-eval' not in page,'Sicherheitsrichtlinie der Oberfläche fehlt'
        if mac:
            with tempfile.TemporaryDirectory() as temp:
                subprocess.run(['/usr/bin/ditto','-x','-k',str(archive),temp],check=True)
                subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(Path(temp)/(PRODUCT+'.app'))],check=True)

def main():
    programs=sorted(OUT.glob('FinanzManager-Pro-'+VERSION+'-*.zip'))
    apps=[p for p in programs if not p.name.endswith('-Quellcode.zip')]
    assert apps,'Kein Programm im Downloadpaket'
    for program in apps:
        assert sha(program)==sha(ROOT/'releases'/program.name),'Programm weicht vom Build ab: '+program.name
        check_program(program)
    source=OUT/('FinanzManager-Pro-'+VERSION+'-Quellcode.zip')
    with zipfile.ZipFile(source) as z:
        names=z.namelist();prefix='FinanzManager-Pro-'+VERSION+'-Quellcode/'
        for needed in ['LICENSE','README.md','apps/FinanzManager/desktop/finanzmanager_desktop.py','platform/python/financecore/store.py','scripts/build.py','tests/test_store.py']:assert prefix+needed in names,'Quellcode unvollständig: '+needed
        assert not any(n.endswith('.swift') or '__pycache__' in n or n.endswith(FORBIDDEN) for n in names),'Unerwartete Datei im Quellcode'
    sums={line.split('  ')[1]:line.split('  ')[0] for line in (OUT/'SHA256SUMS.txt').read_text().splitlines()}
    assert sums=={p.name:sha(p) for p in programs},'Prüfsummen passen nicht'
    for slug,name in [('nutzung','FinanzManager.md'),('datenschutz','Datenschutz.md'),('impressum','Impressum.md'),('lizenzen','Komponenten.md'),('sicherheit','Sicherheit.md')]:
        assert (OUT/(slug+'.txt')).read_bytes()==(ROOT/'platform/terms'/name).read_bytes(),'Textfassung weicht ab: '+slug
    print('PASS',', '.join(p.name for p in apps),'+ Quellcode, Rechtstexte, Prüfsummen'+(' und Signatur' if any(p.name.endswith('-macOS.zip') for p in apps) else ''))

if __name__=='__main__':main()
