#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据管道端到端验证报告模块
"""

import asyncio
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from src.core.data_pipeline_mvp import DataPipelineMVP, DecisionEvent, DecisionMode, PipelineVerifier

logger = logging.getLogger(__name__)


class PipelineValidationReport:
    """管道验证报告生成器
    """
    
    def __init__(self):
        self.results = {}
        self.start_time = datetime.now()
    
    def generate_html(self, data: Dict[str, Any]) -> str:
        """生成 HTML 报告
        """
        html = f"""
<html>
<head>
    <meta charset="UTF-8">
    <title>CogniCore 数据管道验证报告</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; }}
        .header {{ background: #0066cc; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .section {{ margin: 20px 0; padding: 20px; background: #f8f9fa; border-radius: 8px; }}
        .success {{ color: #0f5132; background: #d1e7dd; padding: 10px; border-radius: 4px; }}
        .stage {{ margin: 10px 0; padding: 10px; border-left: 4px solid #0066cc; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ padding: 10px; border: 1px solid #dee2e6; text-align: left; }}
        th {{ background: #e9ecef; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 CogniCore 数据管道 - 端到端验证报告</h1>
        <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="section">
        <h2>📊 测试概览</h2>
        <div class="success">
            <strong>测试状态: {'✅ 通过' if data.get('test_passed') else '❌ 失败'}</strong>
        </div>
        <p><strong>Session ID:</strong> {data.get('session_id', 'N/A')}</p>
        <p><strong>事件数量:</strong> {data.get('event_count', 0)}</p>
        <p><strong>耗时:</strong> {data.get('result', {}).get('elapsed_ms', 0)} ms</p>
    </div>
    
    <div class="section">
        <h2>🔄 数据流向图</h2>
        <div class="stage">
            <pre>
[用户输入]
    ↓
[生成 DecisionEvent]
    ↓
[MQ 发布/内存队列]
    ↓
[SQLite 持久化]
    ↓
[验证查询]
            </pre>
        </div>
        <h3>执行阶段</h3>
        <table>
            <tr>
                <th>阶段</th>
                <th>状态</th>
            </tr>
            {self._render_stages(data)}
        </table>
    </div>
    
    <div class="section">
        <h2>🏗️ 技术栈</h2>
        <table>
            <tr><th>组件</th><th>技术</th><th>说明</th></tr>
            <tr><td>编程语言</td><td>Python 3.10+</td><td>与现有项目一致</td></tr>
            <tr><td>Web框架</td><td>FastAPI</td><td>已集成</td></tr>
            <tr><td>存储</td><td>SQLite</td><td>U盘完美适配</td></tr>
            <tr><td>消息队列</td><td>Redis Streams (可选)</td><td>内存降级模式</td></tr>
        </table>
    </div>
    
    <div class="section">
        <h2>💾 原始数据</h2>
        <pre>{json.dumps(data, indent=2, ensure_ascii=False)}</pre>
    </div>
</body>
</html>
        """
        return html
    
    def _render_stages(self, data):
        stages = data.get('result', {}).get('stages', [])
        html = ""
        for stage in stages:
            html += f"<tr><td>{stage}</td><td>✅ 成功</td></tr>"
        return html
    
    def save_report(self, data: Dict[str, Any], output_dir: Path = None):
        """保存报告
        """
        if output_dir is None:
            output_dir = Path(__file__).parent / "reports"
        output_dir.mkdir(exist_ok=True)
        
        html = self.generate_html(data)
        output_file = output_dir / f"pipeline_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        output_file.write_text(html, encoding="utf-8")
        
        print(f"\n📄 报告已保存: {output_file}")
        
        return output_file


async def run_validation():
    """运行完整端到端验证
    """
    logging.basicConfig(level=logging.INFO)
    print("="*70)
    print("  🚀 CogniCore 数据管道 - 端到端验证")
    print("="*70)
    
    pipeline = DataPipelineMVP(use_redis=False)
    await pipeline.initialize()
    
    verifier = PipelineVerifier(pipeline)
    reporter = PipelineValidationReport()
    
    verifier.print_data_flow()
    
    test_result = await verifier.run_hello_world_test()
    
    report_file = reporter.save_report(test_result)
    
    print("\n" + "="*70)
    print("  🎉 端到端验证完成！")
    print("="*70)
    
    return {
        "test_result": test_result,
        "report_file": str(report_file)
    }


if __name__ == "__main__":
    asyncio.run(run_validation())
