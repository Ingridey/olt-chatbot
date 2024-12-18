# Setting up a development environment

The dependencies in this project is managed via the `uv` tool. Step 0 is to [install
uv](https://docs.astral.sh/uv/getting-started/installation/) on your system. To install
the correct Python-version and all project dependencies, run:

```bash
uv sync
```

To install and activate the pre-commit tool:

```bash
uv tool install pre-commit
pre-commit install
```

# Updating the retriever databases

The retriever databases are stored in the `output` directory. When updating, we will
read all the webcontents from https://olympiatoppen.no/ and https://olt-skala.nif.no/.
We will also index the content of some PDF files that are included as part of the
project.

```bash
python -m olt_chatbot.tasks
```

# Start the webapp

Use the chainlit CLI to start the webapp:

```bash
uv run chainlit run --watch --headless --port 8764 src/olt_chatbot/chainlit_app.py
```

You can then point your browser to http://localhost:8764
