# Transaction Intelligence System

A LangChain-based financial transaction analysis pipeline that answers natural language queries about customer transactions and generates comprehensive PDF reports.

## Features

### Core Capabilities
- **Natural Language Query Processing**: Ask questions in plain English about customer transactions
- **Intelligent Intent Recognition**: Automatically understands user intent and maps to appropriate analytics
- **Structured Pipeline Architecture**: Modular design with intent parsing, planning, execution, and explanation phases
- **Real-time Streaming Responses**: Get live responses as the AI generates answers
- **PDF Report Generation**: Generate comprehensive customer financial reports with LLM-powered summaries
- **Comprehensive Audit Logging**: Full traceability of all queries and responses

---

## Architecture

```
User Query → IntentParser (LLM) → Planner → ToolExecutor → Explainer (LLM) → Response
```

### Pipeline Components

| Component | File | Purpose |
|-----------|------|---------|
| **Intent Parser** | `pipeline/intent_parser.py` | LLM extracts intent + params from query |
| **Planner** | `pipeline/planner.py` | Maps intent → tool calls, validates required fields |
| **Executor** | `pipeline/executor.py` | Runs tools, returns ToolResult |
| **Explainer** | `pipeline/explainer.py` | LLM generates natural language response |
| **Orchestrator** | `pipeline/orchestrator.py` | Coordinates the full pipeline |
| **Audit Logger** | `pipeline/audit.py` | Records all queries and responses |

### Report Generation Flow

```
IntentParser → Planner → generate_customer_report tool
                              ↓
                    customer_report_builder.py (data collection, NO LLM)
                              ↓
                    report_summary_chain.py (LLM summary, optional)
                              ↓
                    pdf_renderer.py (fpdf2 for PDF, Jinja2 for HTML)
```

---

## Supported Intents & Queries

### Spending & Income Analysis
| Intent | Example Query |
|--------|---------------|
| `total_spending` | "How much did customer 123 spend?" |
| `total_income` | "What is customer 123's total income?" |
| `spending_by_category` | "How much did customer 123 spend on Groceries?" |
| `all_categories_spending` | "Show all category spending for customer 123" |
| `top_categories` | "What are the top 5 spending categories for customer 123?" |
| `spending_in_period` | "Customer 123 spending from Jan to March 2024" |

### Financial Analysis
| Intent | Example Query |
|--------|---------------|
| `financial_overview` | "Give me a financial overview of customer 123" |
| `cash_flow` | "Show cash flow for customer 123" |
| `credit_analysis` | "Analyze credits for customer 123" |
| `debit_analysis` | "Analyze debits for customer 123" |
| `income_stability` | "How stable is customer 123's income?" |
| `balance_trend` | "Show balance trend for customer 123" |
| `anomaly_detection` | "Detect anomalies in customer 123's transactions" |

### Reports & Lookups
| Intent | Example Query |
|--------|---------------|
| `customer_report` | "Generate a full report for customer 123" |
| `lender_profile` | "Create a lender profile for customer 123" |
| `category_presence_lookup` | "Does customer 123 have any EMI payments?" |
| `list_customers` | "Show all customers" |
| `list_categories` | "List all categories" |

---

## Project Structure

```
├── config/
│   ├── settings.py           # Model & path configuration
│   ├── intents.py            # Intent → Tool mapping
│   └── category_loader.py    # Category configuration
│
├── pipeline/
│   ├── orchestrator.py       # Main pipeline coordinator
│   ├── intent_parser.py      # NL → structured intent
│   ├── planner.py            # Intent → execution plan
│   ├── executor.py           # Tool execution
│   ├── explainer.py          # Response generation (streaming)
│   ├── audit.py              # Query logging
│   ├── customer_report_builder.py  # Report data collection
│   ├── report_summary_chain.py     # LLM summaries (LCEL)
│   ├── report_orchestrator.py      # Report generation coordinator
│   ├── pdf_renderer.py       # PDF/HTML rendering
│   └── transaction_flow.py   # Transaction insights
│
├── schemas/
│   ├── intent.py             # IntentType enum, ParsedIntent
│   ├── customer_report.py    # Report data schema
│   ├── response.py           # ToolResult, PipelineResponse
│   └── transaction_summary.py # Transaction analysis schemas
│
├── tools/
│   ├── analytics.py          # Spending, cashflow analytics
│   ├── income.py             # Income analysis tools
│   ├── category_resolver.py  # Category presence detection
│   ├── transaction_fetcher.py # Transaction grouping (fuzzy)
│   └── lookup.py             # Customer/category lookups
│
├── templates/
│   └── customer_report.html  # Jinja2 report template
│
├── utils/
│   ├── helpers.py            # Utility functions, ID masking
│   ├── narration_utils.py    # Transaction narration parsing
│   └── transaction_filter.py # Transaction filtering
│
├── data/
│   └── sample_transactions.csv
│
├── reports/                  # Generated PDF reports
├── logs/                     # Audit logs
└── main.py                   # Entry point
```

