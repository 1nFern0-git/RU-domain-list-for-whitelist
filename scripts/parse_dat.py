#!/usr/bin/env python3
"""
Parse .dat files (geosite.dat and geoip.dat) from v2ray/xray
Extracts specific categories and converts them to intermediate format
"""

import os
import sys
import requests
import argparse
from pathlib import Path

# Add scripts directory to path for importing proto files
sys.path.insert(0, str(Path(__file__).parent))
import common_pb2


def download_file(url, output_path):
    """Download a file from URL to output_path"""
    print(f"Downloading {url}...")
    response = requests.get(url, stream=True, timeout=30)
    response.raise_for_status()
    
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print(f"✓ Downloaded to {output_path}")


def get_latest_release_assets(repo):
    """Get download URLs for latest release assets"""
    api_url = f"https://api.github.com/repos/{repo}/releases/latest"
    print(f"Fetching latest release from {repo}...")
    
    response = requests.get(api_url, timeout=30)
    response.raise_for_status()
    
    release_data = response.json()
    assets = {}
    
    for asset in release_data['assets']:
        name = asset['name']
        if name == 'geosite.dat' or name == 'geoip.dat':
            assets[name] = asset['browser_download_url']
    
    return assets


def parse_geosite_dat(dat_file, categories):
    """Parse geosite.dat and extract specified categories"""
    print(f"\nParsing {dat_file}...")
    
    with open(dat_file, 'rb') as f:
        data = f.read()
    
    geosite_list = common_pb2.GeoSiteList()
    geosite_list.ParseFromString(data)
    
    extracted = {}
    found_categories = set()
    
    # Create case-insensitive lookup
    categories_lower = {cat.lower(): cat for cat in categories}
    
    for entry in geosite_list.entry:
        category_name = entry.country_code or entry.code
        found_categories.add(category_name)
        
        # Check case-insensitive
        if category_name.lower() in categories_lower:
            original_cat = categories_lower[category_name.lower()]
            print(f"  ✓ Found category: {category_name} ({len(entry.domain)} domains)")
            extracted[original_cat] = entry
    
    # Print all available categories for debugging
    print(f"\n  Available categories in file: {sorted(found_categories)}")
    
    # Warn about missing categories (case-insensitive check)
    found_lower = {cat.lower() for cat in found_categories}
    missing = set()
    for cat in categories:
        if cat.lower() not in found_lower:
            missing.add(cat)
    
    if missing:
        print(f"  ⚠ Warning: Categories not found: {missing}")
    
    return extracted


def parse_geoip_dat(dat_file, categories):
    """Parse geoip.dat and extract specified categories"""
    print(f"\nParsing {dat_file}...")
    
    with open(dat_file, 'rb') as f:
        data = f.read()
    
    geoip_list = common_pb2.GeoIPList()
    geoip_list.ParseFromString(data)
    
    extracted = {}
    found_categories = set()
    
    # Create case-insensitive lookup
    categories_lower = {cat.lower(): cat for cat in categories}
    
    for entry in geoip_list.entry:
        category_name = entry.country_code or entry.code
        found_categories.add(category_name)
        
        # Check case-insensitive
        if category_name.lower() in categories_lower:
            original_cat = categories_lower[category_name.lower()]
            print(f"  ✓ Found category: {category_name} ({len(entry.cidr)} CIDR blocks)")
            extracted[original_cat] = entry
    
    # Print all available categories for debugging
    print(f"\n  Available categories in file: {sorted(found_categories)}")
    
    # Warn about missing categories (case-insensitive check)
    found_lower = {cat.lower() for cat in found_categories}
    missing = set()
    for cat in categories:
        if cat.lower() not in found_lower:
            missing.add(cat)
    
    if missing:
        print(f"  ⚠ Warning: Categories not found: {missing}")
    
    return extracted


def main():
    parser = argparse.ArgumentParser(description='Parse v2ray .dat files')
    parser.add_argument('--source-repo', default='runetfreedom/russia-v2ray-rules-dat',
                        help='Source repository for .dat files')
    parser.add_argument('--geosite-categories', nargs='+',
                        default=['category-ru', 'ru-blocked', 'ru-available-only-inside', 'category-ads-all'],
                        help='GeoSite categories to extract')
    parser.add_argument('--geoip-categories', nargs='+',
                        default=['ru', 'ru-blocked', 'private'],
                        help='GeoIP categories to extract')
    parser.add_argument('--output-dir', default='output',
                        help='Output directory for extracted data')
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Download latest release files
    try:
        assets = get_latest_release_assets(args.source_repo)
    except Exception as e:
        print(f"Error fetching release: {e}")
        sys.exit(1)
    
    # Download geosite.dat
    geosite_path = output_dir / 'source_geosite.dat'
    if 'geosite.dat' in assets:
        download_file(assets['geosite.dat'], geosite_path)
    else:
        print("Error: geosite.dat not found in release")
        sys.exit(1)
    
    # Download geoip.dat
    geoip_path = output_dir / 'source_geoip.dat'
    if 'geoip.dat' in assets:
        download_file(assets['geoip.dat'], geoip_path)
    else:
        print("Error: geoip.dat not found in release")
        sys.exit(1)
    
    # Parse and extract categories
    geosite_data = parse_geosite_dat(geosite_path, args.geosite_categories)
    geoip_data = parse_geoip_dat(geoip_path, args.geoip_categories)
    
    # Save extracted data as serialized protobuf
    geosite_extracted = common_pb2.GeoSiteList()
    for category_name, entry in geosite_data.items():
        geosite_extracted.entry.append(entry)
    
    extracted_geosite_path = output_dir / 'extracted_geosite.dat'
    with open(extracted_geosite_path, 'wb') as f:
        f.write(geosite_extracted.SerializeToString())
    print(f"\n✓ Saved extracted geosite data to {extracted_geosite_path}")
    
    geoip_extracted = common_pb2.GeoIPList()
    for category_name, entry in geoip_data.items():
        geoip_extracted.entry.append(entry)
    
    extracted_geoip_path = output_dir / 'extracted_geoip.dat'
    with open(extracted_geoip_path, 'wb') as f:
        f.write(geoip_extracted.SerializeToString())
    print(f"✓ Saved extracted geoip data to {extracted_geoip_path}")
    
    print("\n✅ Parsing complete!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
