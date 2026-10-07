# 威联通 NAS 安装步骤

目标仓库：`https://github.com/fengzhiqiu/ctyun-auto`  
目标镜像：`ghcr.io/fengzhiqiu/ctyun-auto:latest`

**这些步骤需要先将改造文件提交到你的 Fork，并等待 GitHub Actions 首次构建成功。目标地址不表示镜像已经发布。**

## 1. 确认 NAS 和安装 Container Station

在 QTS / QuTS hero 的 App Center 安装 Container Station。推荐使用 Container Station 3。

SSH 执行 `uname -m` 查看架构：

| 结果 | 镜像架构 |
| --- | --- |
| x86_64 | linux/amd64（Intel / AMD） |
| aarch64 | linux/arm64 |
| armv7l / armv6l | 不支持，本项目依赖的基础镜像未提供此架构 |

Docker 会自动选择匹配的架构，不需要强制设置 `platform`。

Chromium 和 OCR 会占用内存，建议 NAS 有至少 2 GB 可用内存，第一次部署先观察资源占用。

## 2. 构建并取得镜像

1. Fork [上游仓库](https://github.com/bytehola/ctyun-auto/fork) 到 `fengzhiqiu`。
2. 将改造文件提交到 Fork 的 `main`。
3. 打开仓库 Actions。如果 Fork 提示工作流被禁用，点击启用工作流。
4. 选择 **Build and publish Docker image**，必要时点击 **Run workflow**，选择 `main`。
5. 等待两个架构的 Build and test 和 Publish multi-platform manifest 全部成功。

构建使用 `GITHUB_TOKEN`，不用添加天翼账号、密码或 Docker Hub Token。若提示 `permission_denied: write_package`，检查仓库 Actions 权限和包的 Actions access；工作流已经声明 `packages: write`。已有同名 GHCR 包时，确认它允许这个仓库发布。

GHCR 的新包默认私有，与仓库是否公开是两个设置。[GitHub 官方说明](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)

可以选择：

- **私有镜像**：在 GitHub 创建只有 `read:packages` 权限的 PAT classic，在 NAS 执行 `docker login ghcr.io -u fengzhiqiu`，提示 Password 时输入 Token。不要填写 GitHub 登录密码。通过 Container Station 拉取时，还需在它的 Registries 页面添加 `ghcr.io` 并填写用户名和 Token。
- **公开镜像**：在个人主页 Packages 打开 `ctyun-auto` → Package settings → Change visibility → Public。镜像不包含天翼账号配置，公开后 NAS 可匿名拉取。

## 3. 准备 NAS 本地文件

先在 File Station 创建一个持久目录，例如共享文件夹 `Container` 下的 `ctyun-auto/data`。确认实际路径：以下示例使用 `/share/Container/ctyun-auto`，你的共享文件夹名字可能不同。

从改造仓库或交付 ZIP 取出 `compose.yaml` 和 `.env.example`，放到该目录，复制 `.env.example` 为 `.env` 并编辑：

```dotenv
APP_USER=你的天翼账号
APP_PASSWORD='你的天翼密码'
DEVICECODE=
LOGIN_CRON='0 3,20 * * *'
PC_CRON='0 4,6 * * *'
CTYUN_IMAGE=ghcr.io/fengzhiqiu/ctyun-auto:latest
HOST_DATA_DIR=/share/Container/ctyun-auto/data
```

密码使用单引号可保留 `$` 字符；若密码本身含单引号，按 Compose 的 .env 转义语法使用 `\'`。不要把实际 `.env` 提交到 GitHub。首次生成的设备码会保存在 data 中，后续不要随意更换。如果已有绑定过的 `DEVICECODE`，可以填入原值。

使用普通文本编辑器保存 UTF-8 文件。通过 SSH 进入目录后执行：

```sh
cd /share/Container/ctyun-auto
chmod 600 .env
mkdir -p data
chmod 700 data
```

如果 HOST_DATA_DIR 使用其他路径，也应在该实际路径创建目录并限制访问。

## 4. 首次登录和短信绑定（推荐 SSH）

在 NAS 控制面板 → 网络和文件服务 → Telnet / SSH 中启用 SSH，使用有权操作 Container Station 的 NAS 管理员账号连接。

确认 `docker version` 和 `docker compose version` 可用。某些旧版只有 `docker-compose`，后续将 `docker compose` 替换为 `docker-compose`。若找不到 Docker 命令，在 NAS 上查看 `/etc/config/qpkg.conf` 的 Container Station 安装目录；常见 Docker 所在位置为该目录下的 `bin`，将实际目录加入当前会话的 PATH。不同 QTS / Container Station 版本路径可能不同。

在配置目录执行：

```sh
docker compose pull
docker compose run --rm --no-deps ctyun --init
```

这会打开首次绑定专用的前台容器。若要求短信验证码，直接输入并回车；看到“保活任务启动”或明确的保活日志后，按 **Ctrl+C** 结束初始化。设备标识及程序写入的登录数据保留在 NAS 的 data 目录中。

然后启动后台容器：

```sh
docker compose up -d
docker compose logs -f --tail=100 ctyun
```

查看日志时按 Ctrl+C 只会停止日志跟随。不要让首次初始化容器与正式后台容器同时使用同一个账号。

如果后来再次要求短信验证：先 `docker compose stop`，重新执行 `docker compose run --rm --no-deps ctyun --init`，完成后再 `docker compose up -d`。

首次安装后可手动运行积分任务：

```sh
docker exec -it ctyun-auto python /app/run_job.py login
docker exec -it ctyun-auto python /app/run_job.py pc
```

挂机任务可能运行约 80 分钟；保持 SSH 会话直到结束，或等待自动定时任务。看到锁提示表示同一种任务已在运行，请等它结束再操作。

## 5. Container Station 图形界面部署（另一种方式）

如果使用上一节的 Compose 后台容器，就无需再次创建应用。以下方式适合希望用图形界面管理应用的用户：

1. 完成第 3 节的配置和第 4 节的首次绑定，仅执行初始化，不执行 `docker compose up -d`。
2. 打开 Container Station → **Applications / 应用程序** → **Create / 创建**，应用名称填 `ctyun-auto`。
3. 粘贴仓库 `deploy/qnap-compose.yaml` 的内容。
4. 将 `APP_USER`、`APP_PASSWORD` 换为实际值；将 volume 左侧的 NAS 路径改为第 3 节相同的数据目录。
5. 密码若含 `$`，在此 YAML 中写为 `$$`，避免 Compose 将它解释为变量。若含引号或反斜杠，正确使用 YAML 引号转义。
6. 如果第 3 节手动填写了 DEVICECODE，也把相同值加到 environment；留空生成的设备码已在数据目录中，无需再填写。
7. 点击 **Validate / 验证**，再点击 **Create / 创建**，查看应用及容器日志。

这里的模板直接填写环境变量，不依赖 Container Station 自动读取外部 `.env`。数据路径必须与初始化时相同；否则会生成新设备码并可能再次短信验证。

程序没有 Web 管理页面，无需设置 Default Web URL Port、发布端口或特权模式。外出访问天翼服务使用默认容器网络即可。

菜单和创建流程可参考 [QNAP Container Station 3 官方指南](https://www.qnap.com/en/how-to/tutorial/article/how-to-use-container-station-3)。

## 6. 定时任务与自动兑换

默认时区固定为北京时间：

| 任务 | 默认时间 |
| --- | --- |
| AI 对话积分 | 每天 03:00、20:00 |
| 云电脑挂机积分 | 每天 04:00、06:00 |
| 保活 | 持续运行，沿用上游的定时重启逻辑 |

要修改时间，编辑 .env 的 LOGIN_CRON / PC_CRON，然后 `docker compose up -d --force-recreate`；图形界面则编辑应用 YAML 并 Recreate。**只修改 .env 然后 restart 不会更新容器环境。**

自动兑换需要主动配置，运行：

```sh
docker exec -it ctyun-auto python /app/run_job.py pc --config-redeem
```

按提示选择是否启用、奖励和兑换日期；可选每月最后一天。配置保存到 `data/redeem_config.json`。配置时若挂机任务正在运行，文件锁会阻止重复启动，等任务结束再配置。

如果迁移旧容器，它的兑换配置可能在未挂载的 `/app/redeem_config.json`；**删除旧容器前**用 `docker cp 旧容器名:/app/redeem_config.json /实际数据目录/redeem_config.json` 复制，再备份原数据目录。

## 7. 更新、回退和备份

新的 main 提交成功构建后，SSH/Compose 部署运行：

```sh
docker compose pull
docker compose up -d
docker compose logs --tail=100 ctyun
```

图形界面部署在 Images 中 Pull 新镜像，再在应用详情中 Recreate，保持同一个宿主机数据路径。单纯 Restart 不会替换镜像。

需要固定版本时，将镜像改为 `ghcr.io/fengzhiqiu/ctyun-auto:sha-<12位提交号>` 或已发布的 `v1.0.0` 等标签；回退时恢复旧镜像标签后重新创建容器。

备份 `.env` 和整个 data 目录。data 包含登录凭证和截图，应保存到仅管理员可访问的位置。多个账号使用多个容器和不同的宿主机数据目录。

## 8. 故障排查

| 现象 | 处理 |
| --- | --- |
| manifest unknown | 检查首次 Actions 是否成功，镜像用户名和标签是否正确 |
| denied / unauthorized | 镜像为私有；用 PAT classic 的 read:packages 登录，或把包改为 Public |
| no matching manifest / exec format error | 核对 uname -m；32 位 ARM 不支持；确认双架构发布完成 |
| pull 超时 | NAS 必须能访问 ghcr.io；检查 DNS、路由、网络代理，或在相同架构的其他 Docker 机器 pull + save，再通过 Container Station Import 导入 |
| 缺少 APP_USER / APP_PASSWORD | 确认 .env 或 GUI 的 environment 已填写，随后重新创建容器 |
| 数据目录 Permission denied | 检查共享文件夹实际路径、挂载是否可写以及 NAS ACL |
| 短信验证码无法输入 | 停止后台容器，按第 4 节进入 --init 前台绑定模式 |
| cron 未启动 / unhealthy | 查看 docker logs；健康检查只检查 cron 服务，不检查登录成功 |
| 没有获得积分 | 检查对应任务日志和天翼网页是否变化；积分数量取决于服务端规则 |
| Chromium 启动失败或被杀 | 检查 NAS 剩余内存与资源限制，保留模板中的共享内存配置 |
| 兑换配置重建后消失 | 检查 /app/data 是否始终绑定同一目录；旧版配置要先复制出来 |

离线导入时，另一台可联网的 Docker 机器指定你的 NAS 对应架构：

```sh
docker pull --platform linux/amd64 ghcr.io/fengzhiqiu/ctyun-auto:latest
docker save -o ctyun-auto.tar ghcr.io/fengzhiqiu/ctyun-auto:latest
```

ARM64 NAS 将 linux/amd64 改为 linux/arm64。上传 tar 后在 Container Station → Images → Import 导入，再使用相同镜像标签创建应用。

官方参考：[QNAP 镜像导入与应用管理](https://www.qnap.com/en/how-to/tutorial/article/how-to-use-container-station-3)、[Docker 双架构构建](https://docs.docker.com/build/ci/github-actions/multi-platform/)。
