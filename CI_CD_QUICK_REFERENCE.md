# 🚀 CI/CD 快速参考卡

## 📊 实时监控
- **仪表盘**: https://github.com/Windry157/bayesian-agi-core/actions
- **失败列表**: https://github.com/Windry157/bayesian-agi-core/actions?query=is%3Afailure
- **Dependabot PR**: https://github.com/Windry157/bayesian-agi-core/pulls

## ⚡ 快速修复流程

### 当 CI/CD 失败时
1. 查看失败详情 → 点击 Actions → 失败的 run
2. 根据错误类型修复
3. 提交并推送
4. 验证重新运行成功

### 常见错误修复

| 错误 | 快速修复 |
|------|----------|
| Node.js 20 actions 弃用 | 更新 actions 到最新版本 |
| Test Job exit code 1 | 查看日志，修复测试/添加容错 |
| Lint 失败 | 运行 `black src/ tests/` 和 `isort src/ tests/` |

## 🔧 自动更新方案

### 安装 Dependabot（推荐）
```powershell
# 1. 复制配置
Copy-Item "e:\CogniCore-Portable\DEPENDABOT.yml" "e:\bayesian-agi-core\.github\dependabot.yml"

# 2. 提交
cd "e:\bayesian-agi-core"
git add .github/dependabot.yml
git commit -m "chore: add Dependabot config for auto-updates"
git push origin master
```

## 📁 修复文件位置
- **修复配置**: [CI_CD_FIX_ci.yml](file:///e:/CogniCore-Portable/CI_CD_FIX_ci.yml)
- **维护指南**: [CI_CD_MAINTENANCE_GUIDE.md](file:///e:/CogniCore-Portable/CI_CD_MAINTENANCE_GUIDE.md)
- **监控工具**: [ci-monitor.ps1](file:///e:/CogniCore-Portable/ci-monitor.ps1)
- **Dependabot 配置**: [DEPENDABOT.yml](file:///e:/CogniCore-Portable/DEPENDABOT.yml)

## 📅 定期检查
- **每周一**: 检查 Actions 和 Dependabot
- **每月1号**: 全面审查配置和更新依赖
