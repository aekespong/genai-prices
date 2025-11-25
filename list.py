#!/usr/bin/env python3
"""
List prices for LLMs from the data.json file.

Usage:
    python list.py [filter] [--sort]

The filter argument (optional) will match against:
  - Provider names/IDs (case-insensitive)
  - Model names/IDs (case-insensitive)

The --sort flag (optional) will sort all prices and models by the sum of 
input and output prices (lowest first).

Examples:
    python list.py              # List all providers and models
    python list.py anthropic    # List only Anthropic models
    python list.py google       # List only Google models
    python list.py claude       # List models containing 'claude'
    python list.py haiku        # List models containing 'haiku'
    python list.py anthropic --sort   # List Anthropic sorted by price
    python list.py all --sort   # List all models sorted by price
"""

import json
import sys
from pathlib import Path


def load_data():
    """Load the prices data from data.json."""
    data_path = Path(__file__).parent / "prices" / "data.json"
    with open(data_path) as f:
        return json.load(f)


def matches_filter(text:str, filter_str:str):
    """Check if text matches the filter (case-insensitive)."""
    return filter_str.lower() in text.lower()


def format_price(price_value):
    """Format a price value, return empty string if None or invalid."""
    if price_value is None:
        return ""
    try:
        return f"${float(price_value):.2f}"
    except (TypeError, ValueError):
        return ""


def list_prices(filter_str: str, sort_by_price: bool = False):
    """List prices for all providers and models, optionally filtered and sorted."""
    data = load_data()
    
    # If "all" is passed, treat as empty filter (list everything)
    if filter_str.lower() == "all":
        filter_str = ""
    
    matched_any = False
    current_provider = None
    table_rows: list[dict[str, str | float]] = []
    all_rows: list[dict[str, str | float]] = []  # For sorting across providers
    
    for provider in data:
        provider_id = provider.get("id", "")
        provider_name = provider.get("name", "")
        
        # Check if provider matches filter
        provider_matches = (
            filter_str == ""
            or ( matches_filter(provider_id, filter_str))
            or ( matches_filter(provider_name, filter_str))
        )
        
        if not provider_matches:
            # Check if any models match the filter
            models = provider.get("models", [])
            has_matching_models = any(
                matches_filter(model.get("id", ""), filter_str)
                or matches_filter(model.get("name", ""), filter_str)
                for model in models
            )
            if not has_matching_models:
                continue
        
        # List models
        models = provider.get("models", [])
        for model in models:
            model_id = model.get("id", "")
            model_name = model.get("name", "")
            
            # Check if model matches filter (but skip this check if provider already matched)
            if not provider_matches and filter_str != "":
                model_matches = (
                    matches_filter(model_id, filter_str)
                    or matches_filter(model_name, filter_str)
                )
                if not model_matches:
                    continue
            
            matched_any = True
            prices_raw = model.get("prices", {})
            
            # Handle prices that might be a dict or a list
            if isinstance(prices_raw, list):
                prices = {}  # Skip models with list prices
            elif isinstance(prices_raw, dict):
                prices = prices_raw
            else:
                prices = {}
            
            # Collect price columns
            input_price = format_price(prices.get("input_mtok"))
            write_price = format_price(prices.get("cache_write_mtok"))
            read_price = format_price(prices.get("cache_read_mtok"))
            out_price = format_price(prices.get("output_mtok"))
            
            # Calculate sum of input and output for sorting
            input_val = 0.0
            output_val = 0.0
            try:
                input_raw = prices.get("input_mtok", 0)
                output_raw = prices.get("output_mtok", 0)
                input_val = float(input_raw) if input_raw and isinstance(input_raw, (int, float, str)) else 0.0
                output_val = float(output_raw) if output_raw and isinstance(output_raw, (int, float, str)) else 0.0
            except (TypeError, ValueError):
                pass
            price_sum = input_val + output_val
            
            # Add row to table
            display_name = model_name if model_name else model_id
            row = {
                "Name": display_name,
                "Input": input_price,
                "Write": write_price,
                "Read": read_price,
                "Out": out_price,
                "Model": model_id,
                "PriceSum": price_sum,  # For sorting
            }
            all_rows.append(row)
            
            if not sort_by_price:
                # Print provider header if changed
                if current_provider != provider_name:
                    if table_rows:
                        # Print previous table
                        print_table(table_rows)
                        table_rows = []
                    current_provider = provider_name
                    print(f"\n{'='*120}")
                    print(f"Provider: {provider_name} ({provider_id})")
                    print(f"{'='*120}")
                table_rows.append(row)
    
    if sort_by_price:
        # Sort all rows by price sum (lowest first)
        all_rows.sort(key=lambda x: x["PriceSum"])  # type: ignore
        
        # Add provider name to each row for sorted output
        for row in all_rows:
            # Find the provider name from the original data
            for provider in data:
                for model in provider.get("models", []):
                    if model.get("id") == row.get("Model"):
                        row["Provider"] = provider.get("name", "")
                        break
        
        # Print all sorted rows with a single header
        print(f"\n{'='*120}")
        print("All Models Sorted by Price (Input + Output)")
        print(f"{'='*120}")
        print_table(all_rows)
    else:
        # Print remaining table
        if table_rows:
            print_table(table_rows)
    
    if filter_str and not matched_any:
        print(f"\nNo providers or models matching '{filter_str}' found.")
        return 1
    
    return 0


