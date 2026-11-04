# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Samuele Timoteo Iacierno
"""Legal documents shown in the program, generated from platform/terms.

The texts are embedded at build time (documents_generated.py), so the program shows exactly the
version whose checksum the user confirms. Without a build the files are read directly.
"""
from pathlib import Path
import hashlib,re

FILES={'terms':'FinanzManager.md','privacy':'Datenschutz.md','imprint':'Impressum.md','licenses':'Komponenten.md','security':'Sicherheit.md'}
TITLES={'terms':'Nutzungsbedingungen','privacy':'Datenschutz','imprint':'Impressum','licenses':'Lizenzen & Komponenten','security':'Sicherheit & Updates'}

def read_sources(folder):
    return {key:(Path(folder)/name).read_text(encoding='utf-8') for key,name in FILES.items()}

try:
    from .documents_generated import DOCUMENTS
except ImportError:
    DOCUMENTS=read_sources(Path(__file__).resolve().parents[2]/'terms')

def terms_version(text):
    found=re.search(r'^Fassung (\S+)',text,re.M)
    return found.group(1) if found else ''

TERMS_SHA256=hashlib.sha256(DOCUMENTS['terms'].encode()).hexdigest()
TERMS_VERSION=terms_version(DOCUMENTS['terms'])

def generate(folder,target):
    """Writes documents_generated.py from the Markdown sources (build step)."""
    documents=read_sources(folder)
    Path(target).write_text('# Generated from platform/terms by scripts/build.py. Do not edit.\nDOCUMENTS='+repr(documents)+'\n',encoding='utf-8')
    return documents
