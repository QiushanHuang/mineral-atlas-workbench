"""Print machine-local MCP configuration or a Codex command; changes no client settings."""
import pathlib,sys,json,argparse,shlex
root=pathlib.Path(__file__).resolve().parents[1];p=argparse.ArgumentParser();p.add_argument('--codex-command',action='store_true');a=p.parse_args()
if a.codex_command:print(shlex.join(['codex','mcp','add','mineral-atlas','--',sys.executable,str(root/'atlas_cli.py'),'mcp']))
else:print(json.dumps({'mcpServers':{'mineral-atlas':{'command':sys.executable,'args':[str(root/'atlas_cli.py'),'mcp'],'cwd':str(root)}}},ensure_ascii=False,indent=2))
