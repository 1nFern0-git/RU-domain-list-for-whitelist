#!/usr/bin/env python3
"""
Build merged .dat files combining categories from source and whitelist
Creates geosite.dat and geoip.dat with all required categories
"""

import os
import sys
import re
import ipaddress
import argparse
from pathlib import Path

# Add scripts directory to path for importing proto files
sys.path.insert(0, str(Path(__file__).parent))
import common_pb2


def load_domains_from_file(filepath):
    """Load domains from a file, supporting v2ray domain list format"""
    domains = []
    
    if not filepath.exists():
        return domains
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse v2ray domain list format
                # Formats: domain.com, include:category, full:domain.com, regexp:pattern, keyword:word
                if line.startswith('include:'):
                    # Skip include directives - they should be in separate files
                    continue
                elif line.startswith('full:'):
                    # Full domain match
                    domain = line[5:].strip().split()[0]
                    domains.append(('full', domain))
                elif line.startswith('domain:'):
                    # Domain and subdomains
                    domain = line[7:].strip().split()[0]
                    domains.append(('domain', domain))
                elif line.startswith('regexp:'):
                    # Regular expression
                    pattern = line[7:].strip().split()[0]
                    domains.append(('regexp', pattern))
                elif line.startswith('keyword:'):
                    # Keyword match
                    keyword = line[8:].strip().split()[0]
                    domains.append(('keyword', keyword))
                else:
                    # Default: treat as domain
                    domain = line.split()[0].split('#')[0].strip()
                    if domain and '.' in domain:
                        # Check if it has attributes (e.g., @ads)
                        parts = line.split()
                        if len(parts) > 1 and parts[1].startswith('@'):
                            domains.append(('domain', domain))
                        else:
                            domains.append(('domain', domain))
    except Exception as e:
        print(f"  ⚠ Error reading {filepath}: {e}")
    
    return domains


def load_domains_from_directory(directory):
    """Load all domains from directory, recursively processing include directives"""
    all_domains = []
    processed_files = set()
    
    def process_file(filepath):
        if filepath in processed_files:
            return []
        processed_files.add(filepath)
        
        domains = []
        if not filepath.exists():
            print(f"  ⚠ File not found: {filepath}")
            return domains
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    
                    if not line or line.startswith('#'):
                        continue
                    
                    if line.startswith('include:'):
                        # Process included file
                        include_name = line[8:].strip()
                        include_path = filepath.parent / include_name
                        domains.extend(process_file(include_path))
                    else:
                        # Parse domain entry
                        if line.startswith('full:'):
                            domain = line[5:].strip().split()[0]
                            domains.append(('full', domain))
                        elif line.startswith('domain:'):
                            domain = line[7:].strip().split()[0]
                            domains.append(('domain', domain))
                        elif line.startswith('regexp:'):
                            pattern = line[7:].strip().split()[0]
                            domains.append(('regexp', pattern))
                        elif line.startswith('keyword:'):
                            keyword = line[8:].strip().split()[0]
                            domains.append(('keyword', keyword))
                        else:
                            domain = line.split()[0].split('#')[0].strip()
                            if domain and '.' in domain:
                                domains.append(('domain', domain))
        except Exception as e:
            print(f"  ⚠ Error processing {filepath}: {e}")
        
        return domains
    
    # Start with main file
    main_file = Path(directory)
    if main_file.is_file():
        all_domains = process_file(main_file)
    elif main_file.is_dir():
        # Process all files in directory
        for filepath in main_file.rglob('*'):
            if filepath.is_file() and not filepath.name.startswith('.'):
                all_domains.extend(process_file(filepath))
    
    return all_domains


def load_ips_from_directory(directory):
    """Load all IP CIDR blocks from directory"""
    cidrs = []
    
    directory = Path(directory)
    if not directory.exists():
        print(f"  ⚠ Directory not found: {directory}")
        return cidrs
    
    for filepath in directory.rglob('*.txt'):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip().split('#')[0].strip()
                    
                    if not line:
                        continue
                    
                    # Validate CIDR format
                    try:
                        network = ipaddress.ip_network(line, strict=False)
                        cidrs.append(str(network))
                    except ValueError:
                        # Try to parse as single IP
                        try:
                            ip = ipaddress.ip_address(line)
                            if ip.version == 4:
                                cidrs.append(f"{line}/32")
                            else:
                                cidrs.append(f"{line}/128")
                        except ValueError:
                            print(f"  ⚠ Invalid IP/CIDR: {line} in {filepath.name}")
        except Exception as e:
            print(f"  ⚠ Error reading {filepath}: {e}")
    
    return cidrs


def create_geosite_entry(category_name, domains):
    """Create a GeoSite entry from domain list"""
    entry = common_pb2.GeoSite()
    entry.country_code = category_name
    entry.code = category_name
    
    for domain_type, domain_value in domains:
        domain_entry = entry.domain.add()
        
        if domain_type == 'full':
            domain_entry.type = common_pb2.Domain.Full
            domain_entry.value = domain_value
        elif domain_type == 'regexp':
            domain_entry.type = common_pb2.Domain.Regex
            domain_entry.value = domain_value
        elif domain_type == 'keyword':
            domain_entry.type = common_pb2.Domain.Plain
            domain_entry.value = domain_value
        else:  # domain (root domain)
            domain_entry.type = common_pb2.Domain.RootDomain
            domain_entry.value = domain_value
    
    return entry


