# MAC-Reasoner

This repository is the official code implementation of the paper *MAC-Reasoner: A Multi-Agent Collaborative Framework for Enhancing Logical Reasoning in Large Language Models*.

## Installation

We recommend using a Python virtual environment.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If you are using Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Datasets

The repository already includes the following datasets:

- `AR-LSAT`
- `BBEH_Web_of_Lies`
- `BBEH_Zebra_Puzzles`
- `ProverQA_Hard`

Each dataset directory contains:

- `test.json`
- `few-shots.json`

## Usage

First, activate the virtual environment:

```bash
source .venv/bin/activate
```

This project supports two backend types:

- OpenAI-compatible APIs accessed through `ChatOpenAI`
- Gemini models accessed through `ChatGoogleGenerativeAI`

For OpenAI-compatible backends, use the default interface and provide `--base_url` when needed:

```bash
python main.py \
  --base_url "https://ark.cn-beijing.volces.com/api/v3" \
  --api_key <YOUR_API_KEY> \
  --model_name "doubao-1-5-pro-32k-250115" \
  --dataset AR-LSAT
```

For Gemini models, add the `--Gemini` flag. This code path uses a dedicated Gemini client instead of the OpenAI-compatible interface:

```bash
python main.py \
  --api_key <YOUR_GEMINI_API_KEY> \
  --model_name "gemini-2.5-flash" \
  --dataset AR-LSAT \
  --Gemini
```

You can also set `--max_tokens` for either backend:

```bash
python main.py \
  --api_key <YOUR_GEMINI_API_KEY> \
  --model_name "gemini-2.5-flash" \
  --dataset ProverQA_Hard \
  --max_tokens 12288 \
  --Gemini
```

You can inspect all available arguments with:

```bash
python main.py --help
```

## Output

After execution, results are saved under the `results/` directory with the following naming pattern:

```text
results/{dataset}-{model_name}.json
```

If the model name contains `/`, it will be automatically replaced with `_`.

## Citation

If you find this helpful, please cite our paper:

```bibtex
@inproceedings{lin-etal-2026-mac,
    title = "{MAC}-Reasoner: A Multi-Agent Collaborative Framework for Enhancing Logical Reasoning in Large Language Models",
    author = "Lin, Yehua  and
      Zheng, Liping  and
      Chen, Yin",
    editor = "Liakata, Maria  and
      Moreira, Viviane P.  and
      Zhang, Jiajun  and
      Jurgens, David",
    booktitle = "Findings of the {A}ssociation for {C}omputational {L}inguistics: {ACL} 2026",
    month = jul,
    year = "2026",
    address = "San Diego, California, United States",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2026.findings-acl.233/",
    doi = "10.18653/v1/2026.findings-acl.233",
    pages = "4739--4762",
    ISBN = "979-8-89176-395-1"
}
```
