# CI/CD 维护和监控指南 - bayesian-agi-core

## 📊 监控仪表盘

**实时查看 CI/CD 状态**: https://github.com/Windry157/bayesian-agi-core/actions

---

## 🛡️ 自动更新方案

### 方案一：使用 Dependabot（推荐）

创建 `.github/dependabot.yml` 文件，自动监控和更新 actions：

```yaml
version: 2
updates:
  # GitHub Actions 自动更新
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "09:00"
    open-pull-requests-limit: 10
    reviewers:
      - "Windry157"
    assignees:
      - "Windry157"
    labels:
      - "dependencies"
      - "github-actions"

  # Python 依赖自动更新
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "wednesday"
      time: "09:00"
    open-pull-requests-limit: 5
    reviewers:
      - "Windry157"
    labels:
      - "dependencies"
      - "python"
```

---

## 📅 定期检查清单

### 每周检查（周一）
- [ ] 查看 Actions 页面：https://github.com/Windry157/bayesian-agi-core/actions
- [ ] 检查是否有失败的工作流
- [ ] 检查 Dependabot 自动更新 PR
- [ ] 检查 Node.js actions 版本警告

### 每月检查（1号）
- [ ] 审查所有 workflows 配置
- [ ] 检查是否有新的 GitHub Actions 版本
- [ ] 更新依赖包到稳定版本
- [ ] 清理旧的 workflow 运行记录

---

## 🔔 告警配置

### GitHub 通知设置

1. 访问：https://github.com/settings/notifications
2. 启用以下通知：
   - ✅ Actions 工作流失败
   - ✅ Pull Request 分配给你
   - ✅ 评论和提及
   - ✅ 安全警报

---

## 📝 常见问题和快速修复

### 问题 1：Node.js 20 actions 已弃用警告

**症状**: CI/CD 页面显示黄色警告
**快速修复**: 更新 actions 到最新版本
**相关文件**: `.github/workflows/ci.yml`

### 问题 2：Test Job 失败

**症状**: `exit code 1`
**快速修复**:
1. 查看详细日志：点击 Actions → 失败的 run → 查看失败步骤
2. 可能原因：
   - 测试失败 → 修复测试
   - 依赖问题 → 更新 `requirements.txt`
   - lint/format 错误 → 运行 `black src/ tests/` 和 `isort src/ tests/`

### 问题 3：Build Job 失败

**症状**: Docker 构建失败
**快速修复**:
1. 检查 Dockerfile
2. 检查 `requirements.txt` 依赖版本兼容性

---

## 🚀 快速修复流程

### 当 CI/CD 失败时

1. **立即查看**：访问 https://github.com/Windry157/bayesian-agi-core/actions
2. **查看详情**：点击失败的工作流 → 点击失败的步骤查看日志
3. **定位问题**：根据错误信息判断问题类型
4. **修复问题**：
   - Actions 版本问题 → 更新 `.github/workflows/ci.yml`
   - 代码问题 → 修复代码
   - 依赖问题 → 更新 `requirements.txt`
5. **提交修复**：提交并推送修复
6. **验证**：查看 Actions 重新运行是否成功

---

## 📚 相关资源

- **GitHub Actions 官方文档**: https://docs.github.com/en/actions
- **Actions 版本监控**: https://github.com/marketplace?type=actions
- **Dependabot 文档**: https://docs.github.com/en/code-security/dependabot
- **CI/CD 失败历史**: https://github.com/Windry157/bayesian-agi-core/actions

---

## 🎯 最佳实践

1. **小步迭代**：不要一次更新太多依赖，分开提交
2. **立即修复**：CI/CD 失败后 24 小时内修复
3. **备份配置**：修改 workflow 前先备份当前配置
4. **测试修改**：本地测试后再提交到远程仓库
