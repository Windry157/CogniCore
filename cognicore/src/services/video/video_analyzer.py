import os
import json
from volcenginesdkarkruntime import Ark
from dotenv import load_dotenv

# Load环境变量
load_dotenv()

def analyze_video_key_frames(video_url: str, model_id: str = "doubao-seed-1-8"):
    """
    分析视频, 提取key image info
    :param video_url: Video URL地址
    :param model_id: ModelID, 默认使用doubao-seed-1-8
    :return: 符合要求的关键图片列表
    """
    # Initialization客户端
    api_key = os.environ.get("ARK_API_KEY")
    if not api_key:
        print("Error: ARK_API_KEY environment variable not set")
        return []
        
    client = Ark(
        api_key=api_key,
        base_url=os.environ.get("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3/")
    )

    # 构建Multimodal请求Content
    content = [
        {
            "type": "video_url",
            "video_url": video_url
        },
        {
            "type": "text",
            "text": "请分析这 视频, 找出所有包含代码讲解, 关键技术讲解PPT或能有效帮助读者理解Content的关键图片."
                    "对每 符合 entries件的图片, 输出其在视频中的时间 (格式为MM:SS) 和Reason说明."
                    "严格按照以下JSON数groups格式输出, 不要Add任何额外说明: \n"
                    "[\n"
                    "  {\n"
                    "    \"time\": \"01:23\",\n"
                    "    \"reason\": \"这张图片展示了关键操作, 信息量很大\"\n"
                    "  },\n"
                    "  {\n"
                    "    \"time\": \"02:15\",\n"
                    "    \"reason\": \"这张图片用PPT展示了关键技术概念\"\n"
                    "  }\n"
                    "]"
        }
    ]

    # 发送请求
    response = client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": content}],
        temperature=0.1,
        response_format={"type": "json_object"}
    )

    # 解析Response
    try:
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        print("Model output format exception, raw response: ", response.choices[0].message.content)
        return []

def main():
    # 配置参数
    VIDEO_URL = "https://v.douyin.com/G12cR5DNocw/"  # TestVideo URL
    MODEL_ID = "doubao-seed-1-8"

    # 执行分析
    print("Starting video analysis...")
    print(f"Video URL: {VIDEO_URL}")
    
    key_frames = analyze_video_key_frames(VIDEO_URL, MODEL_ID)

    # 输出
    print("\nAnalysis complete, key image info: ")
    print(json.dumps(key_frames, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