def print_table(rows):
    """Print a formatted table of model prices."""
    if not rows:
        return
    
    # Determine which columns to display
    has_provider = any("Provider" in row for row in rows)
    columns = ["Provider", "Name", "Input", "Write", "Read", "Out", "Model"] if has_provider else ["Name", "Input", "Write", "Read", "Out", "Model"]
    
    # Calculate column widths
    col_widths = {}
    for col in columns:
        col_widths[col] = max(
            len(col),
            max(len(str(row.get(col, ""))) for row in rows) if rows else len(col)
        )
    
    # Print header
    header = " | ".join(
        f"{col:<{col_widths[col]}}" if col in ["Name", "Model", "Provider"]
        else f"{col:>{col_widths[col]}}"
        for col in columns
    )
    separator = "-+-".join("-" * col_widths[col] for col in columns)
    
    print(header)
    print(separator)
    
    # Print rows
    for row in rows:  # type: ignore
        line = " | ".join(
            f"{str(row.get(col, '')):<{col_widths[col]}}" if col in ["Name", "Model", "Provider"]
            else f"{str(row.get(col, '')):>{col_widths[col]}}"
            for col in columns
        )
        print(line)


def main():
    """Main entry point."""
    
    filter_str = ""
    sort_by_price = False
    
    if len(sys.argv) > 1:
        # Parse arguments
        for arg in sys.argv[1:]:
            if arg == "--sort":
                sort_by_price = True
            else:
                filter_str = arg
    else:
        # No argument provided - show providers and ask for input
        data = load_data()
        
        # Prepare provider data with min/max prices
        providers = []
        for provider in data:
            provider_id = provider.get("id", "")
            provider_name = provider.get("name", "")
            models = provider.get("models", [])
            model_count = len(models)
            
            # Calculate min and max prices (sum of input + output)
            prices = []
            for model in models:
                prices_raw = model.get("prices", {})
                if isinstance(prices_raw, dict):
                    input_val = prices_raw.get("input_mtok", 0)
                    output_val = prices_raw.get("output_mtok", 0)
                    # Convert to float safely
                    try:
                        input_val = float(input_val) if input_val else 0.0
                        output_val = float(output_val) if output_val else 0.0
                        if input_val > 0 or output_val > 0:
                            prices.append(input_val + output_val)
                    except (TypeError, ValueError):
                        pass
            
            min_price = min(prices) if prices else 0.0
            max_price = max(prices) if prices else 0.0
            
            providers.append((provider_name, provider_id, model_count, min_price, max_price))
        
        # Calculate column widths
        max_name_len = max(len(p[0]) for p in providers)
        max_id_len = max(len(p[1]) for p in providers)
        
        # Print header
        total_width = max_name_len + max_id_len + 50
        print("=" * total_width)
        print("Available Providers:")
        print("=" * total_width)
        
        header = f"{'Name':<{max_name_len}} | {'ID':<{max_id_len}} | {'Models':>7} | {'Min Price':>10} | {'Max Price':>10}"
        separator = "-" * max_name_len + "-+-" + "-" * max_id_len + "-+-" + "-" * 7 + "-+-" + "-" * 10 + "-+-" + "-" * 10
        print(header)
        print(separator)
        
        # Print providers
        for name, provider_id, model_count, min_price, max_price in providers:
            min_str = f"${min_price:.2f}" if min_price > 0 else "N/A"
            max_str = f"${max_price:.2f}" if max_price > 0 else "N/A"
            print(f"{name:<{max_name_len}} | {provider_id:<{max_id_len}} | {model_count:>7} | {min_str:>10} | {max_str:>10}")
        
        print("=" * total_width)
        filter_str = input("Enter a filter (provider name/id, model name, or 'all'): ").strip()
        
        if not filter_str:
            print("No filter provided. Exiting.")
            return 0
    
    return list_prices(filter_str, sort_by_price)


if __name__ == "__main__":
    sys.exit(main())
