# 📋 U盘迁移操作指南

**时间：2026-05-23
**目的：把E:\CogniCore-Portable完整迁移到F:\CogniCore（U盘）

---

## ✅ 第一步：已完成！
老版本已备份到 `F:\CogniCore_old`

---

## 📋 第二步：手动复制操作指南（请手动执行）

### 方法 1：Windows 资源管理器复制（最简单）

1. 打开文件夹：`E:\CogniCore-Portable`
2. 全选所有文件（Ctrl+A）
3. 复制（Ctrl+C）
4. 打开文件夹：`F:\CogniCore` （若不存在则新建）
5. 粘贴（Ctrl+V）

### 方法 2：管理员 PowerShell（推荐）

以管理员身份运行 PowerShell，执行以下命令：

```powershell
# 复制完整项目到F盘
Copy-Item -Path 'E:\CogniCore-Portable\*' -Destination 'F:\CogniCore' -Recurse -Force

# 验证复制结果
Get-ChildItem 'F:\CogniCore'
```

---

## ✅ 第三步：迁移完成验证

迁移后，在F盘根目录检查：

1. **重要文件是否都在F:\CogniCore？
   - [ ] README.md
   - [ ] SURVIVAL_RESILIENCE_WHITEPAPER.md
   - [ ] FINAL_ACCEPTANCE_PLAYBOOK.md
   - [ ] cognicore/
   - [ ] config/
   - [ ] ... (其他所有文件和文件夹)

2. **启动验证（最重要！）
   进入 `F:\CogniCore\cognicore`，双击运行：
   - `start_portable.bat` （U盘即插即用启动）
   - `start_robust_pipeline.bat` （工业级数据管道测试）

---

## 🎬 第四步：执行终极验收剧本！

F盘迁移完成后，打开：
**[FINAL_ACCEPTANCE_PLAYBOOK.md](file:///F:\CogniCore\FINAL_ACCEPTANCE_PLAYBOOK.md)**
然后按照验收剧本一步步执行！

---

## 📊 迁移前后对比

| 对比项 | 迁移前 | 迁移后 |
|------|------|------|
| 位置 | E:\CogniCore-Portable (本地) | F:\CogniCore (U盘) |
| 老版本 | F:\CogniCore | F:\CogniCore_old (已备份） |
| 新版本 | E:\CogniCore-Portable | F:\CogniCore (新） |

---

## ⚠️ 注意事项

- 若F盘空间不足，请先清理
- 复制过程中请不要中断
- 验证通过后，可删除 F:\CogniCore_old
