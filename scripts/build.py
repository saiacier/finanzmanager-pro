# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Samuele Timoteo Iacierno
"""Builds FinanzManager Pro for macOS or Windows.

Run with the build Python (PyInstaller, pywebview) on the target system, PyInstaller cannot build
for another system:
  work/build-env/bin/python scripts/build.py          (macOS)
  work\\build-env\\Scripts\\python scripts\\build.py   (Windows)

Steps: interface page, embedded legal documents, PyInstaller folder build, notices for every
bundled Python distribution (allowlist platform/compliance/python-policy.json, unknown
components stop the build), checks for forbidden files and foreign native libraries, signature,
isolated start with a temporary data folder (--self-test) and ZIP with checksum.
No user data or private keys are read or packaged.
"""
from pathlib import Path
import ast,hashlib,importlib.metadata as metadata,json,os,plistlib,re,shutil,struct,subprocess,sys,sysconfig,tempfile,zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'platform/python'))
from financecore import BUILD,BUNDLE_ID,PRODUCT,VERSION
from financecore import desktop,documents

MAC,WINDOWS=sys.platform=='darwin',os.name=='nt'
# Build files stay outside synced folders (OneDrive locks files during PyInstaller's cleanup).
BUILD_ROOT=Path(os.environ.get('FINANCE_BUILD_DIR') or (Path.home()/'Library/Caches/FinanzManager-build' if MAC else Path(os.environ.get('LOCALAPPDATA',tempfile.gettempdir()))/'FinanzManager-build'))
WORK,DIST,RELEASES=BUILD_ROOT/'pyinstaller',BUILD_ROOT/'dist',ROOT/'releases'
SYSTEM='macOS' if MAC else 'Windows' if WINDOWS else sys.platform
ARCHIVE=RELEASES/('FinanzManager-Pro-'+VERSION+'-'+SYSTEM+'.zip')
LEGAL_FILES=['FinanzManager.md','Datenschutz.md','Impressum.md','Komponenten.md','Sicherheit.md','GPL-3.0.txt','MIT-Gestaltung.txt']
EXCLUDES=['tkinter','_tkinter','numpy','pytest','IPython','PIL','webview.platforms.qt','webview.platforms.gtk','webview.platforms.android','webview.platforms.cef','PyQt5','PyQt6','PySide2','PySide6','gi']
FORBIDDEN_SUFFIXES=('.sqlite3','.sqlite3-journal','.sqlite3-wal','.sqlite3-shm','.fmb','.key','.pem','.p12')
FORBIDDEN_NAMES={'programm.json','.DS_Store'}

class ReleaseError(RuntimeError):pass
def run(*args,**kw):subprocess.run(list(map(str,args)),check=True,**kw)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def prepare():
    """Interface page and legal folder for the package; documents embedded into FinanceCore."""
    web=WORK/'Web';legal=WORK/'Legal'
    for folder in (web,legal):
        if folder.exists():shutil.rmtree(folder)
        folder.mkdir(parents=True)
    page=desktop.interface(ROOT/'apps/FinanzManager/Web')
    if "connect-src 'self'" not in page or '/* FINANCE_STORAGE */' in page:raise ReleaseError('Oberfläche unvollständig oder ohne Sicherheitsrichtlinie.')
    (web/'index.html').write_text(page,encoding='utf-8')
    documents.generate(ROOT/'platform/terms',ROOT/'platform/python/financecore/documents_generated.py')
    for name in LEGAL_FILES:shutil.copy(ROOT/'platform/terms'/name,legal/name)
    shutil.copy(ROOT/'platform/terms/Komponenten.md',legal/'README.md')
    return web,legal

def ico(png,target):
    """Windows icon with the PNG image embedded (supported since Windows Vista)."""
    data=Path(png).read_bytes()
    Path(target).write_bytes(struct.pack('<HHH',0,1,1)+struct.pack('<BBBBHHII',0,0,0,0,1,32,len(data),22)+data)
    return target

def pyinstaller(web,legal):
    WORK.mkdir(parents=True,exist_ok=True);sep=os.pathsep
    icon=ROOT/'apps/FinanzManager/Resources/AppIcon.icns' if MAC else ico(ROOT/'apps/FinanzManager/Web/assets/app-icon.png',WORK/'FinanzManager.ico')
    args=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed','--onedir','--name',PRODUCT,'--distpath',DIST,'--workpath',WORK,'--specpath',WORK,
          '--icon',icon,'--paths',ROOT/'platform/python','--collect-submodules','financecore','--add-data',str(web)+sep+'Web','--add-data',str(legal)+sep+'Legal']
    if MAC:args+=['--osx-bundle-identifier',BUNDLE_ID]
    for name in EXCLUDES:args+=['--exclude-module',name]
    env=dict(os.environ,PYINSTALLER_CONFIG_DIR=str(WORK/'config'),PYTHONDONTWRITEBYTECODE='1')
    run(*args,ROOT/'apps/FinanzManager/desktop/finanzmanager_desktop.py',env=env)

