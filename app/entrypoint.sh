#!/bin/bash
set -euo pipefail
umask 077

python /app/configure_runtime.py
export DEVICECODE
DEVICECODE=$(python -c 'import json; print(json.load(open("/run/ctyun/environment.json"))["DEVICECODE"])')

# Debian cron follows /etc/localtime rather than TZ from an individual job.
ln -snf "/usr/share/zoneinfo/${TZ:-Asia/Shanghai}" /etc/localtime
printf '%s\n' "${TZ:-Asia/Shanghai}" > /etc/timezone
cd /app

if [ "${1:-}" = "--init" ]; then
    echo "[*] 首次设备绑定模式；完成短信验证并看到保活启动后按 Ctrl+C 退出。"
    exec dotnet CtYun.dll
fi
if [ "$#" -ne 0 ]; then
    echo "[!] 未知参数。首次设备绑定请使用 --init。"
    exit 1
fi

RESTART_AT_FILE="/tmp/ctyun_restart_at"
/usr/sbin/cron
echo "[*] Cron 定时服务已启动。"
trap 'exit 0' TERM INT

set +e
echo "[*] 启动进程守护模式..."
should_restart_ctyun_now() {
    if [ ! -f "$RESTART_AT_FILE" ]; then
        return 1
    fi

    local restart_at
    restart_at=$(tr -d '[:space:]' < "$RESTART_AT_FILE" 2>/dev/null)
    if ! [[ "$restart_at" =~ ^[0-9]+$ ]]; then
        echo "[!] 检测到无效的重启计划文件，已忽略并清理。"
        rm -f "$RESTART_AT_FILE"
        return 1
    fi

    local now
    now=$(date +%s)
    [ "$now" -ge "$restart_at" ]
}

run_ctyun_with_watch() {
    local duration="$1"
    local scheduled_restart=0

    timeout --foreground "$duration" dotnet CtYun.dll <&0 &
    local timeout_pid=$!

    while kill -0 "$timeout_pid" 2>/dev/null; do
        if ! pgrep -x cron >/dev/null; then
            echo "[!] Cron 服务已退出，停止容器以便重启策略恢复。"
            exit 1
        fi
        if should_restart_ctyun_now; then
            echo "[*] 检测到兑换成功后的重启计划已到时，准备重启 CtYun.dll。"
            scheduled_restart=1
            rm -f "$RESTART_AT_FILE"
            kill "$timeout_pid" 2>/dev/null || true
            sleep 1
            pkill -f "dotnet CtYun.dll" 2>/dev/null || true
            break
        fi
        sleep 2
    done

    wait "$timeout_pid"
    local exit_code=$?
    if [ "$scheduled_restart" -eq 1 ]; then
        return 200
    fi
    return "$exit_code"
}

# 开启无限循环，接管程序的生命周期
while true; do
    if ! pgrep -x cron >/dev/null; then
        echo "[!] Cron 服务已退出，停止容器以便重启策略恢复。"
        exit 1
    fi
    echo "======================================================"
    echo "[*] 启动 CtYun.dll..."
    run_ctyun_with_watch 2m
    sleep 10
    run_ctyun_with_watch 24h

    # 获取上方进程退出时的状态码
    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 200 ]; then
        echo "[*] 已按兑换计划完成重启。"
    elif [ $EXIT_CODE -eq 124 ]; then
        echo "[!] 触发定时机制：程序已连续运行 24 小时，执行强制重启。"
    else
        echo "[!] CtYun.dll 进程已退出 (退出码: $EXIT_CODE)。可能正在等待开机或发生了异常。"
    fi

    echo "[*] 容器挂起中，将在 2 分钟 (120秒) 后重新启动程序，请等待..."
    sleep 120

done
