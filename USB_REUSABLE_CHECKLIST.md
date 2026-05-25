# 📦 F盘老版本可复用资源检查

**检查时间：2026-05-23

---

## ✅ 可复用的高价值资源

### 1. **ollama/ 目录（最有价值！）

**位置：** F:\CogniCore_old\ollama\
**包含：**
- ollama.exe - OLLAMA本地运行时
- (可能包含已下载的模型？)

**价值：** ⭐⭐⭐⭐⭐  
**建议：** 复制到新项目！避免重新下载大模型。

---

### 2. **python/ 目录（备选！）

**位置：** F:\CogniCore_old\python\
**包含：**
- 完整的Python 3.12运行时
- 所有依赖库

**价值：** ⭐⭐⭐  
**说明：** 我们新版本有venv/，但这个可以作为便携Python的备选方案。

---

### 3. **config/ 和 cognicore/config.yaml（配置！）

**位置：** F:\CogniCore_old\config\cognicore.yaml, F:\CogniCore_old\cognicore\config.yaml
**价值：** ⭐⭐⭐⭐  
**建议：** 检查配置，合并到新项目中。

---

### 4. **logs/ （历史日志！）

**位置：** F:\CogniCore_old\logs\
**价值：** ⭐⭐  
**说明：** 可以保留作为参考，但不是必须。

---

## 📋 合并方案建议

### 方案 A：最小化（推荐！）

只复制最重要的：
1. 复制 `F:\CogniCore_old\ollama` → `F:\CogniCore\ollama`
2. 检查并合并配置
3. 保留venv/（新项目已有）

### 方案 B：完整合并

复制所有可复用内容：
1. ollama/ → 保留
2. python/ → 可选保留
3. logs/ → 可选保留
4. config/ → 合并检查

---

## ⚠️ 注意事项

- 新项目已有 `venv/` 虚拟环境，所以 python/ 不是必须
- 优先保留 ollama/，因为模型文件很大，重新下载很慢
