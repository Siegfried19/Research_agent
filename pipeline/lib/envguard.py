"""把流水线统一钉在 `research-agent` conda 环境里跑(2026-06-18)。

为什么:检索段(ask.py/retrieve/embed/similar)要 torch/sentence-transformers/sqlite-vec,
只装在 research-agent 环境;主链只要 requests,但用同一个超集环境省得在 base/research-agent
之间来回切。做法=入口脚本(run.py / ask.py)顶部调 `ensure_env()`:**当前若不在该环境,就用
该环境的 python 自动 re-exec 自己**——不管经 `bash run.sh` / `python3` / cron / bot 哪种方式
起,都自动落到对的环境。逃生口:置 `RESEARCH_NO_REEXEC=1` 跳过(调试/特殊场景用)。

换机器可移植:**按环境名探测、不写死任何绝对路径**(经 $CONDA_EXE / which conda / 常见安装位置)。
找不到该环境时不拦着——主链在 base 也能跑(只缺向量检索,ask.py 本就会自动回退纯 FTS)。
"""
import os
import shutil
import sys
from pathlib import Path

ENV_NAME = "research-agent"


def _already_in_env():
    """当前解释器是否已是 research-agent 环境。"""
    if os.environ.get("CONDA_DEFAULT_ENV") == ENV_NAME:
        return True
    # 直接用该环境 python 起、没 activate 时 CONDA_DEFAULT_ENV 可能为空 → 看 sys.prefix
    return Path(sys.prefix).name == ENV_NAME or sys.prefix.endswith(f"/envs/{ENV_NAME}")


def _find_env_python():
    """按环境名找该 conda 环境的 python 可执行文件,返回 Path 或 None(都不写死路径)。"""
    candidates = []
    conda_exe = os.environ.get("CONDA_EXE")  # conda 一旦初始化就有
    if conda_exe:
        base = Path(conda_exe).resolve().parent.parent  # <base>/bin/conda → <base>
        candidates.append(base / "envs" / ENV_NAME / "bin" / "python")
    which_conda = shutil.which("conda")
    if which_conda:
        base = Path(which_conda).resolve().parent.parent
        candidates.append(base / "envs" / ENV_NAME / "bin" / "python")
    home = Path.home()  # 常见安装位置兜底(cron 等无 conda 初始化的干净环境)
    for d in ("anaconda3", "miniconda3", "miniforge3", "mambaforge"):
        candidates.append(home / d / "envs" / ENV_NAME / "bin" / "python")
    for p in candidates:
        if p.is_file():
            return p
    return None


def ensure_env():
    """不在 research-agent 环境就用它的 python re-exec 自己(幂等;已在/逃生口设置则直接返回)。"""
    if os.environ.get("RESEARCH_NO_REEXEC") or _already_in_env():
        return
    py = _find_env_python()
    if py is None:
        sys.stderr.write(
            f"[envguard] 未找到 conda 环境 '{ENV_NAME}',继续用当前 python "
            f"({sys.executable});向量检索功能可能不可用(主链不受影响)。\n")
        return
    os.environ["RESEARCH_NO_REEXEC"] = "1"  # 防 re-exec 重入死循环
    script = os.path.abspath(sys.argv[0])
    os.execv(str(py), [str(py), script, *sys.argv[1:]])
