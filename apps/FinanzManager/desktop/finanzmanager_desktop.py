#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Samuele Timoteo Iacierno
"""FinanzManager Pro program window for macOS and Windows.

The web interface under apps/FinanzManager/Web is shown in a pywebview window; storage, file
dialogs and legal documents are provided by FinanceCore in the same process.
"""
from pathlib import Path
import argparse,os,sys

HERE=Path(__file__).resolve().parent
if not getattr(sys,'frozen',False):sys.path.insert(0,str(HERE.parents[2]/'platform/python'))

import webview
from webview.menu import Menu,MenuAction,MenuSeparator
from financecore import PRODUCT,desktop
from financecore.host import FinanceHost
from financecore.platform import Platform

def web_page():
    if getattr(sys,'frozen',False):return (desktop.resources()/'Web/index.html').read_text(encoding='utf-8')
    return desktop.interface(HERE.parent/'Web')

def create(platform,hidden=False):
    host=FinanceHost(platform,webview,web_page)
    window=webview.create_window(PRODUCT+' · IT-Smarthome',html=desktop.page(PRODUCT,'<h1>'+PRODUCT+'</h1><p>Lokalen Datenbestand laden …</p>'),js_api=host,width=1260,height=840,min_size=(600,640),hidden=hidden)
    host.attach(window)
    menu=[Menu('FinanzManager',[MenuAction('Über FinanzManager Pro',host.about),MenuAction('Einstellungen …',host.open_settings),MenuSeparator(),
        MenuAction('Nutzungsbedingungen …',lambda:host.show_document('terms')),MenuAction('Sicherheit & Updates …',lambda:host.show_document('security')),
        MenuAction('Datenschutz …',lambda:host.show_document('privacy')),MenuAction('Impressum …',lambda:host.show_document('imprint')),
        MenuAction('Lizenzen & Komponenten …',lambda:host.show_document('licenses'))])]
    return host,window,menu

def main(argv=None):
    if os.name!='nt':os.umask(0o077)
    parser=argparse.ArgumentParser(description=PRODUCT)
    parser.add_argument('--home',help='Eigener Datenordner (Test, portable Nutzung).')
    parser.add_argument('--self-test',help=argparse.SUPPRESS)
    args=parser.parse_args(argv)
    platform=Platform(root=args.home)
    host,window,menu=create(platform,hidden=bool(args.self_test))
    def begin():
        host.show()
        if args.self_test:desktop.self_test(window,args.self_test)
    webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER']=False;webview.settings['ALLOW_DOWNLOADS']=False
    webview.start(begin,private_mode=False,storage_path=str(platform.root/'webview'),menu=menu)
    platform.close()

if __name__=='__main__':main()
