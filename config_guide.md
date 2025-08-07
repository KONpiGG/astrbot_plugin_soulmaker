# DeepSeek R1 API 配置指南

## 环境变量设置

在运行测试之前，您需要设置以下环境变量：

### 方法1：直接在终端设置
```bash
export API_KEY="your_deepseek_api_key_here"
export API_BASE_URL="https://api.deepseek.com/v1/chat/completions"
export MODEL_NAME="deepseek-chat"
```

### 方法2：创建 .env 文件
在项目根目录创建 `.env` 文件：
```
API_KEY=your_deepseek_api_key_here
API_BASE_URL=https://api.deepseek.com/v1/chat/completions
MODEL_NAME=deepseek-chat
```

## DeepSeek R1 模型选项

- `deepseek-chat`: 通用对话模型
- `deepseek-coder`: 代码生成模型

## 获取 API 密钥

1. 访问 [DeepSeek 官网](https://platform.deepseek.com/)
2. 注册并登录账户
3. 在控制台中获取 API 密钥
4. 将密钥替换到上述配置中

## 运行测试

配置完成后，运行：
```bash
python test.py
``` 