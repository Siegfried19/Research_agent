// Source clients: OpenAlex, Semantic Scholar, arXiv, PubMed.
// Each returns an array of normalized records with shape:
//   { source, doi, title, authors:[], year, venue, abstract, language,
//     citation_count, is_oa, oa_url, landing_url, ext_ids:{}, ref_ext_ids:[], relRank }
'use strict';

const { getJSON, getText, sleep } = require('./http');

const MAILTO = 'a0904251001@gmail.com';

const normDoi = (d) =>
  !d ? null : String(d).toLowerCase().replace(/^https?:\/\/(dx\.)?doi\.org\//, '').replace(/^doi:/, '').trim() || null;

function abstractFromInverted(inv) {
  if (!inv) return null;
  const words = [];
  for (const [w, positions] of Object.entries(inv)) for (const p of positions) words[p] = w;
  const s = words.join(' ').trim();
  return s || null;
}

// ---------- OpenAlex ----------
async function openalex(query, { fromDate, perPage = 120 }) {
  const url =
    `https://api.openalex.org/works?search=${encodeURIComponent(query)}` +
    `&filter=from_publication_date:${fromDate}` +
    `&per-page=${perPage}&sort=relevance_score:desc&mailto=${MAILTO}`;
  const data = await getJSON(url, { timeout: 45000 });
  return (data.results || []).map((w, i) => ({
    source: 'openalex',
    doi: normDoi(w.doi),
    title: w.display_name || w.title || '',
    authors: (w.authorships || []).map((a) => a.author && a.author.display_name).filter(Boolean),
    year: w.publication_year || null,
    venue: w.primary_location && w.primary_location.source && w.primary_location.source.display_name,
    abstract: abstractFromInverted(w.abstract_inverted_index),
    language: w.language || null,
    citation_count: w.cited_by_count || 0,
    is_oa: !!(w.open_access && w.open_access.is_oa),
    oa_url: (w.open_access && w.open_access.oa_url) ||
      (w.best_oa_location && w.best_oa_location.pdf_url) || null,
    landing_url: w.doi || (w.primary_location && w.primary_location.landing_page_url) || null,
    ext_ids: {
      openalex: w.id ? w.id.replace('https://openalex.org/', '') : null,
      doi: normDoi(w.doi),
      pmid: w.ids && w.ids.pmid ? w.ids.pmid.replace('https://pubmed.ncbi.nlm.nih.gov/', '') : null,
    },
    // referenced_works are OpenAlex IDs -> used to build the internal citation graph
    ref_ext_ids: (w.referenced_works || []).map((r) => r.replace('https://openalex.org/', '')),
    relRank: i,
  }));
}

// ---------- Semantic Scholar ----------
async function semanticScholar(query, { fromYear, limit = 100 }) {
  const fields =
    'title,abstract,year,authors,venue,externalIds,citationCount,openAccessPdf,publicationTypes';
  const url =
    `https://api.semanticscholar.org/graph/v1/paper/search?query=${encodeURIComponent(query)}` +
    `&year=${fromYear}-&fields=${fields}&limit=${limit}`;
  let data;
  try {
    data = await getJSON(url, { timeout: 45000, retries: 3, retryDelay: 3000 });
  } catch (e) {
    if (e.status === 429) return []; // rate-limited without a key; skip gracefully
    throw e;
  }
  return (data.data || []).map((p, i) => ({
    source: 'semantic_scholar',
    doi: normDoi(p.externalIds && p.externalIds.DOI),
    title: p.title || '',
    authors: (p.authors || []).map((a) => a.name).filter(Boolean),
    year: p.year || null,
    venue: p.venue || null,
    abstract: p.abstract || null,
    language: null,
    citation_count: p.citationCount || 0,
    is_oa: !!(p.openAccessPdf && p.openAccessPdf.url),
    oa_url: (p.openAccessPdf && p.openAccessPdf.url) || null,
    landing_url: p.externalIds && p.externalIds.DOI ? `https://doi.org/${p.externalIds.DOI}` : null,
    ext_ids: {
      s2: p.paperId || null,
      doi: normDoi(p.externalIds && p.externalIds.DOI),
      arxiv: (p.externalIds && p.externalIds.ArXiv) || null,
      pmid: (p.externalIds && p.externalIds.PubMed) || null,
    },
    ref_ext_ids: [],
    relRank: i,
  }));
}

// ---------- arXiv (Atom XML, parsed with regex) ----------
function pick(block, tag) {
  const m = block.match(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)</${tag}>`, 'i'));
  return m ? m[1].replace(/\s+/g, ' ').trim() : null;
}
async function arxiv(query, { fromYear, limit = 80 }) {
  const url =
    `https://export.arxiv.org/api/query?search_query=all:${encodeURIComponent(query)}` +
    `&start=0&max_results=${limit}&sortBy=relevance&sortOrder=descending`;
  const xml = await getText(url, { timeout: 45000 });
  const entries = xml.split('<entry>').slice(1).map((e) => '<entry>' + e.split('</entry>')[0]);
  const out = [];
  entries.forEach((block, i) => {
    const idUrl = pick(block, 'id'); // http://arxiv.org/abs/2401.01234v1
    const arxivId = idUrl ? idUrl.replace(/^https?:\/\/arxiv\.org\/abs\//, '').replace(/v\d+$/, '') : null;
    const published = pick(block, 'published');
    const year = published ? parseInt(published.slice(0, 4), 10) : null;
    if (fromYear && year && year < fromYear) return;
    const doi = pick(block, 'arxiv:doi');
    const pdfMatch = block.match(/<link[^>]*title="pdf"[^>]*href="([^"]+)"/i);
    const authors = [...block.matchAll(/<name>([\s\S]*?)<\/name>/g)].map((m) => m[1].trim());
    out.push({
      source: 'arxiv',
      doi: normDoi(doi),
      title: pick(block, 'title') || '',
      authors,
      year,
      venue: 'arXiv',
      abstract: pick(block, 'summary'),
      language: 'en',
      citation_count: 0,
      is_oa: true,
      oa_url: pdfMatch ? pdfMatch[1] : (arxivId ? `https://arxiv.org/pdf/${arxivId}` : null),
      landing_url: idUrl,
      ext_ids: { arxiv: arxivId, doi: normDoi(doi) },
      ref_ext_ids: [],
      relRank: i,
    });
  });
  return out;
}

// ---------- PubMed (E-utilities) ----------
async function pubmed(query, { fromYear, toYear, limit = 100 }) {
  const esearch =
    `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json` +
    `&retmax=${limit}&datetype=pdat&mindate=${fromYear}&maxdate=${toYear}` +
    `&term=${encodeURIComponent(query)}`;
  const s = await getJSON(esearch, { timeout: 45000 });
  const ids = (s.esearchresult && s.esearchresult.idlist) || [];
  if (!ids.length) return [];
  await sleep(400);
  const esum =
    `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&id=${ids.join(',')}`;
  const d = await getJSON(esum, { timeout: 45000 });
  const r = d.result || {};
  return (r.uids || []).map((uid, i) => {
    const p = r[uid] || {};
    const doi = (p.articleids || []).find((a) => a.idtype === 'doi');
    return {
      source: 'pubmed',
      doi: normDoi(doi && doi.value),
      title: p.title || '',
      authors: (p.authors || []).map((a) => a.name).filter(Boolean),
      year: p.pubdate ? parseInt(String(p.pubdate).slice(0, 4), 10) : null,
      venue: p.fulljournalname || p.source || null,
      abstract: null, // abstracts need a separate efetch; filled later if PubMed-only
      language: null,
      citation_count: 0,
      is_oa: false,
      oa_url: null,
      landing_url: doi ? `https://doi.org/${doi.value}` : `https://pubmed.ncbi.nlm.nih.gov/${uid}/`,
      ext_ids: { pmid: uid, doi: normDoi(doi && doi.value) },
      ref_ext_ids: [],
      relRank: i,
    };
  });
}

module.exports = { openalex, semanticScholar, arxiv, pubmed, normDoi, abstractFromInverted };
