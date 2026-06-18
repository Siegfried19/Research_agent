"""索引新鲜度判定 —— fts(关键词)与 vec(向量)两本目录**共用**,保证"判断一篇要不要
重建索引"的逻辑完全一致(原来 fts 用 mtime、vec 用 md5(全文),既不一致又每次读所有文件)。

两段钥匙(便宜筛 → 变了再精确确认):
- stale_key = 便宜指纹,**不读总结文件**(标题+摘要+版本路径+文件mtime 都是手边就有的)。
  没变 → 直接跳过,省掉"读全文算哈希"的开销;abstract 改了 / 换版本 / 动文件 → 指纹变。
- 指纹变了之后,调用方再读全文算 body_hash 精确确认内容真变了才重嵌(见 index.build_index)。
"""
import hashlib


def latest_summary_map(main):
    """{paper_id: 最新版总结相对路径}。按 version 升序,后写覆盖=最高版(全局每篇一个版本号)。"""
    m = {}
    for r in main.execute("SELECT paper_id, path FROM summary_versions ORDER BY paper_id, version"):
        m[r["paper_id"]] = r["path"]
    return m


def stale_key(title, abstract, path, mtime):
    """便宜的内容指纹(不碰总结文件)。任一变化都会改指纹:
    abstract/title 改、换了总结版本(path 变)、总结文件被改写(mtime 变)。"""
    raw = "\x00".join([title or "", abstract or "", path or "", repr(mtime)])
    return hashlib.md5(raw.encode("utf-8")).hexdigest()
