# Board Game Summarizer

Multi-model AI-powered board game analysis using AWS Bedrock. This project fetches board game information from BoardGameGeek and generates summaries using multiple foundation models for comparison.

## Architecture

```
Python Client → API Gateway → Lambda → AWS Bedrock (Multiple Models) → Response
```

### Components

1. **Python Client** (`client/boardgame_client.py`): Fetches HTML from BoardGameGeek and calls the API
2. **API Gateway**: REST API endpoint (`/summarize`)
3. **Lambda Function**: Processes HTML, extracts text with BeautifulSoup, invokes Bedrock models
4. **AWS Bedrock**: Generates summaries using multiple foundation models for comparison

### Default Models

- **Claude 3.5 Sonnet** (`anthropic.claude-3-5-sonnet-20241022-v2:0`) - High capability
- **Claude 3 Haiku** (`anthropic.claude-3-haiku-20240307-v1:0`) - Fast and cost-effective

## Prerequisites

- AWS Account with Bedrock access
- AWS CLI configured with SSO
- Python 3.11+
- AWS SAM CLI
- Models enabled in Bedrock (us-east-1):
  - Anthropic Claude 3.5 Sonnet
  - Anthropic Claude 3 Haiku

## Setup Instructions

### 1. Enable Bedrock Models

Before deploying, ensure you have access to the required models:

1. Go to [AWS Bedrock Console](https://console.aws.amazon.com/bedrock/)
2. Navigate to "Model access" in the left sidebar
3. Click "Manage model access"
4. Enable:
   - Anthropic Claude 3.5 Sonnet v2
   - Anthropic Claude 3 Haiku
5. Wait for "Access granted" status

### 2. Build and Deploy with SAM

```bash
# Ensure you're logged in with AWS SSO
aws sso login --profile <your-profile-name>

# Build the Lambda function
sam build

# Deploy to AWS
sam deploy --guided
```

During the guided deployment:
- Accept default stack name: `boardgame-summarizer`
- Accept default region: `us-east-1`
- Confirm changes before deploy: `Y`
- Allow SAM CLI IAM role creation: `Y`
- Disable rollback: `N`
- Save arguments to config: `Y`

After deployment completes, note the **ApiEndpoint** output value.

### 3. Configure the Python Client

Create a config file with your API endpoint:

```bash
# Copy the ApiEndpoint from SAM output
echo '{
  "api_endpoint": "https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/prod/summarize"
}' > client/config.json
```

### 4. Install Client Dependencies

```bash
cd client
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python client/boardgame_client.py "https://boardgamegeek.com/boardgame/224517/brass-birmingham"
```

### With Custom API Endpoint

```bash
python client/boardgame_client.py \
  --api-endpoint "https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/prod/summarize" \
  "https://boardgamegeek.com/boardgame/174430/gloomhaven"
```

### Example Output

```
Fetching HTML from: https://boardgamegeek.com/boardgame/224517/brass-birmingham
Successfully fetched 245832 characters

Sending HTML to API: https://abc123.execute-api.us-east-1.amazonaws.com/prod/summarize

================================================================================
BOARD GAME SUMMARIZER - MODEL COMPARISON RESULTS
================================================================================

Text extracted: 52341 characters
Models compared: 2

--------------------------------------------------------------------------------
MODEL 1: anthropic.claude-3-5-sonnet-20241022-v2:0
--------------------------------------------------------------------------------

Summary:
Brass: Birmingham is an economic strategy game set in Birmingham during the Industrial
Revolution. Players build industries, develop canal and rail networks, and sell goods
to fuel their economic engine. The game features deep strategic planning with card-driven
actions and a two-era structure...

Metrics:
  - Latency: 4.23 seconds
  - Input tokens: 1250
  - Output tokens: 342
  - Output length: 1543 characters

--------------------------------------------------------------------------------
MODEL 2: anthropic.claude-3-haiku-20240307-v1:0
--------------------------------------------------------------------------------

Summary:
Set in industrial-era Birmingham, this heavy euro game challenges 2-4 players to build
businesses, establish trade networks, and dominate industries...

Metrics:
  - Latency: 2.18 seconds
  - Input tokens: 1250
  - Output tokens: 298
  - Output length: 1342 characters

================================================================================
```

## Customization

### Change Bedrock Models

Edit [template.yaml](template.yaml) and update the `BEDROCK_MODELS` environment variable:

```yaml
Environment:
  Variables:
    BEDROCK_MODELS: "anthropic.claude-3-opus-20240229-v1:0,anthropic.claude-3-sonnet-20240229-v1:0"
```

Then redeploy:

```bash
sam build && sam deploy
```

### Adjust Lambda Timeout or Memory

Edit [template.yaml](template.yaml) in the `Globals` section:

```yaml
Globals:
  Function:
    Timeout: 600  # 10 minutes
    MemorySize: 1024  # 1GB
```

## Project Structure

```
boardgame-summarizer/
├── .mcp.json                    # MCP server configuration
├── template.yaml                # SAM template
├── samconfig.toml              # SAM deployment config
├── README.md                   # This file
├── src/
│   └── lambda/
│       ├── handler.py          # Lambda function code
│       └── requirements.txt    # Lambda dependencies
└── client/
    ├── boardgame_client.py     # Python client application
    ├── requirements.txt        # Client dependencies
    └── config.json             # API endpoint configuration (created during setup)
```

## Development

### Local Testing

You can test the Lambda function locally using SAM:

```bash
# Start local API
sam local start-api

# In another terminal, test with curl
curl -X POST http://localhost:3000/summarize \
  -H "Content-Type: text/html" \
  --data @test_page.html
```

### View Lambda Logs

```bash
sam logs -n BoardGameSummarizerFunction --stack-name boardgame-summarizer --tail
```

## Cost Considerations

- **API Gateway**: ~$3.50 per million requests
- **Lambda**: ~$0.20 per million requests (512MB, 30s average)
- **Bedrock Claude 3.5 Sonnet**: ~$3 per million input tokens, ~$15 per million output tokens
- **Bedrock Claude 3 Haiku**: ~$0.25 per million input tokens, ~$1.25 per million output tokens

Typical cost per request: **$0.01 - $0.05** depending on HTML size and models used.

## Troubleshooting

### "Model not found" errors

Ensure you've enabled model access in the Bedrock console for your region.

### API Gateway timeout

Increase Lambda timeout in [template.yaml](template.yaml) if processing large pages.

### Client connection errors

Verify the API endpoint URL in `client/config.json` matches the SAM output.

### AWS SSO session expired

```bash
aws sso login --profile <your-profile-name>
```

## Cleanup

To delete all AWS resources:

```bash
sam delete --stack-name boardgame-summarizer
```

## License

MIT

## Contributing

Feel free to open issues or submit pull requests for improvements!