def create_geoip_entry(category_name, cidrs):
    """Create a GeoIP entry from CIDR list"""
    entry = common_pb2.GeoIP()
    entry.country_code = category_name
    entry.code = category_name
    
    for cidr_str in cidrs:
        try:
            network = ipaddress.ip_network(cidr_str, strict=False)
            cidr_entry = entry.cidr.add()
            cidr_entry.ip = network.network_address.packed
            cidr_entry.prefix = network.prefixlen
        except ValueError as e:
            print(f"  ⚠ Invalid CIDR {cidr_str}: {e}")
    
    return entry


def build_geosite_dat(extracted_path, whitelist_domains_path, whitelist_ads_path, output_path):
    """Build final geosite.dat combining extracted categories and whitelist"""
    print("\n=== Building geosite.dat ===")
    
    # Load extracted categories
    geosite_list = common_pb2.GeoSiteList()
    
    if Path(extracted_path).exists():
        with open(extracted_path, 'rb') as f:
            data = f.read()
        extracted_list = common_pb2.GeoSiteList()
        extracted_list.ParseFromString(data)
        
        print(f"Loaded {len(extracted_list.entry)} categories from extracted data:")
        for entry in extracted_list.entry:
            category = entry.country_code or entry.code
            print(f"  - {category}: {len(entry.domain)} domains")
            geosite_list.entry.append(entry)
    
    # Load whitelist domains
    print(f"\nLoading whitelist domains from {whitelist_domains_path}...")
    whitelist_domains = load_domains_from_directory(whitelist_domains_path)
    
    if whitelist_domains:
        print(f"  ✓ Loaded {len(whitelist_domains)} whitelist domains")
        whitelist_entry = create_geosite_entry('whitelist', whitelist_domains)
        geosite_list.entry.append(whitelist_entry)
    else:
        print("  ⚠ No whitelist domains found")
    
    # Load whitelist-ads domains
    print(f"\nLoading whitelist-ads domains from {whitelist_ads_path}...")
    whitelist_ads_domains = load_domains_from_directory(whitelist_ads_path)
    
    if whitelist_ads_domains:
        print(f"  ✓ Loaded {len(whitelist_ads_domains)} whitelist-ads domains")
        whitelist_ads_entry = create_geosite_entry('whitelist-ads', whitelist_ads_domains)
        geosite_list.entry.append(whitelist_ads_entry)
    else:
        print("  ⚠ No whitelist-ads domains found")
    
    # Save final geosite.dat
    with open(output_path, 'wb') as f:
        f.write(geosite_list.SerializeToString())
    
    print(f"\n✓ Built geosite.dat with {len(geosite_list.entry)} categories")
    print(f"  Saved to: {output_path}")


def build_geoip_dat(extracted_path, whitelist_ips_path, output_path):
    """Build final geoip.dat combining extracted categories and whitelist"""
    print("\n=== Building geoip.dat ===")
    
    # Load extracted categories
    geoip_list = common_pb2.GeoIPList()
    
    if Path(extracted_path).exists():
        with open(extracted_path, 'rb') as f:
            data = f.read()
        extracted_list = common_pb2.GeoIPList()
        extracted_list.ParseFromString(data)
        
        print(f"Loaded {len(extracted_list.entry)} categories from extracted data:")
        for entry in extracted_list.entry:
            category = entry.country_code or entry.code
            print(f"  - {category}: {len(entry.cidr)} CIDR blocks")
            geoip_list.entry.append(entry)
    
    # Load whitelist IPs
    print(f"\nLoading whitelist IPs from {whitelist_ips_path}...")
    whitelist_cidrs = load_ips_from_directory(whitelist_ips_path)
    
    if whitelist_cidrs:
        print(f"  ✓ Loaded {len(whitelist_cidrs)} whitelist CIDR blocks")
        whitelist_entry = create_geoip_entry('whitelist', whitelist_cidrs)
        geoip_list.entry.append(whitelist_entry)
    else:
        print("  ⚠ No whitelist IPs found")
    
    # Save final geoip.dat
    with open(output_path, 'wb') as f:
        f.write(geoip_list.SerializeToString())
    
    print(f"\n✓ Built geoip.dat with {len(geoip_list.entry)} categories")
    print(f"  Saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Build merged v2ray .dat files')
    parser.add_argument('--extracted-geosite', default='output/extracted_geosite.dat',
                        help='Path to extracted geosite data')
    parser.add_argument('--extracted-geoip', default='output/extracted_geoip.dat',
                        help='Path to extracted geoip data')
    parser.add_argument('--whitelist-domains', default='domains/ru/category-ru',
                        help='Path to whitelist domains directory/file')
    parser.add_argument('--whitelist-ads', default='domains/ads',
                        help='Path to whitelist-ads domains directory')
    parser.add_argument('--whitelist-ips', default='IPs',
                        help='Path to whitelist IPs directory')
    parser.add_argument('--output-dir', default='output',
                        help='Output directory for final .dat files')
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Build geosite.dat
    build_geosite_dat(
        args.extracted_geosite,
        args.whitelist_domains,
        args.whitelist_ads,
        output_dir / 'geosite.dat'
    )
    
    # Build geoip.dat
    build_geoip_dat(
        args.extracted_geoip,
        args.whitelist_ips,
        output_dir / 'geoip.dat'
    )
    
    print("\n✅ Build complete!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