---

## Configuration

All settings are centralized in `config/settings.py`:

```python
# Model Configuration
PARSER_MODEL = "mistral"      # Intent parsing model
EXPLAINER_MODEL = "llama3.2"  # Explanation & summary model

# Paths
DATA_DIR = "data"
TRANSACTIONS_FILE = "data/sample_transactions.csv"
LOG_DIR = "logs"

# Settings
VERBOSE_MODE = True
STREAMING_ENABLED = True
USE_LLM_EXPLAINER = True
```

---

## Installation

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.ai/) installed and running

### Setup

```bash
# Clone the repository
git clone <repo-url>
cd langchain_agentic_v3

# Install dependencies
pip install -r requirements.txt

# Pull required models
ollama pull mistral
ollama pull llama3.2

# Start Ollama server
ollama serve
```

### Dependencies
- `langchain` & `langchain-ollama` - LLM integration
- `pydantic` - Data validation
- `pandas` - Data manipulation
- `fpdf2` - PDF generation
- `jinja2` - HTML templating
- `fuzzywuzzy` - Fuzzy string matching

---

## Usage

### Interactive Mode

```bash
python main.py
# Select option 2 for interactive mode
```

### Programmatic Usage

```python
from pipeline import TransactionPipeline

# Initialize pipeline
pipeline = TransactionPipeline(verbose=True)

# Query with streaming
for chunk in pipeline.query_stream("What are customer 9449274898's top spending categories?"):
    print(chunk, end='', flush=True)

# Generate PDF report
from pipeline.report_orchestrator import generate_customer_report_pdf
report, pdf_path = generate_customer_report_pdf(9449274898)
print(f"Report saved to: {pdf_path}")
```

### Configuration Options

```python
pipeline = TransactionPipeline(
    parser_model="mistral",      # Model for intent parsing
    explainer_model="llama3.2",  # Model for explanations
    use_llm_explainer=True,      # Use LLM for responses
    verbose=True,                # Print debug info
    stream_delay=0.025           # Delay between streaming chunks
)
```

---

## Report Features

Generated PDF reports include:

| Section | Description |
|---------|-------------|
| **Customer Profile** | LLM-generated persona description |
| **Executive Summary** | LLM-generated financial review |
| **Salary Information** | Average, frequency, latest transaction |
| **Spending by Category** | All categories with amounts |
| **Monthly Cash Flow** | Inflow/outflow/net by month |
| **EMI Payments** | Detected loan payments |
| **Rent Payments** | Detected rent transactions |
| **Utility Bills** | Detected bill payments |
| **Top Merchants** | Most frequent transaction recipients |

Reports are saved as both PDF and HTML in the `reports/` directory.

---

## Adding New Features

1. **Add Intent**: Update `schemas/intent.py` with new `IntentType`
2. **Update Parser Prompt**: Modify `pipeline/intent_parser.py` prompt
3. **Map to Tools**: Add mapping in `config/intents.py`
4. **Create Tool**: Implement in `tools/` directory
5. **Register Tool**: Add to executor's `tool_map` in `pipeline/executor.py`
6. **Update Report** (optional): Modify `schemas/customer_report.py` and templates

---

## Data Format

Expected transaction CSV columns:

| Column | Description |
|--------|-------------|
| `cust_id` | Customer identifier |
| `prty_name` | Party/customer name |
| `tran_date` | Transaction date |
| `tran_amt_in_ac` | Transaction amount |
| `dr_cr_indctor` | Direction: 'D' (debit) or 'C' (credit) |
| `tran_partclr` | Transaction narration/description |
| `category_of_txn` | Transaction category |

---

## License

MIT License
