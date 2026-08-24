# IAI Seminar — Workshop Notebooks

Notebooks `01`–`06` plus `data_notebook.ipynb`, runnable either in Google Colab or locally.

## Running in Google Colab (recommended for participants)

1. Open a notebook in Colab (File → Open notebook → GitHub → `RohanYashraj/iai-workshop`).
2. Add your Gemini API key once: click the **🔑 Secrets** icon in Colab's left sidebar, add a secret named `GOOGLE_API_KEY` with your key, and toggle **Notebook access** on.
3. Run the cells top to bottom. Each notebook installs its own dependencies (`%pip install` in the first cell) and downloads any data files it needs from this repo automatically — no other setup required.

## Running locally

Everything needed to run all seven notebooks locally, outside Colab. Dependencies were extracted directly from every `%pip install` line and `import` statement across all seven notebooks, then locked with `uv`.

## Setup

```bash
uv sync
```

This creates `.venv/` with exactly the versions in `uv.lock` — 169 packages resolved, includes JupyterLab itself so you don't need a separate Jupyter install.

## Register the kernel (one-time)

```bash
uv run python -m ipykernel install --user --name iai-seminar --display-name "IAI Seminar (uv)"
```

Then in Jupyter/VS Code, select **"IAI Seminar (uv)"** as the kernel for each notebook.

## Run

```bash
uv run jupyter lab
```

## API key (local, non-Colab use)

The notebooks all try Colab Secrets first, then fall back to a local `.env` file. Copy the provided example and fill in your key:

```bash
cp .env.example .env
```

Then edit `.env` and replace the placeholder with your own Gemini API key.

`python-dotenv` (included) picks this up automatically via each notebook's existing `try: ... except: load_dotenv()` fallback — no notebook code changes needed.

## What's in `pyproject.toml`

| Package | Used by |
|---|---|
| `agno`, `google-genai`, `google-auth` | Every agent notebook (01, 03, 04, 05, 06) |
| `python-dotenv` | Local (non-Colab) API key fallback |
| `pandas`, `numpy`, `matplotlib` | All notebooks — data, tables, charts |
| `scikit-learn` | GLM/model comparisons (02), TF-IDF RAG (05, 06) |
| `xgboost`, `shap`, `statsmodels` | Notebook 02's model comparison track |
| `jupyterlab`, `ipykernel`, `notebook` | Running the notebooks themselves |

## Note on notebook 05 / `data_notebook.ipynb`

`data_notebook.ipynb` and `05_pricing_team.ipynb` both write/read `.pkl` files in their working directory — run them from the same folder (or copy the pre-built `ip_pricing_artifacts.pkl` / `pmi_pricing_artifacts.pkl` alongside `05_pricing_team.ipynb` if you'd rather skip regenerating).
