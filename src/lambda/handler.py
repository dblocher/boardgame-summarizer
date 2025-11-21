import json
import os
import re
import time
import boto3
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

def extract_text_from_html(html_content):
    """
    Extract relevant text content from BoardGameGeek HTML.
    BoardGameGeek uses Angular and embeds game data in JavaScript variables.
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract metadata from meta tags
        meta_description = soup.find('meta', {'name': 'description'})
        description = meta_description.get('content', '') if meta_description else ''

        title_tag = soup.find('title')
        title = title_tag.text if title_tag else ''

        # Try to extract structured data from GEEK.geekitemPreload JavaScript variable
        game_data = {}
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'GEEK.geekitemPreload' in script.string:
                script_text = script.string
                # Extract the JSON data - it's between GEEK.geekitemPreload = { and };
                start = script_text.find('GEEK.geekitemPreload = ')
                if start != -1:
                    start += len('GEEK.geekitemPreload = ')
                    # Find the closing brace - this is tricky, so we'll extract a large chunk
                    json_str = script_text[start:start+50000]  # Get a large chunk
                    try:
                        # Try to parse it as JSON
                        # Find where the object likely ends
                        match = re.search(r'\};[\s\n]*GEEK\.', json_str)
                        if match:
                            json_str = json_str[:match.start()+1]
                        game_data = json.loads(json_str)
                        logger.info(f"Successfully extracted structured game data")
                    except:
                        logger.warning("Could not parse structured game data")
                break

        # Build text summary from extracted data
        text_parts = [title, description]

        if game_data and 'item' in game_data:
            item = game_data['item']

            # Add basic info
            if 'name' in item:
                text_parts.append(f"Game: {item['name']}")
            if 'yearpublished' in item:
                text_parts.append(f"Year: {item['yearpublished']}")
            if 'minplayers' in item and 'maxplayers' in item:
                text_parts.append(f"Players: {item['minplayers']}-{item['maxplayers']}")
            if 'minplaytime' in item and 'maxplaytime' in item:
                text_parts.append(f"Playtime: {item['minplaytime']}-{item['maxplaytime']} minutes")
            if 'minage' in item:
                text_parts.append(f"Age: {item['minage']}+")
            if 'short_description' in item:
                text_parts.append(f"Description: {item['short_description']}")

            # Add links (designers, publishers, categories, mechanisms)
            if 'links' in item:
                links = item['links']

                if 'boardgamedesigner' in links:
                    designers = [d['name'] for d in links['boardgamedesigner']]
                    text_parts.append(f"Designers: {', '.join(designers)}")

                if 'boardgamepublisher' in links:
                    publishers = [p['name'] for p in links['boardgamepublisher'][:5]]  # Limit to 5
                    text_parts.append(f"Publishers: {', '.join(publishers)}")

                if 'boardgamecategory' in links:
                    categories = [c['name'] for c in links['boardgamecategory']]
                    text_parts.append(f"Categories: {', '.join(categories)}")

                if 'boardgamemechanic' in links:
                    mechanics = [m['name'] for m in links['boardgamemechanic']]
                    text_parts.append(f"Mechanisms: {', '.join(mechanics)}")

                if 'boardgamefamily' in links:
                    families = [f['name'] for f in links['boardgamefamily'][:10]]  # Limit to 10
                    text_parts.append(f"Families/Themes: {', '.join(families)}")

            # Add poll data
            if 'polls' in item:
                polls = item['polls']
                if 'userplayers' in polls:
                    best_players = polls['userplayers'].get('best', [])
                    if best_players:
                        text_parts.append(f"Best with: {best_players}")
                if 'playerage' in polls:
                    text_parts.append(f"Community suggested age: {polls['playerage']}")
                if 'boardgameweight' in polls:
                    weight = polls['boardgameweight'].get('averageweight', 0)
                    text_parts.append(f"Complexity (1-5): {weight:.2f}")

        text = ' '.join(text_parts)
        logger.info(f"Extracted text length: {len(text)} characters")

        return text
    except Exception as e:
        logger.error(f"Error extracting text from HTML: {str(e)}", exc_info=True)
        raise

def invoke_bedrock_model(model_id, text_content):
    """
    Invoke a single Bedrock model and return the response with metrics.
    """
    start_time = time.time()

    try:
        # Prepare the prompt
        prompt = f"""Please analyze this board game information and provide a concise summary including:
- Theme and setting
- Core mechanics
- Number of players
- Type of players who would enjoy this game (e.g., strategy enthusiasts, casual gamers, families, etc.)

Board game information:
{text_content[:8000]}

Please provide a natural, engaging paragraph summarizing this game."""

        # Build request body based on model family
        if 'anthropic.claude' in model_id:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "temperature": 0.7,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
        else:
            # Generic format for other models
            request_body = {
                "prompt": prompt,
                "max_tokens_to_sample": 1000,
                "temperature": 0.7
            }

        # Invoke the model
        logger.info(f"Invoking model: {model_id}")
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )

        # Parse response
        response_body = json.loads(response['body'].read())

        # Extract completion based on model family
        if 'anthropic.claude' in model_id:
            completion = response_body['content'][0]['text']
            input_tokens = response_body.get('usage', {}).get('input_tokens', 0)
            output_tokens = response_body.get('usage', {}).get('output_tokens', 0)
        else:
            completion = response_body.get('completion', response_body.get('results', [{}])[0].get('outputText', ''))
            input_tokens = response_body.get('input_tokens', 0)
            output_tokens = response_body.get('output_tokens', 0)

        elapsed_time = time.time() - start_time

        return {
            "model_id": model_id,
            "success": True,
            "summary": completion.strip(),
            "metrics": {
                "latency_seconds": round(elapsed_time, 2),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "output_length": len(completion)
            }
        }

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Error invoking model {model_id}: {str(e)}")
        return {
            "model_id": model_id,
            "success": False,
            "error": str(e),
            "metrics": {
                "latency_seconds": round(elapsed_time, 2)
            }
        }

def compare_models(text_content, models):
    """
    Compare multiple Bedrock models by invoking each and collecting results.
    """
    results = []

    for model_id in models:
        result = invoke_bedrock_model(model_id, text_content)
        results.append(result)

    return results

def lambda_handler(event, context):
    """
    Lambda handler for processing board game HTML and generating summaries.
    """
    try:
        logger.info(f"Received event: {json.dumps(event, default=str)}")

        # Extract HTML from request body
        if 'body' not in event:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Missing request body'})
            }

        html_content = event['body']

        # Handle base64 encoding if present
        if event.get('isBase64Encoded', False):
            import base64
            html_content = base64.b64decode(html_content).decode('utf-8')

        logger.info(f"Received HTML content length: {len(html_content)} characters")

        # Extract text from HTML
        text_content = extract_text_from_html(html_content)

        if len(text_content) < 100:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Insufficient text content extracted from HTML'})
            }

        # Get models from environment variable
        models_str = os.environ.get('BEDROCK_MODELS', 'anthropic.claude-3-5-sonnet-20241022-v2:0')
        models = [m.strip() for m in models_str.split(',')]

        logger.info(f"Comparing {len(models)} models: {models}")

        # Compare models
        comparison_results = compare_models(text_content, models)

        # Prepare response
        response_body = {
            'text_length': len(text_content),
            'models_compared': len(models),
            'results': comparison_results
        }

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_body, indent=2)
        }

    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }
