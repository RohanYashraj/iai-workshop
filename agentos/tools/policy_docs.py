"""Policy-document RAG tool for the Team (from notebook 05)."""

from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import fetch_if_missing


def load_policy_chunks(filepaths):
    """Splits each markdown file into its ## sections, so retrieval returns one coherent
    topic at a time rather than a whole document or a single sentence."""
    chunks = {}
    for path in filepaths:
        text = Path(path).read_text(encoding="utf-8")
        doc_id = Path(path).stem
        sections = text.split("\n## ")
        for i, section in enumerate(sections):
            if i > 0:
                section = "## " + section
            section = section.strip()
            if not section:
                continue
            heading = section.splitlines()[0].lstrip("#").strip()
            chunks[f"{doc_id} :: {heading[:60]}"] = section
    return chunks


POLICY_CHUNKS = load_policy_chunks([fetch_if_missing("ip_policy_assumptions.md"),
                                    fetch_if_missing("pmi_policy_assumptions.md")])
_vec = TfidfVectorizer().fit(POLICY_CHUNKS.values())
_mat = _vec.transform(POLICY_CHUNKS.values())
_chunk_keys = list(POLICY_CHUNKS)


def search_policy_docs(query: str) -> dict:
    """Search ABC Health's policy assumption documents for IP and PMI. Returns the single most
    relevant passage and its source chunk id - always cite the source in any answer built from
    this result."""
    sims = cosine_similarity(_vec.transform([query]), _mat)[0]
    i = int(sims.argmax())
    return {
        "source": _chunk_keys[i],
        "passage": POLICY_CHUNKS[_chunk_keys[i]],
        "relevance_score": round(float(sims[i]), 3),
    }