def layout():
    """(program folder or .app, resources folder, executable)."""
    if MAC:
        app=DIST/(PRODUCT+'.app');return app,app/'Contents/Resources',app/'Contents/MacOS'/PRODUCT
    folder=DIST/PRODUCT;return folder,folder/'_internal',folder/(PRODUCT+'.exe')

def bundled_distributions():
    """Distributions whose modules or binaries PyInstaller placed into the program."""
    toc=[ast.literal_eval(f.read_text()) for f in sorted((WORK/PRODUCT).glob('*.toc')) if f.name.startswith(('Analysis','COLLECT','PYZ'))]
    if not toc:raise ReleaseError('PyInstaller-Inhaltsverzeichnis fehlt.')
    names=set()
    def walk(value):
        if isinstance(value,(tuple,list)):
            if len(value)>=3 and isinstance(value[0],str) and isinstance(value[2],str) and value[2] in ('PYMODULE','PYSOURCE','EXTENSION','BINARY','DATA','PYZ'):names.add(value[0])
            else:
                for item in value:walk(item)
    walk(toc)
    owners=metadata.packages_distributions();found={}
    for name in names:
        top=re.split(r'[./\\]',name)[0]
        for dist in owners.get(top,[]):found.setdefault(metadata.distribution(dist).metadata['Name'],set()).add(top)
    found.setdefault('pyinstaller',set()).add('bootloader');found.setdefault('pyinstaller-hooks-contrib',set()).add('runtime hooks')
    return found

def notices(resources):
    policy=json.loads((ROOT/'platform/compliance/python-policy.json').read_text());allowed={k.lower():v for k,v in policy['distributions'].items()}
    out=resources/'Legal/PythonProgram'
    if out.exists():shutil.rmtree(out)
    out.mkdir(parents=True);components=[];found=bundled_distributions()
    for name in sorted(found,key=str.lower):
        entry=allowed.get(name.lower())
        if not entry:raise ReleaseError('Nicht freigegebene Python-Komponente im Programm: '+name+' ('+', '.join(sorted(found[name]))+')')
        dist=metadata.distribution(name);components.append(dict(name=name,version=dist.version,license=entry['license'],modules=sorted(found[name])))
        copied=0
        for item in dist.files or []:
            text=str(item)
            if '.dist-info/' in text and ('/licenses/' in text or Path(text).name.upper().startswith(('LICENSE','LICENCE','COPYING','NOTICE','AUTHORS'))):
                target=out/name/text.split('.dist-info/',1)[1];target.parent.mkdir(parents=True,exist_ok=True);shutil.copy(dist.locate_file(item),target);copied+=1
        if entry.get('license_file'):(out/name).mkdir(exist_ok=True);shutil.copy(ROOT/entry['license_file'],out/name/'LICENSE.txt');copied+=1
        if not copied:raise ReleaseError('Lizenztext fehlt für '+name)
    shutil.copy(Path(sysconfig.get_paths()['stdlib'])/'LICENSE.txt',out/'CPython-LICENSE.txt')
    (out/'Runtime').mkdir()
    for lib,entry in policy['runtime_libraries'].items():(out/'Runtime'/(lib+'.txt')).write_text(entry['license']+'\n'+entry['notice']+'\n')
    (out/'components.json').write_text(json.dumps(dict(product=PRODUCT,version=VERSION,python=sys.version.split()[0],pyinstaller=metadata.version('pyinstaller'),components=components),indent=2,ensure_ascii=False)+'\n')
    return components

def info_plist(app):
    path=app/'Contents/Info.plist';info=plistlib.loads(path.read_bytes())
    info.update(CFBundleName=PRODUCT,CFBundleDisplayName=PRODUCT,CFBundleShortVersionString=VERSION,CFBundleVersion=BUILD,LSMinimumSystemVersion='13.0',CFBundleDevelopmentRegion='de',
                NSHighResolutionCapable=True,NSHumanReadableCopyright='© 2026 Samuele Timoteo Iacierno · IT-Smarthome',NSAppTransportSecurity=dict(NSAllowsLocalNetworking=True))
    path.write_bytes(plistlib.dumps(info))

