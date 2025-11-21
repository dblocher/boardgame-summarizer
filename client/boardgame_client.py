#!/usr/bin/env python3
"""
Board Game Summarizer Client

Fetches board game HTML from BoardGameGeek and sends it to the Bedrock API
for multi-model comparison and summarization.
"""

import argparse
import json
import sys
import requests
from urllib.parse import urlparse
from typing import Dict, Any


class BoardGameClient:
    def __init__(self, api_endpoint: str):
        """
        Initialize the client with the API Gateway endpoint.

        Args:
            api_endpoint: The full URL to the /summarize endpoint
        """
        self.api_endpoint = api_endpoint
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def fetch_boardgame_html(self, url: str) -> str:
        """
        Fetch HTML content from a BoardGameGeek URL.

        Args:
            url: BoardGameGeek game URL

        Returns:
            HTML content as string
        """
        print(f"Fetching HTML from: {url}")

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            print(f"Successfully fetched {len(response.text)} characters")
            return response.text

        except requests.exceptions.RequestException as e:
            print(f"Error fetching URL: {e}", file=sys.stderr)
            sys.exit(1)

    def send_to_api(self, html_content: str) -> Dict[str, Any]:
        """
        Send HTML content to the API for processing.

        Args:
            html_content: Raw HTML content

        Returns:
            API response as dictionary
        """
        print(f"\nSending HTML to API: {self.api_endpoint}")

        try:
            response = requests.post(
                self.api_endpoint,
                data=html_content,
                headers={'Content-Type': 'text/html'},
                timeout=300  # 5 minutes for Bedrock processing
            )
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"Error calling API: {e}", file=sys.stderr)
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}", file=sys.stderr)
            sys.exit(1)

    def display_results(self, results: Dict[str, Any]):
        """
        Display the comparison results in a readable format.

        Args:
            results: API response containing model comparisons
        """
        print("\n" + "=" * 80)
        print("BOARD GAME SUMMARIZER - MODEL COMPARISON RESULTS")
        print("=" * 80)

        print(f"\nText extracted: {results.get('text_length', 0)} characters")
        print(f"Models compared: {results.get('models_compared', 0)}")

        model_results = results.get('results', [])

        for i, result in enumerate(model_results, 1):
            print("\n" + "-" * 80)
            print(f"MODEL {i}: {result['model_id']}")
            print("-" * 80)

            if result.get('success'):
                print(f"\nSummary:")
                print(result['summary'])

                metrics = result.get('metrics', {})
                print(f"\nMetrics:")
                print(f"  - Latency: {metrics.get('latency_seconds', 0)} seconds")
                print(f"  - Input tokens: {metrics.get('input_tokens', 0)}")
                print(f"  - Output tokens: {metrics.get('output_tokens', 0)}")
                print(f"  - Output length: {metrics.get('output_length', 0)} characters")
            else:
                print(f"\n❌ ERROR: {result.get('error', 'Unknown error')}")
                print(f"Latency: {result.get('metrics', {}).get('latency_seconds', 0)} seconds")

        print("\n" + "=" * 80)

    def process_boardgame(self, url: str):
        """
        Complete workflow: fetch HTML, send to API, display results.

        Args:
            url: BoardGameGeek game URL
        """
        # Validate URL
        parsed = urlparse(url)
        if 'boardgamegeek.com' not in parsed.netloc:
            print("Warning: URL doesn't appear to be from BoardGameGeek", file=sys.stderr)

        # Fetch HTML
        html_content = self.fetch_boardgame_html(url)

        # Send to API
        results = self.send_to_api(html_content)

        # Display results
        self.display_results(results)


def main():
    parser = argparse.ArgumentParser(
        description='Fetch and summarize board games using AWS Bedrock multi-model comparison'
    )
    parser.add_argument(
        'url',
        help='BoardGameGeek URL (e.g., https://boardgamegeek.com/boardgame/224517/brass-birmingham)'
    )
    parser.add_argument(
        '--api-endpoint',
        help='API Gateway endpoint URL (default: reads from config or environment)',
        default=None
    )

    args = parser.parse_args()

    # Get API endpoint
    api_endpoint = args.api_endpoint
    if not api_endpoint:
        # Try to read from a config file or environment
        try:
            with open('client/config.json', 'r') as f:
                config = json.load(f)
                api_endpoint = config.get('api_endpoint')
        except FileNotFoundError:
            print("Error: API endpoint not provided and config.json not found", file=sys.stderr)
            print("\nPlease either:", file=sys.stderr)
            print("  1. Use --api-endpoint flag", file=sys.stderr)
            print("  2. Create client/config.json with your API endpoint", file=sys.stderr)
            sys.exit(1)

    if not api_endpoint:
        print("Error: API endpoint not configured", file=sys.stderr)
        sys.exit(1)

    # Create client and process
    client = BoardGameClient(api_endpoint)
    client.process_boardgame(args.url)


if __name__ == '__main__':
    main()
