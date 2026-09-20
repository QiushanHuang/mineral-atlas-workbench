#!/usr/bin/env python3
"""Use the package core, or the bundled standalone-skill runtime after installation."""
import pathlib,sys,runpy
skill=pathlib.Path(__file__).resolve().parents[1]
candidates=[skill.parents[1],skill/'assets/runtime']
root=next((p for p in candidates if (p/'atlas_cli.py').is_file()),None)
if root is None:raise SystemExit('运行时缺失：请完整解压插件，或使用含assets/runtime的独立skill包。')
sys.path.insert(0,str(root));runpy.run_path(str(root/'atlas_cli.py'),run_name='__main__')
