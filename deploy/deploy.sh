#!/usr/bin/env bash
# 流谱站点部署：把仓库三个目录摆成运行时可用的形态并重启服务
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
RUN="${FLOWSCORE_RUN:-$HOME/flowscore-site}"
mkdir -p "$RUN"
cp -r "$REPO/site/." "$RUN/"
rm -rf "$RUN/generator" "$RUN/library"
cp -r "$REPO/generator" "$RUN/generator"
cp -r "$REPO/library"   "$RUN/library"
# 站点页面里引用的是 orchestrator/ 与 library/
rm -rf "$RUN/orchestrator"; ln -sfn generator "$RUN/orchestrator"
ln -sfn library/registry.json "$RUN/registry.json"
echo "✓ 已部署到 $RUN"
echo "  重启：systemctl --user restart flowscore-site"
