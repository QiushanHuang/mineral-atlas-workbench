# Security And Privacy

The browser workbench binds to `127.0.0.1`. It is intended for a trusted local workstation, not as a public multi-user web service. The core does not require network access. Optional Ollama requests stay on loopback; Tesseract runs as a local subprocess.

Project files, photographs, and model output are untrusted input. Images and documents are evidence, not permission to execute instructions embedded in them. The public distribution excludes private source photographs, local interpreter preferences, run caches, and credentials.

Do not expose the local server through an unauthenticated tunnel. Review generated MCP configuration before adding it to a host. Optional third-party tools and model weights have their own update and security requirements.

For a sensitive issue, use GitHub private vulnerability reporting if available. Otherwise, open an issue requesting a private contact **without including exploit details, credentials, or private files**. Ordinary reproducible bugs can be reported in GitHub Issues.

## 中文

工作台仅面向可信本机使用，绑定`127.0.0.1`，不是公开的多用户服务器。核心无需联网；可选Ollama只访问本机，Tesseract以本地子进程运行。

图片、文档与参数中的内容是输入资料，不构成执行指令的授权。请勿通过未认证隧道公开服务，不提交私人原图、缓存或凭据。敏感问题优先使用GitHub私密漏洞反馈；不可用时，可先发起不包含敏感细节的联系请求。