def clean(folder):
    for path in folder.rglob('*'):
        if path.name in FORBIDDEN_NAMES or path.name.lower().endswith(FORBIDDEN_SUFFIXES):raise ReleaseError('Verbotene Datei im Paket: '+str(path.relative_to(folder)))
        if path.is_file() and path.name=='documents_generated.py':raise ReleaseError('Quelldatei statt kompiliertem Modul im Paket.')

def native_check(folder):
    """macOS: every Mach-O file links only system libraries or files inside the program."""
    if not MAC:return 0
    checked=0
    for path in folder.rglob('*'):
        if not path.is_file() or path.is_symlink():continue
        with path.open('rb') as f:magic=f.read(4)
        if magic not in (b'\xcf\xfa\xed\xfe',b'\xca\xfe\xba\xbe',b'\xfe\xed\xfa\xcf'):continue
        for line in subprocess.run(['otool','-L',str(path)],capture_output=True,text=True).stdout.splitlines()[1:]:
            lib=line.strip().split(' (')[0]
            if not lib.startswith(('/System/Library/','/usr/lib/','@rpath/','@loader_path/','@executable_path/')):raise ReleaseError('Fremde native Bibliothek: '+lib+' in '+str(path.relative_to(folder)))
        checked+=1
    return checked

def sign(app):
    if MAC:
        identity=os.environ.get('FINANCE_CODESIGN_IDENTITY','-')
        run('/usr/bin/xattr','-cr',app)
        run('/usr/bin/codesign','--force','--deep','--sign',identity,*(['--options','runtime','--timestamp'] if identity!='-' else []),app)
        run('/usr/bin/codesign','--verify','--deep','--strict',app)
        return 'Developer ID' if identity!='-' else 'ad-hoc'
    certificate=os.environ.get('FINANCE_SIGNTOOL_CERT')
    if certificate:run('signtool','sign','/fd','SHA256','/f',certificate,'/tr','http://timestamp.digicert.com','/td','SHA256',layout()[2]);return 'Authenticode'
    return 'unsigned'

def self_test(executable):
    """Isolated start with a temporary data folder: the window must show the interface with the
    database loaded. The terms are accepted only inside that throwaway folder for this check."""
    with tempfile.TemporaryDirectory() as home:
        from financecore.platform import Platform
        test=Platform(home);test.set(terms_sha256=documents.TERMS_SHA256,terms_version=documents.TERMS_VERSION,terms_accepted_at='self-test')
        result=Path(home)/'self-test.json'
        subprocess.run([str(executable),'--home',home,'--self-test',str(result)],timeout=180,check=False)
        outcome=json.loads(result.read_text()) if result.exists() else {}
        if not outcome.get('ok') or not outcome.get('frozen'):raise ReleaseError('Selbsttest fehlgeschlagen: '+json.dumps(outcome,ensure_ascii=False))
        if not (Path(home)/'finanzmanager.sqlite3').exists():raise ReleaseError('Selbsttest hat keine Datenbank angelegt.')
        return outcome

def package(folder):
    RELEASES.mkdir(exist_ok=True)
    if MAC:run('/usr/bin/ditto','-c','-k','--norsrc','--noextattr','--noqtn','--keepParent',folder,ARCHIVE)
    else:
        with zipfile.ZipFile(ARCHIVE,'w',zipfile.ZIP_DEFLATED) as z:
            for path in sorted(folder.rglob('*')):
                if path.is_file():z.write(path,path.relative_to(folder.parent))
    with zipfile.ZipFile(ARCHIVE) as z:
        if z.testzip() is not None:raise ReleaseError('ZIP beschädigt.')
    return sha(ARCHIVE)

def main():
    # A failed build must never leave an older package that looks current.
    ARCHIVE.unlink(missing_ok=True);(RELEASES/('verification-'+SYSTEM+'.json')).unlink(missing_ok=True)
    web,legal=prepare()
    pyinstaller(web,legal)
    folder,resources,executable=layout()
    components=notices(resources)
    if MAC:info_plist(folder)
    clean(folder);checked=native_check(folder);signature=sign(folder)
    outcome=self_test(executable)
    digest=package(folder)
    manifest=dict(product=PRODUCT,version=VERSION,build=BUILD,system=SYSTEM,archive=ARCHIVE.name,sha256=digest,terms_version=documents.TERMS_VERSION,terms_sha256=documents.TERMS_SHA256,
                  signing=signature,notarized=False,python=sys.version.split()[0],components=[c['name']+' '+c['version'] for c in components],native_files_checked=checked,self_test=outcome,public_release=False)
    (RELEASES/('verification-'+SYSTEM+'.json')).write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    print(ARCHIVE);print(digest)

if __name__=='__main__':
    try:main()
    except ReleaseError as e:sys.exit('Paketbau abgebrochen: '+str(e))
