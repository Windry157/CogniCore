"""自由能最小化过程"""

import numpy as np


class FreeEnergyMinimizer:
    """
    自由能最小化器
    
    基于自由能原理, 大脑通过最小化预测误差来维持内部Model
    自由能 = 惊讶度 - 复杂度 = -ln P(s) - (-ln P(s|m)) = -ln P(s|m) + ln P(m)
    其中: 
    - s: 感官输入
    - m: 内部Model
    - P(s): 感官输入的概率
    - P(s|m): 给定Model时感官输入的概率
    - P(m): Model的先验概率
    """
    
    def __init__(self, model_prior=None):
        """
        Initialization自由能最小化器
        
        Args:
            model_prior: Model的先验概率分布
        """
        self.model_prior = model_prior
        self.current_model = model_prior
    
    def calculate_free_energy(self, sensory_input, model_prediction):
        """
        计算自由能
        
        Args:
            sensory_input: 感官输入
            model_prediction: Model预测
            
        Returns:
            自由能值
        """
        # 计算预测误差
        prediction_error = np.abs(sensory_input - model_prediction)
        
        # 计算惊讶度 (负对数似然)
        surprise = -np.log(self._likelihood(sensory_input, model_prediction) + 1e-10)
        
        # 计算复杂度 (负对数先验)
        complexity = -np.log(self.model_prior + 1e-10) if self.model_prior is not None else 0
        
        # 自由能 = 惊讶度 + 复杂度
        free_energy = surprise + complexity
        
        return free_energy, prediction_error
    
    def minimize_free_energy(self, sensory_input, learning_rate=0.1, iterations=100):
        """
        最小化自由能, Update内部Model
        
        Args:
            sensory_input: 感官输入
            learning_rate: 学习率
            iterations: 迭代次数
            
        Returns:
            Update后的Model和最终自由能
        """
        if self.current_model is None:
            self.current_model = np.random.normal(0, 1, size=sensory_input.shape)
        
        for i in range(iterations):
            # Model预测
            model_prediction = self._predict(self.current_model)
            
            # 计算自由能和预测误差
            free_energy, prediction_error = self.calculate_free_energy(sensory_input, model_prediction)
            
            # 通过梯度下降UpdateModel
            gradient = self._compute_gradient(prediction_error)
            self.current_model -= learning_rate * gradient
            
            # 检查收敛
            if i > 0 and np.mean(np.abs(free_energy - previous_free_energy)) < 1e-6:
                break
            
            previous_free_energy = free_energy
        
        return self.current_model, free_energy
    
    def _likelihood(self, sensory_input, model_prediction):
        """
        计算似然度 P(s|m)
        
        Args:
            sensory_input: 感官输入
            model_prediction: Model预测
            
        Returns:
            似然度
        """
        # 使用高斯分布计算似然度
        variance = 0.1
        return np.exp(-0.5 * np.sum((sensory_input - model_prediction)**2 / variance))
    
    def _predict(self, model):
        """
        Model预测函数
        
        Args:
            model: 内部Model
            
        Returns:
            预测值
        """
        # 简单线性预测
        return model
    
    def _compute_gradient(self, prediction_error):
        """
        计算梯度
        
        Args:
            prediction_error: 预测误差
            
        Returns:
            梯度
        """
        # 简单梯度计算
        return prediction_error
    
    def get_current_model(self):
        """
        Get当前内部Model
        
        Returns:
            Current model
        """
        return self.current_model
