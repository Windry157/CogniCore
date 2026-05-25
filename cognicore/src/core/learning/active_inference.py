"""主动推理 module"""

import numpy as np
import time
from .free_energy import FreeEnergyMinimizer


class ActiveInference:
    """
    主动推理 module
    
    基于自由能原理, 系统不仅要Update内部Model, 还要通过行动改变外部环境
    来最小化自由能
    """
    
    def __init__(self, model_prior=None):
        """
        Initialization主动推理 module
        
        Args:
            model_prior: Model的先验概率分布
        """
        self.free_energy_minimizer = FreeEnergyMinimizer(model_prior)
        self.possible_actions = []
        self.action_history = []  # 行动历史
        self.action_values = {}  # 行动价值评估
    
    def set_possible_actions(self, actions):
        """
        设置可能的行动
        
        Args:
            actions: 行动列表
        """
        self.possible_actions = actions
        # Initialization行动价值
        for action in actions:
            if action not in self.action_values:
                self.action_values[action] = 0.5
    
    def calculate_expected_free_energy(self, action, sensory_input, model):
        """
        计算预期自由能
        
        Args:
            action: 行动
            sensory_input: 感官输入
            model: 内部Model
            
        Returns:
            预期自由能
        """
        # 模拟行动后的感官输入
        predicted_input = self._simulate_action_effect(action, sensory_input, model)
        
        # 计算自由能
        free_energy, _ = self.free_energy_minimizer.calculate_free_energy(predicted_input, model)
        
        return free_energy
    
    def calculate_action_value(self, action, sensory_input, model, context=None):
        """
        计算行动价值
        
        Args:
            action: 行动
            sensory_input: 感官输入
            model: 内部Model
            context: 上下文信息
            
        Returns:
            行动价值
        """
        # 基础价值: 自由能的倒数
        free_energy = self.calculate_expected_free_energy(action, sensory_input, model)
        base_value = 1.0 / (1.0 + free_energy)
        
        # 上下文相关价值调整
        context_value = 1.0
        if context:
            # 根据上下文调整行动价值
            if action == "Save" and any(keyword in context for keyword in ["重要", "Save", "记录"]):
                context_value = 1.5
            elif action == "总结" and any(keyword in context for keyword in ["总结", "概括", "要点"]):
                context_value = 1.5
            elif action == "提问" and any(keyword in context for keyword in ["疑问", "问题", "为什么"]):
                context_value = 1.5
            elif action == "对比" and any(keyword in context for keyword in ["比较", "对比", "区别"]):
                context_value = 1.5
            elif action == "规划" and any(keyword in context for keyword in ["计划", "规划", "Step"]):
                context_value = 1.5
            elif action == "执行Tool调用" and any(keyword in context for keyword in ["执行", "Tool", "调用"]):
                context_value = 1.5
            elif action == "执行手机操作" and any(keyword in context for keyword in ["手机", "打开", "操作", "应用", "发消息", "打电话"]):
                context_value = 1.5
        
        # 历史价值: 基于过去的表现
        history_value = self.action_values.get(action, 0.5)
        
        # 综合价值
        total_value = base_value * 0.4 + context_value * 0.3 + history_value * 0.3
        
        return total_value
    
    def select_action(self, sensory_input, model, context=None):
        """
        选择最佳行动
        
        Args:
            sensory_input: 感官输入
            model: 内部Model
            context: 上下文信息, 用于辅助行动选择
            
        Returns:
            最佳行动
        """
        if not self.possible_actions:
            return None
        
        # 根据上下文信息进行启发式行动选择
        if context:
            # 检查是否包含URL
            import re
            url_pattern = r'https?://\S+'
            urls = re.findall(url_pattern, context)
            if urls and "Search网页" in self.possible_actions:
                # 如果包含URL, 优先选择Search网页
                return "Search网页"
            
            # 根据输入typeselecting action
            if any(keyword in context for keyword in ["声音", "叫声", "听见", "听"]):
                if "听" in self.possible_actions:
                    return "听"
            elif any(keyword in context for keyword in ["气味", "闻", "嗅觉"]):
                if "闻" in self.possible_actions:
                    return "闻"
            elif any(keyword in context for keyword in ["看", "视觉", "颜色", "形状"]):
                if "看" in self.possible_actions:
                    return "看"
            elif any(keyword in context for keyword in ["重要", "Save", "记录"]):
                if "Save" in self.possible_actions:
                    return "Save"
            elif any(keyword in context for keyword in ["总结", "概括", "要点"]):
                if "总结" in self.possible_actions:
                    return "总结"
            elif any(keyword in context for keyword in ["疑问", "问题", "为什么"]):
                if "提问" in self.possible_actions:
                    return "提问"
            elif any(keyword in context for keyword in ["比较", "对比", "区别"]):
                if "对比" in self.possible_actions:
                    return "对比"
            elif any(keyword in context for keyword in ["计划", "规划", "Step"]):
                if "规划" in self.possible_actions:
                    return "规划"
            elif any(keyword in context for keyword in ["执行", "Tool", "调用"]):
                if "执行Tool调用" in self.possible_actions:
                    return "执行Tool调用"
            elif any(keyword in context for keyword in ["手机", "打开", "操作", "应用", "发消息", "打电话"]):
                if "执行手机操作" in self.possible_actions:
                    return "执行手机操作"
        
        # 计算每 行动的价值
        action_values = []
        for action in self.possible_actions:
            value = self.calculate_action_value(action, sensory_input, model, context)
            action_values.append((action, value))
        
        # 选择价值最高的行动
        best_action, best_value = max(action_values, key=lambda x: x[1])
        
        # Update行动价值
        self._update_action_value(best_action, best_value)
        
        return best_action
    
    def _update_action_value(self, action, value):
        """
        Update行动价值
        
        Args:
            action: 行动
            value: 行动价值
        """
        if action in self.action_values:
            # 指数移动平均Update
            self.action_values[action] = 0.7 * self.action_values[action] + 0.3 * value
    
    def _simulate_action_effect(self, action, sensory_input, model):
        """
        模拟行动对环境的影响
        
        Args:
            action: 行动
            sensory_input: 感官输入
            model: 内部Model
            
        Returns:
            模拟的感官输入
        """
        # 将输入转换为NumPy数groups
        import numpy as np
        sensory_input = np.array(sensory_input)
        model = np.array(model)
        
        # 简单的行动效果模拟
        # 实际应用中, 这应该基于环境Model
        if action == "看":
            # 看的行动会减少不确定性, 使感官输入更接近Model预测
            return model * 0.8 + sensory_input * 0.2
        elif action == "听":
            # 听的行动会提供额外的信息
            return sensory_input + np.random.normal(0, 0.1, size=sensory_input.shape)
        elif action == "闻":
            # 闻的行动会提供不同type的信息
            return sensory_input * 0.9 + np.random.normal(0, 0.05, size=sensory_input.shape)
        elif action == "Search网页":
            # Search网页会提供外部信息
            return model * 0.6 + sensory_input * 0.4 + np.random.normal(0, 0.15, size=sensory_input.shape)
        elif action == "Save":
            # Save行动会巩固 memories
            return model * 0.9 + sensory_input * 0.1
        elif action == "总结":
            # 总结行动会提炼信息
            return model * 0.7 + sensory_input * 0.3
        elif action == "提问":
            # 提问行动会Get更多信息
            return sensory_input + np.random.normal(0, 0.12, size=sensory_input.shape)
        elif action == "对比":
            # 对比行动会发现差异
            return model * 0.5 + sensory_input * 0.5 + np.random.normal(0, 0.1, size=sensory_input.shape)
        elif action == "规划":
            # 规划行动会预测未来
            return model * 0.85 + sensory_input * 0.15
        elif action == "执行Tool调用":
            # 执行Tool调用会与外部交互
            return model * 0.65 + sensory_input * 0.35 + np.random.normal(0, 0.18, size=sensory_input.shape)
        elif action == "执行手机操作":
            # 执行手机操作会与手机交互, Get外部信息
            return model * 0.6 + sensory_input * 0.4 + np.random.normal(0, 0.2, size=sensory_input.shape)
        else:
            # 默认行动
            return sensory_input
    
    def act(self, sensory_input, model, context=None):
        """
        Execute action
        
        Args:
            sensory_input: 感官输入
            model: 内部Model
            context: 上下文信息, 用于辅助行动选择
            
        Returns:
            行动执行
        """
        best_action = self.select_action(sensory_input, model, context)
        print(f"[AI] Execute action: {best_action}")
        
        # 执行具体行动
        result = best_action
        if best_action == "执行手机操作":
            # From上下文中提取手机Task
            task = self._extract_phone_task(context)
            if task:
                # 尝试调用AutoGLM集成插件执行手机Task
                try:
                    from ..plugins.plugin_manager import PluginManager
                    pm = PluginManager()
                    pm.load_plugins()
                    autoglm_plugin = pm.plugins.get("autoglm_integration")
                    if autoglm_plugin:
                        task_result = autoglm_plugin.execute_phone_task(task)
                        result = f"执行手机Task: {task}, : {task_result.get('result', 'execution failed')}"
                    else:
                        result = f"执行手机Task: {task}, 但AutoGLM插件未Load"
                except Exception as e:
                    result = f"执行手机Task failed: {str(e)}"
            else:
                result = "执行手机Task failed: 无法From上下文中提取Task"
        
        # 记录行动历史
        self.action_history.append({
            'action': best_action,
            'result': result,
            'context': context,
            'timestamp': time.time()
        })
        
        return result
    
    def _extract_phone_task(self, context):
        """
        From上下文中提取手机Task
        
        Args:
            context: 上下文信息
            
        Returns:
            提取的手机Task
        """
        if not context:
            return "打开设置"
        
        # 简单的Task提取逻辑
        # 实际应用中可以使用更复杂的NLP方法
        import re
        
        # 提取Task关键词
        task_patterns = [
            r'打开(.*?)',
            r'Start(.*?)',
            r'运行(.*?)',
            r'执行(.*?)',
            r'发(.*?)消息',
            r'打(.*?)电话',
            r'浏览(.*?)',
            r'查看(.*?)'
        ]
        
        for pattern in task_patterns:
            match = re.search(pattern, context)
            if match:
                return match.group(0)
        
        # 如果没有提取到具体Task, 返回默认Task
        return "打开设置"
    
    def plan_chain_actions(self, goal, context, max_steps=5):
        """
        规划链式行动
        
        Args:
            goal: 目标
            context: 上下文信息
            max_steps: 最大Step数
            
        Returns:
            行动链列表
        """
        action_chain = []
        current_context = context
        
        for step in range(max_steps):
            # 简单的启发式规划
            if "Search" in goal.lower() and "Search网页" in self.possible_actions and "Search网页" not in action_chain:
                action = "Search网页"
            elif "总结" in goal.lower() and "总结" in self.possible_actions and "总结" not in action_chain:
                action = "总结"
            elif "Save" in goal.lower() and "Save" in self.possible_actions and "Save" not in action_chain:
                action = "Save"
            elif "对比" in goal.lower() and "对比" in self.possible_actions and "对比" not in action_chain:
                action = "对比"
            elif "规划" in goal.lower() and "规划" in self.possible_actions and "规划" not in action_chain:
                action = "规划"
            elif "提问" in goal.lower() and "提问" in self.possible_actions and "提问" not in action_chain:
                action = "提问"
            elif "执行" in goal.lower() and "执行Tool调用" in self.possible_actions and "执行Tool调用" not in action_chain:
                action = "执行Tool调用"
            elif any(keyword in goal.lower() for keyword in ["手机", "打开", "操作", "应用", "发消息", "打电话"]) and "执行手机操作" in self.possible_actions and "执行手机操作" not in action_chain:
                action = "执行手机操作"
            else:
                # 默认行动
                action = "看"
            
            action_chain.append(action)
            
            # 模拟行动效果, Update上下文
            current_context += f"\nalready执行: {action}"
        
        print(f"[AI] Plan action chain: {action_chain}")
        return action_chain
    
    def execute_action_chain(self, action_chain, sensory_input, model, context=None):
        """
        Execute action链
        
        Args:
            action_chain: 行动链列表
            sensory_input: 感官输入
            model: 内部Model
            context: 上下文信息
            
        Returns:
            执行
        """
        results = []
        current_context = context or ""
        
        for action in action_chain:
            result = self.act(sensory_input, model, current_context)
            results.append(result)
            current_context += f"\nalready执行: {action}"
        
        return results
    
    def get_action_history(self):
        """
        Get行动历史
        
        Returns:
            行动历史列表
        """
        return self.action_history
    
    def get_action_values(self):
        """
        Get行动价值
        
        Returns:
            行动价值字典
        """
        return self.action_values
