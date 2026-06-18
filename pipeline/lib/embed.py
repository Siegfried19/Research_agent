"""嵌入引擎 —— "意思尺":把文字变成可比较的坐标(向量),用于语义检索/找相似。

跟 lib/claude.py、lib/codex.py 并列的第三个引擎,但**它不是 LLM**:
只读文字→吐一串定长数字(向量),不生成文字、不对话,所以又小又快、CPU/GPU 都能跑。
意思相近的两段文字,坐标也相近 → "找意思像的"变成"找坐标近的"。

- 模型: Qwen/Qwen3-Embedding-0.6B(多语言,中英都强,1024维,体格小)。
- 模型文件落在 pipeline/retrieve/models/(gitignored,可重下),不污染家目录。
- 首次调用按需加载(首跑会下模型~1.2GB),之后进程内单例复用;GPU 可用就吃 GPU。
- 查询侧带 Qwen 的 instruct 前缀(召回更准),文档侧不带 —— 这是 Qwen3-Embedding 的推荐用法。

只在 research-agent conda 环境里有依赖(torch/sentence-transformers);base 环境 import 会失败,符合预期。
"""
import os
from pathlib import Path

# 模型缓存钉在检索模块内(必须在 import huggingface/sentence_transformers 之前设 HF_HOME)
_MODELS_DIR = Path(__file__).resolve().parent.parent / "retrieve" / "models"
_MODELS_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("HF_HOME", str(_MODELS_DIR))
# 防显存碎片:6GB 卡上一次 reindex 在同进程连续嵌很多篇,碎片会攒成"假性 OOM"(实测连续测
# 24k 会炸、单篇单独跑就过)。开 expandable_segments 后稳。必须在 import torch 前设。
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
_model = None


# 质量优先(用户 2026-06-18 定):满精度(fp32,不降精度) + 不截断长总结 + 逐篇小 batch。
# 6GB 笔记本 GPU(3060 Laptop)放不下"长序列+大 batch",所以代价全摊在 batch 上(=1,慢但保质)。
MAX_SEQ = 24576       # 模型原生上限 32768。实测(fp32/batch1)单篇显存峰值:8k=2.3G/16k=3.4G/
                      # 24k=4.5G —— 24576 在 6GB(可用~5.65G)留 ~1.2G 余量(+expandable_segments
                      # 防碎片 + CPU 兜底)。真实总结最长才 ~7k token,24576 是给未来更长总结的
                      # 天花板,平时够不着,绝不截断现有总结。
GPU_BATCH = 1         # 逐篇,质量优先(O(L²)注意力下大 batch + 长序列 + fp32 会爆 6GB 显存)


def get_model():
    """懒加载单例。第一次调用会(必要时)下载模型并载入显存/内存。满精度 fp32。"""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _model = SentenceTransformer(MODEL_NAME, device=device)  # 默认 fp32,不降精度
        _model.max_seq_length = MAX_SEQ                          # 抬到 16384=实质不截断
    return _model


def embed_documents(texts, batch_size=GPU_BATCH):
    """把一批文档(论文总结/主题综述)变坐标。返回 numpy 数组 (n, dim),已归一化。
    显存不够先减半 batch;减到 1 还 OOM 就把这批放 CPU 跑(满精度、慢但必完成,绝不降精度)。"""
    m = get_model()
    texts = list(texts)
    while True:
        try:
            return m.encode(texts, batch_size=batch_size, normalize_embeddings=True,
                            show_progress_bar=False, convert_to_numpy=True)
        except Exception as e:
            if "out of memory" not in str(e).lower():
                raise
            import torch
            torch.cuda.empty_cache()
            if batch_size > 1:                       # 还能减:先减半 batch 留在 GPU
                batch_size = max(1, batch_size // 2)
                continue
            return _encode_on_cpu(m, texts)          # batch 已=1 仍爆:整批退 CPU(不丢精度)


def _encode_on_cpu(m, texts):
    """单篇都撑爆显存时的兜底:临时把模型搬到 CPU 逐篇量,完事搬回 GPU。慢但满精度、必完成。"""
    import torch
    m.to("cpu")
    try:
        return m.encode(texts, batch_size=1, normalize_embeddings=True,
                        show_progress_bar=False, convert_to_numpy=True)
    finally:
        if torch.cuda.is_available():
            m.to("cuda")


def embed_query(text):
    """把一条查询变坐标(查询侧带 instruct 前缀,召回更准)。返回 1 维 numpy 向量。"""
    m = get_model()
    v = m.encode([text], prompt_name="query", normalize_embeddings=True,
                 convert_to_numpy=True)
    return v[0]


def dim():
    """向量维度(Qwen3-Embedding-0.6B = 1024)。"""
    return get_model().get_sentence_embedding_dimension()
