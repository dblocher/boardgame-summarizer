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
from colorama import init, Fore, Back, Style

# Initialize colorama for cross-platform color support
init(autoreset=True)


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
        print(f"{Fore.CYAN}🌐 Fetching HTML from: {Style.BRIGHT}{url}")

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            print(f"{Fore.GREEN}✓ Successfully fetched {Fore.YELLOW}{len(response.text):,}{Fore.GREEN} characters")
            return response.text

        except requests.exceptions.RequestException as e:
            print(f"{Fore.RED}✗ Error fetching URL: {e}", file=sys.stderr)
            sys.exit(1)

    def send_to_api(self, html_content: str) -> Dict[str, Any]:
        """
        Send HTML content to the API for processing.

        Args:
            html_content: Raw HTML content

        Returns:
            API response as dictionary
        """
        print(f"\n{Fore.CYAN}🚀 Sending HTML to API...")
        print(f"{Fore.BLUE}   Endpoint: {Style.DIM}{self.api_endpoint}")

        try:
            response = requests.post(
                self.api_endpoint,
                data=html_content,
                headers={'Content-Type': 'text/html'},
                timeout=300  # 5 minutes for Bedrock processing
            )
            response.raise_for_status()

            print(f"{Fore.GREEN}✓ API response received")
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"{Fore.RED}✗ Error calling API: {e}", file=sys.stderr)
            if hasattr(e, 'response') and e.response is not None:
                print(f"{Fore.RED}Response: {e.response.text}", file=sys.stderr)
            sys.exit(1)

    def display_results(self, results: Dict[str, Any]):
        """
        Display the comparison results in a readable format.

        Args:
            results: API response containing model comparisons
        """
        print("\n" + Style.BRIGHT + Fore.CYAN + "═" * 80)
        print(f"{Style.BRIGHT}{Fore.WHITE}🎲 BOARD GAME SUMMARIZER - MODEL COMPARISON RESULTS")
        print(Style.BRIGHT + Fore.CYAN + "═" * 80 + Style.RESET_ALL)

        print(f"\n{Fore.BLUE}📊 Text extracted: {Fore.YELLOW}{results.get('text_length', 0):,}{Fore.BLUE} characters")
        print(f"{Fore.BLUE}🤖 Models compared: {Fore.YELLOW}{results.get('models_compared', 0)}")

        model_results = results.get('results', [])

        for i, result in enumerate(model_results, 1):
            print(f"\n{Style.BRIGHT}{Fore.MAGENTA}{'─' * 80}")
            print(f"{Style.BRIGHT}{Fore.MAGENTA}🔮 MODEL {i}: {Fore.WHITE}{result['model_id']}")
            print(f"{Style.BRIGHT}{Fore.MAGENTA}{'─' * 80}{Style.RESET_ALL}")

            if result.get('success'):
                print(f"\n{Style.BRIGHT}{Fore.GREEN}📝 Summary:{Style.RESET_ALL}")
                # Wrap the summary text with slight indentation
                summary_lines = result['summary'].split('\n')
                for line in summary_lines:
                    print(f"{Fore.WHITE}   {line}")

                metrics = result.get('metrics', {})
                print(f"\n{Style.BRIGHT}{Fore.CYAN}⚡ Performance Metrics:{Style.RESET_ALL}")
                print(f"{Fore.BLUE}   ⏱️  Latency: {Fore.YELLOW}{metrics.get('latency_seconds', 0):.2f}s")
                print(f"{Fore.BLUE}   📥 Input tokens: {Fore.YELLOW}{metrics.get('input_tokens', 0):,}")
                print(f"{Fore.BLUE}   📤 Output tokens: {Fore.YELLOW}{metrics.get('output_tokens', 0):,}")
                print(f"{Fore.BLUE}   📏 Output length: {Fore.YELLOW}{metrics.get('output_length', 0):,} {Fore.BLUE}characters")
            else:
                print(f"\n{Fore.RED}❌ ERROR: {result.get('error', 'Unknown error')}")
                print(f"{Fore.YELLOW}⏱️  Latency: {result.get('metrics', {}).get('latency_seconds', 0):.2f}s")

        print("\n" + Style.BRIGHT + Fore.CYAN + "═" * 80 + Style.RESET_ALL + "\n")

    def process_boardgame(self, url: str):
        """
        Complete workflow: fetch HTML, send to API, display results.

        Args:
            url: BoardGameGeek game URL
        """
        # Validate URL
        parsed = urlparse(url)
        if 'boardgamegeek.com' not in parsed.netloc:
            print(f"{Fore.YELLOW}⚠️  Warning: URL doesn't appear to be from BoardGameGeek", file=sys.stderr)

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
