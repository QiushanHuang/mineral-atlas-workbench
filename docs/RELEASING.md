# Releasing / 发布说明

## Build From A Clean Checkout

```bash
python3 -m unittest discover -s tests
python3 scripts/run_js_checks.py
python3 scripts/build_reference_gallery.py
python3 scripts/release.py --out dist
python3 scripts/verify_release.py dist
```

Run the fitting tests with the pinned optional environment as well. CI performs the core checks across macOS/Linux/Windows and uses a separate fitting job. The packaging job rebuilds from the repository's `verification/` records; it does not require a private `evaluation/` directory.

Release outputs:

- `mineral-atlas-workbench-1.0.0.zip`
- `mineral-face-atlas-skill-2.0.0.zip`
- `release-checksums.json`

The software archive is also the plugin bundle. The skill archive includes a standalone runtime. Both include the project license, author information, documentation, and logo. Private photographs, local interpreter preferences, caches, and development task notes are excluded.

## Version And Publication

Before the next release, update the software version consistently in `atlas/__init__.py`, `plugin.json`, `.codex-plugin/plugin.json`, `CITATION.cff`, both READMEs, `CHANGELOG.md`, and the software archive name in `scripts/release.py`. Change the standalone skill version/archive name only when its own release version changes. Update links and this document accordingly.

Review the staged source and archive contents, confirm CI for the commit being tagged, then create an annotated version tag and a GitHub Release. Attach both ZIPs and the checksums. Do not replace previously published assets silently; publish a new version for a material change.

Check the public release URL, download the attached artifacts, and verify their hashes. A passing local build is not proof that the uploaded assets are complete.

## 中文

先在干净源码中执行上面的检查与打包命令，再使用配准依赖环境运行完整测试。发布脚本从仓库内`verification/`读取基准记录，不依赖私人开发目录。软件包同时也是插件包，独立skill包自带运行时；两者包含许可证、署名、文档与logo。

新版本需同步代码版本、两个插件manifest、引用文件、双语README、更新日志与压缩包名称。确认待发布提交的CI通过后，创建带注释的版本标签并发布GitHub Release，附两份ZIP和校验文件。最后实际下载公开附件核对哈希；不要把“本地测试通过”当作“线上分发完整”。
