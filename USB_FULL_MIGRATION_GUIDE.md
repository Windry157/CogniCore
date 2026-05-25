# 🎯 OpenCode U盘安全迁移操作手册（不破坏原有OpenCode结构！）

**时间：2026-05-23
**目标：把 E:\CogniCore-Portable（完整版本）安全迁移到OpenCode U盘，完全保留原有OpenCode文件不动！

---

## ⚠️ 重要：OpenCode U盘结构说明（必须遵守！）

| F盘内容 | 操作 |
|------|------|
| **OpenCode Desktop Installer.exe** | ❌ 不要移动，不要删除！ |
| **System Volume Information/** | ❌ 系统隐藏文件夹，绝对不要碰！ |
| **CogniCore_old/** | ✅ 这是我们的备份，可以读取 |
| **(新建)CogniCore/** | ⭐ 我们的项目放在这里！新增！ |

---

## 📊 现状

| 路径 | 内容 | 状态 |
|------|------|------|
| **E:\CogniCore-Portable** | 我们完成的最新完整版本！ | ✅ 100%完整！ |
| **F:\CogniCore_old** | F盘原始老版本备份 | ✅ 已安全保存 |
| **F:\OpenCode...** | OpenCode原有文件 | ❌ 不要动！ |
| **F:\CogniCore** | (待创建！目标位置！） | ⏳ 等待创建和迁移 |

---

## 🎬 步骤一：在F盘安全创建新项目文件夹

### 方法：在F盘根目录新建 CogniCore 文件夹

1. 打开F盘
2. 新建文件夹，命名为 `CogniCore`
3. **确认不要**删除或移动OpenCode相关任何文件！

---

## 🎬 步骤二：把完整版本复制到F盘的CogniCore文件夹

### 方法 1：Windows资源管理器（最简单！）

1. 打开 E:\CogniCore-Portable 文件夹
2. **全选所有**（Ctrl+A）
3. **复制**（Ctrl+C）
4. 进入 F:\CogniCore 文件夹（刚才新建的）
5. **粘贴**（Ctrl+V）

### 方法 2：管理员PowerShell复制（可选）

以**管理员身份**打开PowerShell，执行：
```powershell
# 先在F盘创建目标文件夹（如果不存在）
if (!(Test-Path 'F:\CogniCore')) { New-Item -ItemType Directory -Path 'F:\CogniCore' }

# 复制完整项目到F盘的CogniCore文件夹中
Copy-Item -Path 'E:\CogniCore-Portable\*' -Destination 'F:\CogniCore' -Recurse -Force

# 验证是否复制完成
Get-ChildItem 'F:\CogniCore'
```

---

## 🔄 步骤三：合并F盘老版本的重要资源（从CogniCore_old到CogniCore）

F:\CogniCore创建并复制完成后，把以下内容从 `F:\CogniCore_old` 合并过来：

### ⭐⭐⭐⭐⭐ 最重要：复制ollama目录！

**操作：**
```
从：F:\CogniCore_old\ollama
到：F:\CogniCore\ollama
```

**为什么？** 避免重新下载大模型文件，节省大量时间！

---

### ⭐⭐⭐⭐ 检查并合并配置文件

**操作：**
1. 检查 `F:\CogniCore_old\config\cognicore.yaml`
2. 检查 `F:\CogniCore_old\cognicore\config.yaml`
3. 与 `F:\CogniCore\config\cognicore.yaml` 对比
4. 需要的话，手动合并配置项

---

### ⭐⭐ 可选：保留历史日志（需要就复制）

**操作：**
```
从：F:\CogniCore_old\logs
到：F:\CogniCore\logs_old（可选！）
```

---

### ⭐ 可选：保留完整python（新项目已有venv，可忽略）

若需要，可把 `F:\CogniCore_old\python` 复制过来作为备选。

---

## ✅ 步骤四：验证F盘新版本

F盘迁移合并完成后，进行验证：

### 验证 1：文件完整性检查
确认 F:\CogniCore 中有：
- [ ] 所有16+专业.md文档
- [ ] cognicore/start_portable.bat
- [ ] cognicore/start_robust_pipeline.bat
- [ ] cognicore/src/core/cognition/ (等新模块）
- [ ] ollama/（如果合并了的话）

### 验证 2：运行启动测试
进入 `F:\CogniCore\cognicore`，双击运行：
1. 先运行 `start_portable.bat` 测试U盘便携启动
2. 然后按 [FINAL_ACCEPTANCE_PLAYBOOK.md](file:///F:\CogniCore\FINAL_ACCEPTANCE_PLAYBOOK.md) 执行验收剧本！

---

## 📋 快速检查表（执行时用）

| 项 | 完成 | 备注 |
|------|------|------|
| 1. 确认没碰OpenCode和System Volume文件 | ☐ | ✅ 必须！ |
| 2. 在F盘根创建新文件夹 CogniCore | ☐ | |
| 3. 把 E:\CogniCore-Portable 复制到 F:\CogniCore | ☐ | |
| 4. 合并 ollama/ 目录（最重要！） | ☐ | |
| 5. 检查并合并配置（config.yaml） | ☐ | |
| 6. 验证文件完整性 | ☐ | |
| 7. 运行 start_portable.bat 测试 | ☐ | |
| 8. 执行终极验收剧本 | ☐ | |

---

## 🎉 完成后

完成后，您就可以在任何电脑上插入OpenCode U盘，直接使用完整的四层韧性企业级CogniCore-Portable了！同时完全保留OpenCode原有功能！

---

## 📄 配套参考文档

- [USB_MIGRATION_GUIDE.md](file:///E:\CogniCore-Portable\USB_MIGRATION_GUIDE.md) - 基础迁移指南
- [USB_REUSABLE_CHECKLIST.md](file:///E:\CogniCore-Portable\USB_REUSABLE_CHECKLIST.md) - 可复用资源清单
- [FINAL_ACCEPTANCE_PLAYBOOK.md](file:///E:\CogniCore-Portable\FINAL_ACCEPTANCE_PLAYBOOK.md) - 终极验收剧本
