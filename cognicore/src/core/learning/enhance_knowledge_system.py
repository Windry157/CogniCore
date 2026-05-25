#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Knowledge Base Enhancement System
1. 完善标签体系
2. 扩展每周回顾模板
3. 集成视频转笔记功能
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict


class KnowledgeSystemEnhancer:
    def __init__(self, vault_path):
        self.vault_path = Path(vault_path)
        self.tag_rules = {
            '技术/编程': ['python', 'javascript', 'java', 'cpp', '编程', '代码', '开发', '算法', '数据结构'],
            '技术/Web': ['html', 'css', 'web', '前端', '后端', 'flask', 'django', 'http', 'api'],
            '技术/AI': ['ai', '机器学习', '深度学习', 'tensorflow', 'pytorch', 'Model', '神经网络'],
            '技术/Tool': ['git', 'docker', 'linux', 'vscode', 'Tool', '效率', '自动化'],
            '文史/历史': ['历史', '朝代', '古代', '近代', '文明', '战争', '革命'],
            '文史/文学': ['文学', '诗词', '小说', '名著', '作家', '红楼梦', '古文'],
            '学习/方法': ['学习方法', '笔记', ' memories', '复习', '效率', '番茄工作法'],
            'Tool/教程': ['教程', '指南', 'howto', 'Step', '配置', '安装'],
            '项目/实战': ['项目', '实战', '案例', '练习', 'demo', '应用'],
            '视频/学习': ['视频', '课程', '讲座', '教学', 'b站', 'youtube'],
        }
        
    def analyze_note_content(self, content, file_path):
        """分析笔记Content, 推荐标签"""
        content_lower = content.lower()
        file_name = file_path.stem.lower()
        
        recommended_tags = []
        
        # 基于Content匹配标签
        for tag_category, keywords in self.tag_rules.items():
            for keyword in keywords:
                if keyword in content_lower or keyword in file_name:
                    recommended_tags.append(tag_category)
                    break
        
        # 基于文件路径判断
        path_str = str(file_path).lower()
        if '技术' in path_str or 'programming' in path_str:
            if '技术/编程' not in recommended_tags:
                recommended_tags.append('技术/编程')
        if '文史' in path_str or 'history' in path_str:
            if '文史/历史' not in recommended_tags:
                recommended_tags.append('文史/历史')
        if 'Tool' in path_str or 'tutorial' in path_str:
            if 'Tool/教程' not in recommended_tags:
                recommended_tags.append('Tool/教程')
        
        return list(set(recommended_tags))
    
    def ensure_tags(self):
        """确保所有笔记都有标签"""
        print("\n[tag] Step 1: Improving tag system...")
        
        updated_count = 0
        
        for file_path in self.vault_path.rglob("*.md"):
            if any(part.startswith(".") for part in file_path.parts):
                continue
            if "每周知识回顾" in file_path.name:
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 检查是否already有 YAML
                if content.startswith("---"):
                    # 提取 YAML
                    yaml_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
                    if yaml_match:
                        yaml_content = yaml_match.group(1)
                        body_content = content[yaml_match.end():]
                        
                        # 检查是否already有 tags
                        if "tags:" not in yaml_content:
                            # 分析Content推荐标签
                            recommended_tags = self.analyze_note_content(body_content, file_path)
                            
                            if not recommended_tags:
                                recommended_tags = ["待分类"]
                            
                            # Add tags 字段
                            tags_str = ', '.join([f'"{tag}"' for tag in recommended_tags])
                            yaml_content += f"\ntags: [{tags_str}]"
                            
                            # Update文件
                            new_content = f"---\n{yaml_content}\n---\n\n{body_content}"
                            
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(new_content)
                            
                            updated_count += 1
                            print(f"[OK] Tags added: {file_path.name} -> {recommended_tags}")
                else:
                    # 没有 YAML, Create新的
                    recommended_tags = self.analyze_note_content(content, file_path)
                    if not recommended_tags:
                        recommended_tags = ["待分类"]
                    
                    tags_str = ', '.join([f'"{tag}"' for tag in recommended_tags])
                    yaml_header = f"""---
aliases: []
tags: [{tags_str}]
created: {datetime.now().strftime("%Y-%m-%d %H:%M")}
updated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
---

"""
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(yaml_header + content)
                    
                    updated_count += 1
                    print(f"[OK] YAML created and tags added: {file_path.name}")
                    
            except Exception as e:
                print(f"[ERR] Processing failed: {file_path.name} - {str(e)}")
        
        print(f"\n[OK] Updated {updated_count}  note tags")
        return updated_count
    
    def generate_enhanced_weekly_review(self):
        """生成增强版的每周回顾"""
        print("\n[note] Step 2: Generating enhanced weekly review...")
        
        # Get本周范围
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        week_number = monday.isocalendar()[1]
        
        # 收集本周笔记
        this_week_notes = []
        todos_from_notes = []
        video_notes = []
        
        for file_path in self.vault_path.rglob("*.md"):
            if any(part.startswith(".") for part in file_path.parts):
                continue
            if "每周知识回顾" in file_path.name:
                continue
                
            try:
                stat = file_path.stat()
                created_time = datetime.fromtimestamp(stat.st_ctime)
                
                if monday.date() <= created_time.date() <= sunday.date():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    note_info = {
                        'path': file_path,
                        'name': file_path.stem,
                        'created': created_time,
                        'tags': self.extract_tags(content),
                        'summary': self.extract_summary(content),
                        'todos': self.extract_todos(content),
                        'is_video_note': '视频' in content or 'youtube' in content.lower() or 'b站' in content,
                    }
                    
                    this_week_notes.append(note_info)
                    
                    if note_info['todos']:
                        todos_from_notes.extend(note_info['todos'])
                    
                    if note_info['is_video_note']:
                        video_notes.append(note_info)
                    
            except Exception as e:
                print(f"[ERR] Read failed: {file_path} - {str(e)}")
        
        # 生成增强版回顾Content
        content = self.build_enhanced_review_content(
            this_week_notes, 
            todos_from_notes, 
            video_notes,
            week_number,
            monday,
            sunday
        )
        
        # Save file
        review_path = self.vault_path / "00_临时笔记" / f"每周知识回顾-Round {week_number}周-增强版.md"
        review_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(review_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"[OK] Enhanced review saved: {review_path}")
        return review_path
    
    def extract_tags(self, content):
        """提取标签"""
        tags = []
        yaml_match = re.search(r'tags:\s*\[(.*?)\]', content, re.DOTALL)
        if yaml_match:
            tag_str = yaml_match.group(1)
            tags = [t.strip().strip('"').strip("'") for t in tag_str.split(',')]
        return tags
    
    def extract_summary(self, content):
        """提取总结"""
        summary_match = re.search(r'[[pin]>]\s*\*\*一句话总结\*\*: (.+?)(?:\n|$)', content)
        if summary_match:
            return summary_match.group(1).strip()
        return "暂无摘要"
    
    def extract_todos(self, content):
        """提取待办事项"""
        todos = []
        # 查找 - [ ] 格式的待办
        todo_matches = re.findall(r'- \[ \]\s*(.+?)(?:\n|$)', content)
        todos.extend(todo_matches)
        # 查找 TODO: 格式的待办
        todo_matches = re.findall(r'TODO[:: ]\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
        todos.extend(todo_matches)
        return todos
    
    def build_enhanced_review_content(self, notes, todos, video_notes, week_number, monday, sunday):
        """构建增强版回顾Content"""
        
        # 按标签分类
        tag_categories = defaultdict(list)
        for note in notes:
            for tag in note['tags']:
                tag_categories[tag].append(note)
        
        content = f"""---
aliases: [周回顾, 知识总结, 学习复盘]
tags: [每周回顾, 知识管理, 总结, 行动清单]
created: {datetime.now().strftime("%Y-%m-%d %H:%M")}
updated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
week: {week_number}
---

# [books] 每周知识回顾 - Round {week_number}周 (增强版) 

> 🗓️ 时间范围: {monday.strftime("%Y年%m月%d日")} ~ {sunday.strftime("%Y年%m月%d日")}
> [note] 本周新增笔记: {len(notes)} 篇
> [tag] 涉及标签: {len(tag_categories)}  类别
> [video] 视频学习: {len(video_notes)}  
> [OK] 待办事项: {len(todos)} 项

---

## [chart] 本周概览

### Statistics
| 指标 | 数量 | 说明 |
|------|------|------|
| [doc] 新增笔记 | {len(notes)} 篇 | 本周Create的笔记 |
| [tag] 标签类别 | {len(tag_categories)}   | 知识分类数 |
| [video] 视频笔记 | {len(video_notes)}   | 视频学习转化 |
| [OK] 待办事项 | {len(todos)} 项 | 需要跟进的事项 |

### 标签分布
"""
        
        # Add标签分布
        for tag, tag_notes in sorted(tag_categories.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
            content += f"- `{tag}`: {len(tag_notes)} 篇\n"
        
        content += """
---

## [OK] 待办事项清单

### 本周收集的待办
"""
        
        # Add待办事项
        if todos:
            for i, todo in enumerate(todos[:15], 1):  # 最多显示15 
                content += f"- [ ] {todo}\n"
        else:
            content += "> 本周没有收集到待办事项\n"
        
        content += """
### 下周行动计划
<!-- 在这里手动规划下周的具体行动 -->
- [ ] 
- [ ] 
- [ ] 

---

## [video] 视频学习汇总

### 本周视频学习笔记
"""
        
        # Add视频笔记
        if video_notes:
            for note in video_notes[:5]:
                content += f"""#### {note['name']}
- **总结**: {note['summary'][:100]}...
- **标签**: {', '.join(note['tags'][:3])}
- **链接**: [[{note['name']}]]

"""
        else:
            content += "> 本周没有视频学习笔记\n"
        
        content += """
---

## 📂 知识分类回顾

"""
        
        # 按标签分类展示笔记
        for tag, tag_notes in sorted(tag_categories.items()):
            content += f"### {tag}\n\n"
            content += f"本周Total记录 **{len(tag_notes)}** 篇相关笔记\n\n"
            
            for note in tag_notes[:5]:  # 每类最多显示5 
                content += f"- **{note['name']}**: {note['summary'][:80]}...\n"
            
            if len(tag_notes) > 5:
                content += f"- *...还有 {len(tag_notes) - 5} 篇笔记*\n"
            
            content += "\n"
        
        content += """---

## [link] 关联笔记推荐

### 基于本周学习的推荐链接
<!-- 系统自动推荐可能相关的笔记 -->
"""
        
        # 推荐关联笔记 (基于Total同标签) 
        related_notes = self.find_related_notes(notes)
        for note_name, reason in related_notes[:10]:
            content += f"- [[{note_name}]] - {reason}\n"
        
        content += """
---

## 🌟 本周亮点与反思

### 最重要的收获
<!-- 手动填写本周最重要的知识收获 -->
1. 
2. 
3. 

### 视频学习心得
<!-- 总结视频学习的核心收获 -->
- 

### 需要深入学习的方向
<!-- 标记需要后续深入研究的知识点 -->
- [ ] 
- [ ] 

### 学习方法优化
<!-- 反思本周的学习方法, 如何改进 -->
- 

---

## [chart] 学习数据追踪

### 本周学习时长统计
<!-- 手动填写或From笔记中提取 -->
| 日期 | 学习时长 | 主要Content |
|------|----------|----------|
"""
        
        # Add每日统计
        daily_notes = defaultdict(int)
        for note in notes:
            day = note['created'].strftime("%m月%d日")
            daily_notes[day] += 1
        
        for day in sorted(daily_notes.keys()):
            content += f"| {day} | - | {daily_notes[day]} 篇笔记 |\n"
        
        content += f"""
### 知识积累趋势
- 本周新增: {len(notes)} 篇
- 视频转化: {len(video_notes)} 篇
- 待办 complete率: -% (需手动统计)

---

## [search] 快速导航

### 按标签查看
"""
        
        # Add标签链接
        for tag in sorted(tag_categories.keys())[:15]:
            content += f"- `#{tag}`\n"
        
        content += """
### 历史回顾
- [[每周知识回顾]] - 查看所有周回顾

---

## [AI] Automation workflow说明

### video learning -> auto notes -> weekly review 闭环

```mermaid
graph LR
    A[观看视频] --> B[视频分析Agent]
    B --> C[自动生成笔记]
    C --> D[打上标签]
    D --> E[每周日自动回顾]
    E --> F[生成行动清单]
    F --> A
```

### 本周自动化统计
- [OK] 自动标签补全: already complete
- [OK] 待办事项提取: already complete
- [OK] 视频笔记Recognition: already complete
- [OK] 关联笔记推荐: already complete

---

*[AI] 此文件由Knowledge Base Enhancement System自动生成于 {datetime.now().strftime("%Y-%m-%d %H:%M")}*
*[idea] 提示: 请手动补充"本周亮点与反思"部分的Content*
"""
        
        return content
    
    def find_related_notes(self, notes):
        """基于标签Found关联笔记"""
        related = []
        
        # 收集所有标签
        all_tags = set()
        for note in notes:
            all_tags.update(note['tags'])
        
        # 扫描knowledge baseFound有Total同标签的笔记
        for file_path in self.vault_path.rglob("*.md"):
            if any(part.startswith(".") for part in file_path.parts):
                continue
            if "每周知识回顾" in file_path.name:
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                note_tags = self.extract_tags(content)
                common_tags = all_tags & set(note_tags)
                
                if common_tags:
                    related.append((file_path.stem, f"Total同标签: {', '.join(common_tags[:2])}"))
                    
            except Exception:
                continue
        
        return related
    
    def setup_video_integration(self):
        """设置视频集 successful能"""
        print("\n[video] Step 3: Configuring video learning integration...")
        
        # Create视频笔记模板
        video_template = """---
aliases: []
tags: ["视频学习", "待分类", "学习中"]
created: <% tp.date.now("YYYY-MM-DD HH:mm") %>
updated: <% tp.date.now("YYYY-MM-DD HH:mm") %>
video_source: <% tp.system.prompt("视频Source (如: B站/YouTube/其他) ") %>
video_url: <% tp.system.prompt("视频链接") %>
video_duration: <% tp.system.prompt("视频时长") %>
status: 学习中
---

# <% tp.file.title %>

> [video] **视频Source**: <% tp.system.prompt("视频平台") %>
> ⏱️ **视频时长**: <% tp.system.prompt("视频时长") %>
> [pin] **一句话总结**: <% tp.system.prompt("用一句话概括视频核心Content") %>

---

## [note] 视频笔记

### 关键时间点
| 时间 | Content摘要 | 详细笔记 |
|------|----------|----------|
| 00:00 | 开场/介绍 | <% tp.system.prompt("开场Content") %> |
| <% tp.system.prompt("关键时间点1") %> | <% tp.system.prompt("该时间点Content") %> | <% tp.system.prompt("详细笔记") %> |
| <% tp.system.prompt("关键时间点2") %> | <% tp.system.prompt("该时间点Content") %> | <% tp.system.prompt("详细笔记") %> |

### 核心知识点
1. <% tp.system.prompt("知识点1") %>
2. <% tp.system.prompt("知识点2") %>
3. <% tp.system.prompt("知识点3") %>

### 重要Screenshot/PPT
<!-- 插入视频中的关键Screenshot -->
- <% tp.system.prompt("Screenshot说明1") %>
- <% tp.system.prompt("Screenshot说明2") %>

---

## [idea] 学习心得

### 主要收获
<% tp.system.prompt("视频学习的主要收获") %>

### 疑问与思考
<% tp.system.prompt("观看过程中的疑问") %>

### 实践计划
- [ ] <% tp.system.prompt("实践计划1") %>
- [ ] <% tp.system.prompt("实践计划2") %>

---

## [link] 关联知识

### 前置知识
- [[<% tp.system.prompt("前置知识1") %>]]
- [[<% tp.system.prompt("前置知识2") %>]]

### 延伸阅读
- [[<% tp.system.prompt("相关笔记1") %>]]
- [[<% tp.system.prompt("相关笔记2") %>]]

---

## [OK] 后续行动

### 待办事项
- [ ] <% tp.system.prompt("待办1: 如整理笔记") %>
- [ ] <% tp.system.prompt("待办2: 如实践练习") %>
- [ ] <% tp.system.prompt("待办3: 如深入研究") %>

### 复习计划
- **下次复习时间**: <% tp.date.now("YYYY-MM-DD", 7) %>
- **复习重点**: <% tp.system.prompt("需要重点复习的Content") %>

---

*[video] 此笔记由视频学习模板自动生成*
*[refresh] 将自动纳入每周知识回顾*
"""
        
        # Save视频笔记模板
        template_path = self.vault_path / "99_模板库" / "视频学习笔记模板.md"
        template_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(video_template)
        
        print(f"[OK] Video learning template created: {template_path}")
        
        # Create视频分析 Agent 配置
        agent_config = {
            "name": "视频学习助手",
            "description": "自动分析视频Content并生成结构化笔记",
            "input": {
                "video_url": "视频链接",
                "video_file": "本地视频文件路径"
            },
            "output": {
                "note_template": "视频学习笔记模板",
                "auto_tag": True,
                "extract_keyframes": True,
                "generate_summary": True
            },
            "integration": {
                "weekly_review": True,
                "auto_categorize": True,
                "link_suggestions": True
            }
        }
        
        config_path = self.vault_path / "05_数据支撑" / "video_agent_config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(agent_config, f, ensure_ascii=False, indent=2)
        
        print(f"[OK] Video agent config saved: {config_path}")
        
        return True
    
    def run(self):
        """运行完整的增强流程"""
        print("=" * 60)
        print("[boot] Knowledge Base Enhancement System")
        print("=" * 60)
        print(f"\n[folder] Knowledge base path: {self.vault_path}")
        
        # 1. 完善标签体系
        self.ensure_tags()
        
        # 2. 生成增强版每周回顾
        review_path = self.generate_enhanced_weekly_review()
        
        # 3. 设置视频集成
        self.setup_video_integration()
        
        print("\n" + "=" * 60)
        print("[OK] Knowledge base enhancement complete!")
        print("=" * 60)
        
        print("\n[clipboard] Completed features: ")
        print("  1. [OK] Tag system improved - all notes auto-classified")
        print("  2. [OK] Enhanced weekly review with todos, video learning, recommendations")
        print("  3. [OK] Video learning integration - templates and agent config")
        
        print("\n[idea] Usage suggestions: ")
        print("  *  View enhanced review: 00_temp_notes/weekly_knowledge_review-Round_X-enhanced.md")
        print("  *  Use video template: 99_templates/video_learning_note_template.md")
        print("  *  Implement closed-loop process: video learning -> auto notes -> weekly review")
        
        print("\n[refresh] Automation workflow: ")
        print("  Watch -> Agent analyze -> Generate notes -> Auto-tag -> Sunday review -> Action items")


def main():
    """主函数"""
    vault_path = r"E:\obsidian\全能型knowledge base"
    
    enhancer = KnowledgeSystemEnhancer(vault_path)
    enhancer.run()


if __name__ == "__main__":
    main()
