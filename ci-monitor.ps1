# CI/CD 监控和告警脚本

# ============================================================
# 使用说明
# ============================================================
# 这个脚本帮助您快速检查 CI/CD 状态
# 运行前请确保已安装必要的工具（curl, jq 等）
# ============================================================

# ============================================================
# 1. 快速检查 CI/CD 状态（浏览器打开）
# ============================================================
function check-ci-status {
    echo "正在打开 CI/CD 仪表盘..."
    start "https://github.com/Windry157/bayesian-agi-core/actions"
}

# ============================================================
# 2. 快速访问最新的失败工作流
# ============================================================
function check-failed-workflows {
    echo "正在打开失败的工作流..."
    start "https://github.com/Windry157/bayesian-agi-core/actions?query=is%3Afailure"
}

# ============================================================
# 3. 打开 Dependabot 更新页面
# ============================================================
function check-dependabot {
    echo "正在打开 Dependabot 更新..."
    start "https://github.com/Windry157/bayesian-agi-core/pulls"
}

# ============================================================
# 4. 完整的 CI/CD 检查流程
# ============================================================
function ci-health-check {
    echo "========================================"
    echo "  CI/CD 健康检查"
    echo "========================================"
    echo ""
    echo "[1/4] 打开 Actions 仪表盘..."
    start "https://github.com/Windry157/bayesian-agi-core/actions"
    
    echo "[2/4] 打开失败工作流列表..."
    start "https://github.com/Windry157/bayesian-agi-core/actions?query=is%3Afailure"
    
    echo "[3/4] 打开 Dependabot PR..."
    start "https://github.com/Windry157/bayesian-agi-core/pulls"
    
    echo "[4/4] 打开通知设置..."
    start "https://github.com/settings/notifications"
    
    echo ""
    echo "✅ 检查完成！请查看浏览器中打开的标签页"
    echo ""
}

# ============================================================
# 5. 安装 Dependabot 配置文件
# ============================================================
function install-dependabot {
    echo "正在安装 Dependabot 配置..."
    
    if [ -d "e:\\bayesian-agi-core\\.github" ]; then
        Copy-Item "e:\\CogniCore-Portable\\DEPENDABOT.yml" "e:\\bayesian-agi-core\\.github\\dependabot.yml"
        
        echo "✅ Dependabot 配置已安装！"
        echo ""
        echo "下一步："
        echo "1. cd e:\\bayesian-agi-core"
        echo "2. git add .github/dependabot.yml"
        echo "3. git commit -m 'chore: add Dependabot config for auto-updates'"
        echo "4. git push origin master"
    else
        echo "❌ 请先克隆仓库到 e:\\bayesian-agi-core"
    fi
}

# ============================================================
# 显示帮助信息
# ============================================================
function show-help {
    echo "========================================"
    echo "  CI/CD 监控和修复工具"
    echo "========================================"
    echo ""
    echo "可用命令："
    echo ""
    echo "  check-ci-status        - 打开 CI/CD 仪表盘"
    echo "  check-failed-workflows - 查看失败的工作流"
    echo "  check-dependabot       - 查看 Dependabot 更新"
    echo "  ci-health-check        - 完整健康检查"
    echo "  install-dependabot     - 安装 Dependabot 配置"
    echo ""
    echo "使用方法："
    echo "  . .\ci-monitor.ps1"
    echo "  然后运行上述命令"
    echo ""
}

# ============================================================
# 主程序
# ============================================================
if ($MyInvocation.InvocationName -ne ".") {
    show-help
} else {
    echo "✅ CI/CD 监控工具已加载！"
    echo "输入 show-help 查看可用命令"
}
