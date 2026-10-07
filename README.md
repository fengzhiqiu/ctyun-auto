# 天翼云电脑：GitHub Actions 镜像与威联通部署

基于 [bytehola/ctyun-auto](https://github.com/bytehola/ctyun-auto) 改造。保留云电脑保活、AI 对话积分、云电脑挂机积分和可选自动兑换功能。实际积分与登录效果取决于天翼服务端。

本版本由 GitHub Actions 构建 Docker 镜像，NAS 直接拉取镜像，无需在 NAS 安装 Python 或构建 Chromium。

## 镜像

目标镜像：`ghcr.io/fengzhiqiu/ctyun-auto:latest`。**先确认 Actions 首次构建成功，再拉取镜像。**

- `main` 提交：构建、离线测试并发布 `latest` 和 `sha-<12位提交号>`。
- `v1.0.0` 等版本标签：发布对应版本和提交号标签，不覆盖 `latest`。
- Pull Request：仅构建和测试，不发布。
- Actions 页面支持手动运行；发布时请选择 `main`。
- 原生 `linux/amd64`、`linux/arm64` 构建；32 位 ARM 不支持。
- 使用仓库自带 `GITHUB_TOKEN` 发布，无需配置 Docker Hub 密码或天翼账号 Secrets。
- GHCR 新镜像默认私有；NAS 需登录，或由仓库所有者将镜像包改为 Public。

## 威联通 NAS 安装

请看完整 [威联通部署说明](docs/QNAP.md)，包含 Container Station、SSH 首次短信绑定、更新和故障排查。

SSH 快速流程（在存放 `compose.yaml` 和 `.env` 的目录内执行）：

```sh
cp .env.example .env
# 在 NAS 上编辑 .env：填写账号、密码和 HOST_DATA_DIR。
chmod 600 .env
docker compose pull
docker compose run --rm --no-deps ctyun --init
# 完成短信验证、看到保活启动后按 Ctrl+C 退出初始化。
docker compose up -d
docker compose logs -f
```

账户密码只填写在 NAS 本地 `.env` 或 Container Station 的容器配置中。数据目录映射至 `/app/data`，持久保存设备码、Cookie、登录状态和兑换设置。容器启动会自动生成稳定设备码。无需发布端口。

默认北京时间每天 03:00、20:00 执行 AI 对话任务，04:00、06:00 执行挂机任务；可用 `LOGIN_CRON`、`PC_CRON` 调整。后台任务不会自动开启兑换；启用方式见部署说明。

## 运行与验证

- cron 环境通过受限权限的 JSON 文件传递，密码中的引号、空格和美元符号不会被 shell 解释。
- 每种积分任务使用独立文件锁，避免同一种任务重复启动；Chromium 使用独立调试端口。
- 镜像使用 Python 虚拟环境；兑换配置持久化到 `/app/data/redeem_config.json`。
- `tini` 管理信号与子进程，支持正常停止和首次交互初始化。
- 默认日志最多保留三个 10 MB 文件；健康检查检测 cron 进程，不代表账号登录或积分任务成功。
- Actions 发布前在每种架构执行 .NET、OCR 和 Chromium 的离线冒烟检查，不登录天翼。

本地基础验证：

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q app
bash -n app/entrypoint.sh deploy.sh deploy_cron.sh
```

可选本地构建：`docker build -t ctyun-auto:local ./app`，然后在 `.env` 设置 `CTYUN_IMAGE=ctyun-auto:local`。原 `deploy.sh`、`deploy_cron.sh` 保留为本地构建方式；NAS 建议使用预构建镜像。旧的自定义脚本路径不适用于新的 cron 包装器。

## 文件

```text
.github/workflows/docker.yml  # 双架构构建、验证、发布 GHCR
compose.yaml                 # SSH/Compose 部署
.env.example                 # NAS 本地配置模板
deploy/qnap-compose.yaml     # Container Station 可粘贴模板
docs/QNAP.md                 # 威联通安装、更新与排错
app/Dockerfile               # 保活基础镜像 + Python + Chromium + cron
app/configure_runtime.py     # 设备码、运行环境与 cron 配置
app/run_job.py               # 任务环境与防重复运行
app/entrypoint.sh            # 首次绑定与保活进程管理
app/smoke_test.py            # 无账号离线镜像检查
tests/test_runtime.py        # cron、密码与持久化测试
```

## 来源

保活程序来自 [leleji/CtYun](https://github.com/leleji/CtYun)，沿用其发布的 [su3817807/ctyun:1.1.5](https://hub.docker.com/r/su3817807/ctyun/tags) 基础镜像。验证码识别依赖 [sml2h3/ddddocr](https://github.com/sml2h3/ddddocr)。上游项目的署名与来源保留。
