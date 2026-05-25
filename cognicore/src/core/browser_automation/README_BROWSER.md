# PyWJJ 浏览器自动化框架

## 🎯 核心亮点

- **Token极省**：比传统MCP省约4倍
- **按需加载**：只返回页面摘要，不塞全量DOM
- **持久化Cookie**：免重复登录
- **自然语言驱动**：用中文描述操作
- **流程可沉淀**：把踩坑经验固化为Skill
- **0Token模式**：生成独立脚本，完全脱离AI

## 📁 目录结构

```
src/core/browser_automation/
├── __init__.py              # 模块初始化
├── playwright_wrapper.py    # Playwright CLI包装器
├── browser_skill.py         # 浏览器自动化Skill
├── README_BROWSER.md        # 本文档
└── skills/                  # Skill知识库（待实现）
    ├── x_post.md            # X发帖Skill
    └── e_commerce_scrape.md # 电商爬取Skill
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install playwright
playwright install chromium
```

### 2. 在PyWJJ中使用

直接在聊天中说：

```
帮我打开浏览器访问 https://example.com
```

或者使用工具调用：

```python
{
  "tool": "browser_automation",
  "action": "navigate",
  "url": "https://example.com"
}
```

### 3. 生成独立脚本（0Token模式）

```
帮我生成一个浏览器自动化脚本，用于抓取X网站的评论
```

生成的脚本可以独立运行，完全不需要AI。

## 🛠️ Skill系统

### 什么是Skill？

Skill是操作流程的知识沉淀，包含：
- 操作步骤
- CSS选择器
- 避坑指南
- 异常处理

### Skill示例

#### X发帖Skill (`skills/x_post.md`)

```markdown
# X发帖Skill

## 操作步骤
1. 导航到 https://x.com
2. 点击创作按钮 (CSS: [data-testid="ComposeButton"])
3. 填写内容 (CSS: [data-testid="tweetTextarea_0"])
4. 点击发送 (CSS: [data-testid="tweetButtonInline"])

## 避坑指南
- 确保已登录（持久化Cookie会处理）
- 内容长度不能超过280字符
- 发送前检查网络状态

## 异常处理
- 如果按钮点击失败，尝试用JavaScript点击
- 网络超时则重试3次
```

## 📊 工具操作说明

### 支持的操作

| 操作 | 参数 | 说明 |
|------|------|------|
| `launch` | `headed`, `browser` | 启动浏览器 |
| `navigate` | `url` | 导航到URL |
| `click` | `selector` | 点击元素 |
| `fill` | `selector`, `value` | 填写表单 |
| `get_text` | `selector` | 获取文本 |
| `scroll` | `direction`, `amount` | 滚动页面 |
| `execute_script` | `script` | 执行JavaScript |
| `close` | - | 关闭浏览器 |
| `generate_script` | `task_description` | 生成独立脚本 |

### 使用示例

#### 1. 简单导航

```json
{
  "action": "navigate",
  "url": "https://example.com"
}
```

#### 2. 完整工作流

```json
{
  "action": "launch"
}
```

```json
{
  "action": "navigate",
  "url": "https://example.com/login"
}
```

```json
{
  "action": "fill",
  "selector": "#username",
  "value": "your_username"
}
```

```json
{
  "action": "fill",
  "selector": "#password",
  "value": "your_password"
}
```

```json
{
  "action": "click",
  "selector": "#login-button"
}
```

#### 3. 生成脚本

```json
{
  "action": "generate_script",
  "task_description": "抓取电商网站的产品评论"
}
```

## 💡 使用技巧

### 1. 持久化登录态

首次登录后，Cookie会自动保存，下次无需重复登录。

### 2. 选择合适的模式

- **开发调试**：使用 `headed=True`，可见浏览器操作
- **生产环境**：使用 `headed=False`，后台静默运行

### 3. Token优化策略

- 只获取需要的元素，不获取全量DOM
- 截图存本地，不占上下文Token
- 常用流程生成Skill或脚本

## 🔧 高级功能

### 自定义Skill

创建你的专用Skill：

1. 在 `skills/` 目录下创建 `your_skill.md`
2. 描述操作流程、选择器、避坑指南
3. PyWJJ会自动学习和使用

### 脚本模板

生成的脚本包含完整框架，只需填充步骤：

```python
# 在此添加你的自动化步骤
await page.goto("https://example.com")
await page.fill("#username", "your_username")
await page.click("#login-button")
```

## 📚 参考资料

- [Playwright官方文档](https://playwright.dev/python/)
- [CSS选择器教程](https://developer.mozilla.org/zh-CN/docs/Web/CSS/CSS_selectors)
- [XPath教程](https://www.w3schools.com/xml/xpath_intro.asp)

## 🎉 开始使用

现在你可以对PyWJJ说：

```
帮我打开浏览器访问百度
```

然后看看效果吧！
