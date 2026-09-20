#!/usr/bin/env python3
"""Portable MCP bootstrap. Prefer an explicitly selected local interpreter/venv; never download."""
import pathlib,sys,os
root=pathlib.Path(__file__).resolve().parent
choice=os.environ.get('MINERAL_ATLAS_PYTHON')
if not choice and (root/'.atlas-python').is_file():choice=(root/'.atlas-python').read_text().strip()
if not choice:
 for p in [root/'.venv/bin/python',root/'.venv/Scripts/python.exe']:
  if p.is_file():choice=str(p);break
choice=choice or sys.executable
os.execv(choice,[choice,str(root/'atlas_cli.py'),'mcp'])
